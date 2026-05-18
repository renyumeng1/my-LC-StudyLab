import re
from math import log
from typing import Any, Optional, Literal
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_core.retrievers import BaseRetriever, RetrieverLike
from langchain_core.tools.retriever import (
    create_retriever_tool as lc_create_retriever_tool,
)

from ..config import settings, get_logger
from .evaluation import reciprocal_rank_fusion

logger = get_logger(__name__)


# 检索类型
SearchType = Literal["similarity", "mmr", "similarity_score_threshold"]


class ReciprocalRankFusionRetriever(BaseRetriever):
    """用 RRF 融合多个检索器的结果。"""

    retrievers: list[BaseRetriever]
    weights: list[float] | None = None
    k: int = 5
    rrf_k: int = 60

    def _get_relevant_documents(self, query: str) -> list[Document]:
        doc_by_id: dict[str, Document] = {}
        ranked_lists: list[list[str]] = []

        for index, retriever in enumerate(self.retrievers):
            docs = retriever.invoke(query)
            ranked_doc_ids: list[str] = []
            for rank, doc in enumerate(docs, start=1):
                doc_id = _document_id(doc, fallback=f"{index}:{rank}")
                if doc_id not in doc_by_id:
                    doc_by_id[doc_id] = doc
                ranked_doc_ids.append(doc_id)
            ranked_lists.append(ranked_doc_ids)

        fused = reciprocal_rank_fusion(
            ranked_lists=ranked_lists,
            k=self.rrf_k,
            weights=self.weights,
        )
        return [doc_by_id[doc_id] for doc_id, _ in fused[: self.k]]


class TermOverlapReranker:
    """无模型依赖的词项覆盖率 reranker，用作后续 cross-encoder 的可替换基线。"""

    def rerank(
        self,
        query: str,
        documents: list[Document],
        top_k: int | None = None,
    ) -> list[Document]:
        query_terms = _tokenize(query)
        if not query_terms:
            return documents[:top_k] if top_k is not None else documents

        scored = [
            (self.score(query_terms, document), index, document)
            for index, document in enumerate(documents)
        ]
        scored.sort(key=lambda item: (item[0], -item[1]), reverse=True)
        ordered = [document for _, _, document in scored]
        return ordered[:top_k] if top_k is not None else ordered

    def score(self, query_terms: set[str], document: Document) -> float:
        document_terms = _tokenize(document.page_content)
        if not document_terms:
            return 0.0
        return len(query_terms & document_terms) / len(query_terms)


class RerankRetriever(BaseRetriever):
    """先召回候选文档，再用 reranker 重排并截断到 top K。"""

    retriever: BaseRetriever
    reranker: Any
    k: int = 5
    candidate_k: int | None = None

    def _get_relevant_documents(self, query: str) -> list[Document]:
        documents = self.retriever.invoke(query)
        if self.candidate_k is not None:
            documents = documents[: self.candidate_k]
        return self.reranker.rerank(query, documents, top_k=self.k)


def create_retriever(
    vector_store: VectorStore,
    search_type: Optional[SearchType | str] = None,
    k: Optional[int] = None,
    score_threshold: Optional[float] = None,
    fetch_k: Optional[int] = None,
    **kwargs: Any,
) -> BaseRetriever:
    """
    从向量库创建检索器

    Args:
        vector_store: 向量存储实例
        search_type: 检索类型
            - "similarity": 相似度检索（默认）
            - "mmr": 最大边际相关性检索（多样性）
            - "similarity_score_threshold": 相似度阈值过滤
        k: 返回的文档数量，默认使用配置值
        score_threshold: 相似度阈值（仅用于 similarity_score_threshold）
        fetch_k: MMR 候选文档数量（仅用于 mmr）
        **kwargs: 其他参数

    Returns:
        Retriever 实例

    Example:
        >>> from rag import load_vector_store, get_embeddings, create_retriever
        >>>
        >>> # 加载向量库
        >>> embeddings = get_embeddings()
        >>> vector_store = load_vector_store("data/indexes/my_docs", embeddings)
        >>>
        >>> # 创建相似度检索器
        >>> retriever = create_retriever(vector_store, search_type="similarity", k=4)
        >>>
        >>> # 创建 MMR 检索器（更多样化的结果）
        >>> retriever = create_retriever(
        ...     vector_store,
        ...     search_type="mmr",
        ...     k=4,
        ...     fetch_k=20
        ... )
        >>>
        >>> # 创建阈值过滤检索器
        >>> retriever = create_retriever(
        ...     vector_store,
        ...     search_type="similarity_score_threshold",
        ...     score_threshold=0.7
        ... )
        >>>
        >>> # 使用检索器
        >>> docs = retriever.invoke("什么是机器学习？")
        >>> for doc in docs:
        ...     print(doc.page_content[:100])
    """

    search_type = search_type or settings.retriever_search_type
    k = k or settings.retriever_k
    score_threshold = score_threshold or settings.retriever_score_threshold
    fetch_k = fetch_k or settings.retriever_fetch_k

    logger.info(f"🔍 创建检索器: search_type={search_type}, k={k}")

    # 构建搜索参数
    search_kwargs: dict[str, Any] = {"k": k}

    if search_type == "mmr":
        search_kwargs["fetch_k"] = fetch_k
        logger.debug(f"MMR 检索: fetch_k={fetch_k}")
    elif search_type == "similarity_score_threshold":
        search_kwargs["score_threshold"] = score_threshold
        logger.debug(f"相似度阈值检索: score_threshold={score_threshold}")

    search_kwargs.update(kwargs)

    try:
        retriever = vector_store.as_retriever(
            search_type=search_type, search_kwargs=search_kwargs
        )

        logger.info("✅ 检索器创建成功")
        return retriever
    except Exception as e:
        logger.error(f"❌ 创建检索器失败: {e}")
        raise


def search_retriever_with_scores(
    retriever: BaseRetriever,
    query: str,
    **kwargs: Any,
) -> list[tuple[Document, float]]:
    vector_store = getattr(retriever, "vectorstore", None)
    if vector_store is None:
        raise ValueError("当前检索器不包含 vectorstore，无法获取真实相关度分数")

    search_kwargs = dict(getattr(retriever, "search_kwargs", {}) or {})
    search_kwargs.update(kwargs)

    return vector_store.similarity_search_with_relevance_scores(
        query=query,
        **search_kwargs,
    )


def create_rrf_retriever(
    retrievers: list[BaseRetriever],
    weights: list[float] | None = None,
    k: Optional[int] = None,
    rrf_k: int = 60,
) -> BaseRetriever:
    """创建 RRF 组合检索器，融合 dense/sparse 等多路召回。"""
    if not retrievers:
        raise ValueError("retrievers 不能为空")
    if weights is not None and len(weights) != len(retrievers):
        raise ValueError("weights 数量必须和 retrievers 数量一致")
    return ReciprocalRankFusionRetriever(
        retrievers=retrievers,
        weights=weights,
        k=k or settings.retriever_k,
        rrf_k=rrf_k,
    )


def create_rerank_retriever(
    retriever: BaseRetriever,
    reranker: Any | None = None,
    k: Optional[int] = None,
    candidate_k: Optional[int] = None,
) -> BaseRetriever:
    """创建两阶段 rerank 检索器。"""
    return RerankRetriever(
        retriever=retriever,
        reranker=reranker or TermOverlapReranker(),
        k=k or settings.retriever_k,
        candidate_k=candidate_k,
    )


def create_retriever_tool(
    retriever: BaseRetriever,
    name: str = "knowledge_base",
    description: Optional[str] = None,
) -> Any:
    if description is None:
        description = (
            f"搜索 {name} 知识库中的相关信息。"
            "当需要回答关于文档内容的问题时使用此工具。"
            "输入应该是一个搜索查询。"
        )

    logger.info(f"🔧 创建检索器工具: {name}")
    logger.debug(f"   描述: {description}")

    try:
        tool = lc_create_retriever_tool(
            retriever=retriever, name=name, description=description
        )

        logger.info("✅ 检索器工具创建成功")
        return tool
    except Exception as e:
        logger.error(f"❌ 创建检索器工具失败: {e}")
        raise


def test_retriever(
    retriever: BaseRetriever,
    query: str = "测试查询",
    show_results: bool = True,
) -> bool:

    try:
        logger.info(f"🔍 测试检索器: query='{query}'")
        docs = retriever.invoke(query)

        logger.info(f"✅ 检索成功: 找到 {len(docs)} 个文档")

        if show_results and docs:
            logger.info("📄 检索结果:")
            for i, doc in enumerate(docs, 1):
                logger.info(f"   [{i}] {doc.page_content[:100]}...")
                if doc.metadata:
                    logger.info(f"       元数据: {doc.metadata}")

        return True

    except Exception as e:
        logger.error(f"❌ 检索测试失败: {e}")
        return False


def create_multi_retriever(
    retrievers: list[tuple[RetrieverLike, float]], **kwargs: Any
) -> BaseRetriever:
    """创建多个检索器，按照权重合并结果

    Args:
        retrievers (list[tuple[BaseRetriever,float]]): 元组列表

    Returns:
        Ensemble Retriever

    Example:
        >>> # 创建两个不同的检索器
        >>> retriever1 = create_retriever(vector_store1, k=3)
        >>> retriever2 = create_retriever(vector_store2, k=3)
        >>>
        >>> # 组合检索器
        >>> ensemble = create_multi_retriever([
        ...     (retriever1, 0.6),
        ...     (retriever2, 0.4),
        ... ])
    """

    try:
        from langchain_classic.retrievers import EnsembleRetriever

        logger.info(f"🔍 创建组合检索器：{len(retrievers)}个检索器")

        retriever_list = [r for r, _ in retrievers]
        weights = [w for _, w in retrievers]

        ensemble = EnsembleRetriever(
            retrievers=retriever_list, weights=weights, **kwargs
        )

        logger.info("✅ 组合检索器创建成功")
        return ensemble

    except ImportError:
        logger.error("❌ EnsembleRetriever 不可用")
        raise
    except Exception as e:
        logger.error(f"❌ 创建组合检索器失败: {e}")
        raise


def _document_id(document: Document, fallback: str) -> str:
    metadata = document.metadata or {}
    for key in ("doc_id", "id", "source"):
        value = metadata.get(key)
        if value:
            return str(value)
    return fallback


def _tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w]+", text.lower())
        if len(token) > 1
    }


def get_retriever_config(search_type: str = "similarity") -> dict:
    """
    获取推荐的检索器配置

    Args:
        search_type: 检索类型

    Returns:
        配置字典

    Example:
        >>> config = get_retriever_config("mmr")
        >>> retriever = create_retriever(vector_store, **config)
    """
    configs = {
        "similarity": {
            "search_type": "similarity",
            "k": 4,
            "description": "基本相似度检索，速度快",
        },
        "mmr": {
            "search_type": "mmr",
            "k": 4,
            "fetch_k": 20,
            "description": "最大边际相关性检索，结果更多样化",
        },
        "threshold": {
            "search_type": "similarity_score_threshold",
            "score_threshold": 0.7,
            "k": 10,
            "description": "相似度阈值过滤，只返回高质量结果",
        },
    }

    if search_type not in configs:
        logger.warning(f"未知的检索类型: {search_type}，使用默认配置")
        return configs["similarity"]

    config = configs[search_type].copy()
    logger.info(f"📋 推荐的检索器配置 ({search_type}):")
    logger.info(f"   {config.get('description', '')}")

    # 移除描述字段
    config.pop("description", None)

    return config
