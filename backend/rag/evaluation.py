from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol

from langchain_core.documents import Document


class RetrieverProtocol(Protocol):
    """最小检索器协议，兼容 LangChain retriever 的 invoke 接口。"""

    def invoke(self, query: str) -> list[Document]:
        ...


@dataclass(frozen=True)
class QueryJudgement:
    """一条查询的标准答案集合。"""

    query_id: str
    query: str
    relevant_doc_ids: set[str]


@dataclass(frozen=True)
class QueryEvaluation:
    """单条查询在一个 K 值下的评测结果。"""

    query_id: str
    k: int
    retrieved_doc_ids: list[str]
    relevant_doc_ids: set[str]
    recall: float
    precision: float
    reciprocal_rank: float
    ndcg: float


@dataclass(frozen=True)
class EvaluationReport:
    """多条查询的聚合评测结果。"""

    k: int
    query_count: int
    recall_at_k: float
    precision_at_k: float
    mrr_at_k: float
    ndcg_at_k: float
    per_query: list[QueryEvaluation]


def load_beir_queries(dataset_path: str | Path, split: str = "test") -> list[QueryJudgement]:
    """加载 BEIR 格式数据集中的 queries 与 qrels。

    BEIR 数据集通常包含 `queries.jsonl` 和 `qrels/{split}.tsv`。
    `queries.jsonl` 每行包含 `_id` 和 `text`，`qrels` 表示 query 与相关文档。
    """
    dataset_path = Path(dataset_path)
    queries = _load_beir_query_texts(dataset_path / "queries.jsonl")
    qrels = _load_beir_qrels(dataset_path / "qrels" / f"{split}.tsv")

    judgements: list[QueryJudgement] = []
    for query_id, doc_ids in qrels.items():
        query = queries.get(query_id)
        if query is None:
            continue
        judgements.append(
            QueryJudgement(
                query_id=query_id,
                query=query,
                relevant_doc_ids=doc_ids,
            )
        )
    return judgements


def load_beir_corpus(dataset_path: str | Path) -> list[Document]:
    """加载 BEIR `corpus.jsonl` 为 LangChain Document 列表。"""
    corpus_path = Path(dataset_path) / "corpus.jsonl"
    documents: list[Document] = []
    with corpus_path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            item = json.loads(line)
            doc_id = str(item["_id"])
            title = item.get("title") or ""
            text = item.get("text") or ""
            content = f"{title}\n\n{text}".strip()
            documents.append(
                Document(
                    page_content=content,
                    metadata={"doc_id": doc_id, "source": doc_id, "title": title},
                )
            )
    return documents


def evaluate_retriever(
    retriever: RetrieverProtocol,
    judgements: Iterable[QueryJudgement],
    k: int = 5,
    doc_id_metadata_key: str = "doc_id",
) -> EvaluationReport:
    """对任意 LangChain 风格检索器计算 Recall/MRR/nDCG 等指标。"""
    per_query: list[QueryEvaluation] = []
    for judgement in judgements:
        documents = retriever.invoke(judgement.query)
        retrieved_doc_ids = [
            _extract_doc_id(doc, doc_id_metadata_key)
            for doc in documents[:k]
            if _extract_doc_id(doc, doc_id_metadata_key) is not None
        ]
        per_query.append(
            evaluate_query(
                query_id=judgement.query_id,
                retrieved_doc_ids=retrieved_doc_ids,
                relevant_doc_ids=judgement.relevant_doc_ids,
                k=k,
            )
        )
    return aggregate_evaluations(per_query, k=k)


def evaluate_query(
    query_id: str,
    retrieved_doc_ids: list[str],
    relevant_doc_ids: set[str],
    k: int,
) -> QueryEvaluation:
    """计算单条查询在 K 值下的指标。"""
    top_k = retrieved_doc_ids[:k]
    recall = recall_at_k(top_k, relevant_doc_ids, k)
    precision = precision_at_k(top_k, relevant_doc_ids, k)
    reciprocal_rank = reciprocal_rank_at_k(top_k, relevant_doc_ids, k)
    ndcg = ndcg_at_k(top_k, relevant_doc_ids, k)
    return QueryEvaluation(
        query_id=query_id,
        k=k,
        retrieved_doc_ids=top_k,
        relevant_doc_ids=relevant_doc_ids,
        recall=recall,
        precision=precision,
        reciprocal_rank=reciprocal_rank,
        ndcg=ndcg,
    )


def aggregate_evaluations(
    evaluations: list[QueryEvaluation],
    k: int,
) -> EvaluationReport:
    """聚合多条查询的平均指标。"""
    query_count = len(evaluations)
    if query_count == 0:
        return EvaluationReport(
            k=k,
            query_count=0,
            recall_at_k=0.0,
            precision_at_k=0.0,
            mrr_at_k=0.0,
            ndcg_at_k=0.0,
            per_query=[],
        )

    return EvaluationReport(
        k=k,
        query_count=query_count,
        recall_at_k=sum(item.recall for item in evaluations) / query_count,
        precision_at_k=sum(item.precision for item in evaluations) / query_count,
        mrr_at_k=sum(item.reciprocal_rank for item in evaluations) / query_count,
        ndcg_at_k=sum(item.ndcg for item in evaluations) / query_count,
        per_query=evaluations,
    )


def recall_at_k(
    retrieved_doc_ids: list[str],
    relevant_doc_ids: set[str],
    k: int,
) -> float:
    """Recall@K = |Relevant ∩ Retrieved@K| / |Relevant|。"""
    if not relevant_doc_ids:
        return 0.0
    hits = _count_hits(retrieved_doc_ids[:k], relevant_doc_ids)
    return hits / len(relevant_doc_ids)


def precision_at_k(
    retrieved_doc_ids: list[str],
    relevant_doc_ids: set[str],
    k: int,
) -> float:
    """Precision@K = |Relevant ∩ Retrieved@K| / K。"""
    if k <= 0:
        return 0.0
    hits = _count_hits(retrieved_doc_ids[:k], relevant_doc_ids)
    return hits / k


def reciprocal_rank_at_k(
    retrieved_doc_ids: list[str],
    relevant_doc_ids: set[str],
    k: int,
) -> float:
    """MRR 的单查询项：第一个相关文档排名的倒数。"""
    for rank, doc_id in enumerate(retrieved_doc_ids[:k], start=1):
        if doc_id in relevant_doc_ids:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(
    retrieved_doc_ids: list[str],
    relevant_doc_ids: set[str],
    k: int,
) -> float:
    """nDCG@K = DCG@K / IDCG@K，二值相关性版本。"""
    if not relevant_doc_ids:
        return 0.0

    gains = [1.0 if doc_id in relevant_doc_ids else 0.0 for doc_id in retrieved_doc_ids[:k]]
    dcg = _discounted_cumulative_gain(gains)
    ideal_hits = min(len(relevant_doc_ids), k)
    idcg = _discounted_cumulative_gain([1.0] * ideal_hits)
    if idcg == 0.0:
        return 0.0
    return dcg / idcg


def reciprocal_rank_fusion(
    ranked_lists: Iterable[list[str]],
    k: int = 60,
    weights: Iterable[float] | None = None,
) -> list[tuple[str, float]]:
    """RRF: score(d) = sum_i weight_i / (k + rank_i(d))。"""
    lists = list(ranked_lists)
    weight_values = list(weights) if weights is not None else [1.0] * len(lists)
    if len(weight_values) != len(lists):
        raise ValueError("weights 数量必须和 ranked_lists 数量一致")

    scores: dict[str, float] = {}
    for ranked_list, weight in zip(lists, weight_values):
        for rank, doc_id in enumerate(ranked_list, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + weight / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def _load_beir_query_texts(path: Path) -> dict[str, str]:
    queries: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue
            item = json.loads(line)
            queries[str(item["_id"])] = str(item["text"])
    return queries


def _load_beir_qrels(path: Path) -> dict[str, set[str]]:
    qrels: dict[str, set[str]] = {}
    with path.open("r", encoding="utf-8") as file:
        header = file.readline().strip().split("\t")
        query_index = _index_or_default(header, "query-id", 0)
        corpus_index = _index_or_default(header, "corpus-id", 1)
        score_index = _index_or_default(header, "score", 2)
        for line in file:
            if not line.strip():
                continue
            columns = line.rstrip("\n").split("\t")
            score = int(float(columns[score_index]))
            if score <= 0:
                continue
            query_id = columns[query_index]
            corpus_id = columns[corpus_index]
            qrels.setdefault(query_id, set()).add(corpus_id)
    return qrels


def _index_or_default(header: list[str], name: str, default: int) -> int:
    try:
        return header.index(name)
    except ValueError:
        return default


def _count_hits(retrieved_doc_ids: list[str], relevant_doc_ids: set[str]) -> int:
    seen: set[str] = set()
    hits = 0
    for doc_id in retrieved_doc_ids:
        if doc_id in seen:
            continue
        seen.add(doc_id)
        if doc_id in relevant_doc_ids:
            hits += 1
    return hits


def _discounted_cumulative_gain(gains: list[float]) -> float:
    return sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))


def _extract_doc_id(doc: Document, metadata_key: str) -> str | None:
    value: Any = (doc.metadata or {}).get(metadata_key)
    if value is None:
        value = (doc.metadata or {}).get("source")
    if value is None:
        return None
    return str(value)
