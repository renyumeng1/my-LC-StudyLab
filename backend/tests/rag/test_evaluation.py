from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from backend.rag.evaluation import (
    QueryJudgement,
    evaluate_retriever,
    load_beir_corpus,
    load_beir_queries,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
    reciprocal_rank_fusion,
)


class _StaticRetriever:
    def __init__(self, results: dict[str, list[Document]]) -> None:
        self.results = results

    def invoke(self, query: str) -> list[Document]:
        return self.results[query]


def test_metric_formulas_use_top_k() -> None:
    retrieved = ["d1", "d2", "d3", "d4"]
    relevant = {"d2", "d4", "d5"}

    assert recall_at_k(retrieved, relevant, k=3) == 1 / 3
    assert precision_at_k(retrieved, relevant, k=3) == 1 / 3
    assert reciprocal_rank_at_k(retrieved, relevant, k=3) == 1 / 2
    assert round(ndcg_at_k(retrieved, relevant, k=4), 4) == 0.4982


def test_reciprocal_rank_fusion_boosts_docs_seen_in_multiple_lists() -> None:
    fused = reciprocal_rank_fusion(
        [["d1", "d2", "d3"], ["d2", "d4", "d1"]],
        k=60,
    )

    assert fused[0][0] == "d2"
    assert fused[1][0] == "d1"
    assert {doc_id for doc_id, _ in fused} == {"d1", "d2", "d3", "d4"}


def test_evaluate_retriever_aggregates_metrics() -> None:
    retriever = _StaticRetriever(
        {
            "what is rag": [
                Document(page_content="x", metadata={"doc_id": "d2"}),
                Document(page_content="x", metadata={"doc_id": "d1"}),
            ],
            "what is bm25": [
                Document(page_content="x", metadata={"doc_id": "d4"}),
                Document(page_content="x", metadata={"doc_id": "d3"}),
            ],
        }
    )
    judgements = [
        QueryJudgement("q1", "what is rag", {"d1", "d2"}),
        QueryJudgement("q2", "what is bm25", {"d3"}),
    ]

    report = evaluate_retriever(retriever, judgements, k=2)

    assert report.query_count == 2
    assert report.recall_at_k == 1.0
    assert report.precision_at_k == 0.75
    assert report.mrr_at_k == 0.75


def test_load_beir_dataset_files(tmp_path: Path) -> None:
    (tmp_path / "qrels").mkdir()
    (tmp_path / "corpus.jsonl").write_text(
        '{"_id": "d1", "title": "RAG", "text": "Retrieval augmented generation"}\n',
        encoding="utf-8",
    )
    (tmp_path / "queries.jsonl").write_text(
        '{"_id": "q1", "text": "what is rag"}\n',
        encoding="utf-8",
    )
    (tmp_path / "qrels" / "test.tsv").write_text(
        "query-id\tcorpus-id\tscore\nq1\td1\t1\n",
        encoding="utf-8",
    )

    corpus = load_beir_corpus(tmp_path)
    queries = load_beir_queries(tmp_path)

    assert corpus[0].metadata["doc_id"] == "d1"
    assert corpus[0].page_content.startswith("RAG")
    assert queries == [QueryJudgement("q1", "what is rag", {"d1"})]
