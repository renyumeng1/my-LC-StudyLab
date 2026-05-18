from __future__ import annotations

from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from backend.rag.retrievers import (
    create_rerank_retriever,
    create_rrf_retriever,
    search_retriever_with_scores,
)


class _FakeVectorStore:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def similarity_search_with_relevance_scores(
        self, query: str, **kwargs: Any
    ) -> list[tuple[Document, float]]:
        self.calls.append({"query": query, **kwargs})
        return [(Document(page_content="real score"), 0.88)]


class _FakeRetriever:
    def __init__(self) -> None:
        self.vectorstore = _FakeVectorStore()
        self.search_kwargs = {"k": 4, "fetch_k": 20}


class _StaticRetriever(BaseRetriever):
    docs: list[Document]

    def _get_relevant_documents(self, query: str) -> list[Document]:
        return self.docs


def test_search_retriever_with_scores_uses_retriever_vectorstore() -> None:
    retriever = _FakeRetriever()

    results = search_retriever_with_scores(retriever, "rag", k=8)

    assert results[0][1] == 0.88
    assert retriever.vectorstore.calls == [{"query": "rag", "k": 8, "fetch_k": 20}]


def test_create_rrf_retriever_fuses_multiple_ranked_lists() -> None:
    dense = _StaticRetriever(
        docs=[
            Document(page_content="dense first", metadata={"doc_id": "d1"}),
            Document(page_content="dense second", metadata={"doc_id": "d2"}),
            Document(page_content="dense third", metadata={"doc_id": "d3"}),
        ]
    )
    sparse = _StaticRetriever(
        docs=[
            Document(page_content="sparse first", metadata={"doc_id": "d2"}),
            Document(page_content="sparse second", metadata={"doc_id": "d4"}),
            Document(page_content="sparse third", metadata={"doc_id": "d1"}),
        ]
    )

    retriever = create_rrf_retriever([dense, sparse], k=2)

    docs = retriever.invoke("rag query")

    assert [doc.metadata["doc_id"] for doc in docs] == ["d2", "d1"]


def test_create_rerank_retriever_reorders_candidates() -> None:
    base = _StaticRetriever(
        docs=[
            Document(page_content="unrelated vector database"),
            Document(page_content="python decorator wraps a function"),
            Document(page_content="python class inheritance"),
        ]
    )

    retriever = create_rerank_retriever(base, k=1)

    docs = retriever.invoke("python decorator function")

    assert docs[0].page_content == "python decorator wraps a function"
