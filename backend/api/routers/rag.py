from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from langchain_core.documents import Document

from ...config import settings, get_logger
from ...rag.loaders import load_document, load_directory, get_supported_extensions
from ...rag.splitters import split_documents, split_text
from ...rag.embeddings import get_embeddings
from ...rag.index_manager import IndexManager
from ...rag.retrievers import create_retriever
from ...rag.rag_agent import create_conversational_rag_agent, aquery_rag_agent


logger = get_logger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])

SplitterType = Literal["recursive", "character", "markdown", "token"]
SearchType = Literal["similarity", "mmr", "similarity_score_threshold"]


class IndexSourceRequest(BaseModel):
    source_type: Literal["files", "directory", "text"] = Field(
        default="text", description="索引数据来源类型: files/directory/text"
    )
    files: Optional[list[str]] = Field(default=None, description="文件路径列表")
    directory: Optional[str] = Field(default=None, description="目录路径")
    texts: Optional[list[str]] = Field(default=None, description="纯文本列表")
    glob_pattern: str = Field(default="**/*", description="目录加载的匹配模式")
    exclude_patterns: Optional[list[str]] = Field(
        default=None, description="目录加载时排除的模式"
    )
    recursive: bool = Field(default=True, description="是否递归加载目录")
    max_files: Optional[int] = Field(default=None, description="最多加载的文件数")
    splitter_type: SplitterType = Field(default="recursive", description="分块器类型")
    chunk_size: Optional[int] = Field(default=None, description="分块大小")
    chunk_overlap: Optional[int] = Field(default=None, description="分块重叠大小")
    metadata: Optional[dict[str, Any]] = Field(
        default=None, description="要添加到文档的额外元数据"
    )
    embedding_model: Optional[str] = Field(
        default=None, description="Embedding 模型名称"
    )
    embedding_batch_size: Optional[int] = Field(
        default=None, description="Embedding 批处理大小"
    )


class CreateIndexRequest(IndexSourceRequest):
    name: str = Field(..., min_length=1, description="索引名称")
    description: str = Field(default="", description="索引描述")
    store_type: Optional[str] = Field(default=None, description="向量库类型")
    overwrite: bool = Field(default=False, description="是否覆盖已有索引")


class UpdateIndexRequest(IndexSourceRequest):
    pass


class IndexOperationResponse(BaseModel):
    success: bool = Field(default=True, description="操作是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")
    index: Optional[dict[str, Any]] = Field(default=None, description="索引详情")


class IndexListResponse(BaseModel):
    indexes: list[dict[str, Any]] = Field(default_factory=list, description="索引列表")


class RagQueryRequest(BaseModel):
    index_name: str = Field(..., min_length=1, description="索引名称")
    query: str = Field(..., min_length=1, description="查询问题")
    search_type: Optional[SearchType] = Field(default=None, description="检索模式")
    k: Optional[int] = Field(default=None, description="返回文档数量")
    score_threshold: Optional[float] = Field(
        default=None, description="相似度阈值"
    )
    fetch_k: Optional[int] = Field(default=None, description="MMR 候选文档数量")
    model: Optional[str] = Field(default=None, description="对话模型")
    embedding_model: Optional[str] = Field(default=None, description="Embedding 模型名称")
    embedding_batch_size: Optional[int] = Field(
        default=None, description="Embedding 批处理大小"
    )
    include_sources: bool = Field(default=True, description="是否返回来源信息")
    include_documents: bool = Field(default=False, description="是否返回文档内容")


class RagQueryResponse(BaseModel):
    success: bool = Field(default=True, description="查询是否成功")
    error: Optional[str] = Field(default=None, description="错误信息")
    index_name: str = Field(..., description="索引名称")
    answer: str = Field(default="", description="回答内容")
    sources: list[str] = Field(default_factory=list, description="来源列表")
    documents: list[dict[str, Any]] = Field(
        default_factory=list, description="检索文档列表"
    )


def _resolve_data_path(raw_path: str) -> Path:
    base_dir = Path(settings.DATA_DIR).resolve()
    candidate = Path(raw_path)
    if candidate.is_absolute():
        raise HTTPException(status_code=400, detail="仅支持 DATA_DIR 下的相对路径")
    if ".." in candidate.parts:
        raise HTTPException(status_code=400, detail="路径不能包含 ..")
    resolved = (base_dir / candidate).resolve()
    if not resolved.is_relative_to(base_dir):
        raise HTTPException(status_code=400, detail="路径必须位于 DATA_DIR 下")
    return resolved


def _apply_metadata(documents: list[Document], metadata: Optional[dict[str, Any]]) -> None:
    if not metadata:
        return
    for doc in documents:
        doc.metadata = doc.metadata or {}
        doc.metadata.update(metadata)


def _build_documents(request: IndexSourceRequest) -> list[Document]:
    if request.source_type == "files":
        if not request.files:
            raise HTTPException(status_code=400, detail="files 不能为空")
        documents: list[Document] = []
        for file_path in request.files:
            resolved = _resolve_data_path(file_path)
            documents.extend(load_document(str(resolved)))
        _apply_metadata(documents, request.metadata)
        return split_documents(
            documents,
            splitter_type=request.splitter_type,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )

    if request.source_type == "directory":
        if not request.directory:
            raise HTTPException(status_code=400, detail="directory 不能为空")
        resolved = _resolve_data_path(request.directory)
        documents = load_directory(
            str(resolved),
            glob_pattern=request.glob_pattern,
            exclude_patterns=request.exclude_patterns,
            recursive=request.recursive,
            max_files=request.max_files,
        )
        _apply_metadata(documents, request.metadata)
        return split_documents(
            documents,
            splitter_type=request.splitter_type,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
        )

    if request.source_type == "text":
        if not request.texts:
            raise HTTPException(status_code=400, detail="texts 不能为空")
        documents = []
        base_metadata = request.metadata or {}
        for index, text in enumerate(request.texts):
            if not text.strip():
                continue
            metadata = {
                "source": base_metadata.get("source", "manual_input"),
                "index": index,
                **base_metadata,
            }
            documents.extend(
                split_text(
                    text,
                    splitter_type=request.splitter_type,
                    chunk_size=request.chunk_size,
                    chunk_overlap=request.chunk_overlap,
                    metadata=metadata,
                )
            )
        if not documents:
            raise HTTPException(status_code=400, detail="文本内容为空")
        return documents

    raise HTTPException(status_code=400, detail="不支持的 source_type")


@router.get("/supported-extensions")
async def supported_extensions() -> dict[str, str]:
    return get_supported_extensions()


@router.get("/indexes", response_model=IndexListResponse)
async def list_indexes() -> IndexListResponse:
    manager = IndexManager()
    indexes = manager.list_indexes()
    return IndexListResponse(indexes=indexes)


@router.get("/indexes/{name}", response_model=IndexOperationResponse)
async def get_index(name: str) -> IndexOperationResponse:
    manager = IndexManager()
    info = manager.get_index_info(name)
    if not info:
        return IndexOperationResponse(success=False, error="索引不存在", index=None)
    return IndexOperationResponse(index=info)


@router.post("/indexes", response_model=IndexOperationResponse)
async def create_index(request: CreateIndexRequest) -> IndexOperationResponse:
    try:
        manager = IndexManager()
        documents = _build_documents(request)
        embeddings = get_embeddings(
            model=request.embedding_model,
            batch_size=request.embedding_batch_size,
        )
        manager.create_index(
            name=request.name,
            documents=documents,
            embeddings=embeddings,
            description=request.description,
            store_type=request.store_type,
            overwrite=request.overwrite,
        )
        info = manager.get_index_info(request.name)
        return IndexOperationResponse(index=info)
    except Exception as exc:
        logger.error(f"❌ 创建索引失败: {exc}")
        return IndexOperationResponse(success=False, error=str(exc))


@router.post("/indexes/{name}/documents", response_model=IndexOperationResponse)
async def update_index(name: str, request: UpdateIndexRequest) -> IndexOperationResponse:
    try:
        manager = IndexManager()
        documents = _build_documents(request)
        embeddings = get_embeddings(
            model=request.embedding_model,
            batch_size=request.embedding_batch_size,
        )
        manager.update_index(name=name, documents=documents, embeddings=embeddings)
        info = manager.get_index_info(name)
        return IndexOperationResponse(index=info)
    except Exception as exc:
        logger.error(f"❌ 更新索引失败: {exc}")
        return IndexOperationResponse(success=False, error=str(exc))


@router.delete("/indexes/{name}", response_model=IndexOperationResponse)
async def delete_index(name: str) -> IndexOperationResponse:
    try:
        manager = IndexManager()
        manager.delete_index(name)
        return IndexOperationResponse(index=None)
    except Exception as exc:
        logger.error(f"❌ 删除索引失败: {exc}")
        return IndexOperationResponse(success=False, error=str(exc))


@router.post("/query", response_model=RagQueryResponse)
async def query_rag(request: RagQueryRequest) -> RagQueryResponse:
    try:
        manager = IndexManager()
        embeddings = get_embeddings(
            model=request.embedding_model,
            batch_size=request.embedding_batch_size,
        )
        vector_store = manager.load_index(request.index_name, embeddings)
        retriever = create_retriever(
            vector_store=vector_store,
            search_type=request.search_type,
            k=request.k,
            score_threshold=request.score_threshold,
            fetch_k=request.fetch_k,
        )
        agent = create_conversational_rag_agent(
            retriever=retriever,
            model=request.model,
        )
        result = await aquery_rag_agent(agent, request.query)
        answer = result.get("answer", "") if isinstance(result, dict) else str(result)

        sources: list[str] = []
        documents: list[dict[str, Any]] = []
        if request.include_sources or request.include_documents:
            retrieved_docs = retriever.invoke(request.query)
            for doc in retrieved_docs:
                metadata = doc.metadata or {}
                source = metadata.get("source")
                if not source and metadata.get("filename"):
                    source = metadata["filename"]
                    metadata = {**metadata, "source": source}
                if source and source not in sources:
                    sources.append(source)
                if request.include_documents:
                    documents.append(
                        {"content": doc.page_content, "metadata": metadata}
                    )

        return RagQueryResponse(
            index_name=request.index_name,
            answer=answer,
            sources=sources,
            documents=documents,
        )
    except Exception as exc:
        logger.error(f"❌ RAG 查询失败: {exc}")
        return RagQueryResponse(
            success=False,
            error=str(exc),
            index_name=request.index_name,
            answer="",
        )
