from __future__ import annotations

from typing import Any

from langchain_core.documents import Document

from backend.rag.retrievers import search_retriever_with_scores


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


def test_search_retriever_with_scores_uses_retriever_vectorstore() -> None:
    retriever = _FakeRetriever()

    results = search_retriever_with_scores(retriever, "rag", k=8)

    assert results[0][1] == 0.88
    assert retriever.vectorstore.calls == [{"query": "rag", "k": 8, "fetch_k": 20}]
