from __future__ import annotations

from importlib import import_module
from typing import Any

from langchain_core.documents import Document

retrieval_node_module = import_module("backend.workflows.nodes.retrieval_node")


class _FakeIndexManager:
    loaded_index_names: list[str] = []

    def load_index(self, name: str, embeddings: Any) -> Any:
        self.loaded_index_names.append(name)
        return _FakeVectorStore()


class _FakeVectorStore:
    pass


class _FakeRetriever:
    pass


def _fake_create_retriever(vector_store: Any, **kwargs: Any) -> _FakeRetriever:
    _fake_create_retriever.calls.append({"vector_store": vector_store, **kwargs})
    return _FakeRetriever()


_fake_create_retriever.calls = []


def _fake_search_with_scores(
    retriever: Any, query: str, k: int, fetch_k: int
) -> list[tuple[Document, float]]:
    if query == "LangChain RAG":
        return [
            (Document(page_content="RAG overview", metadata={"source": "a.md"}), 0.92),
            (Document(page_content="Vector search", metadata={"source": "b.md"}), 0.84),
        ]

    return [
        (Document(page_content="RAG overview", metadata={"source": "a.md"}), 0.70),
        (Document(page_content=f"Extra {query}", metadata={"source": "c.md"}), 0.65),
    ]


def test_retrieval_node_uses_explicit_index_and_real_scores(monkeypatch: Any) -> None:
    _FakeIndexManager.loaded_index_names = []
    _fake_create_retriever.calls = []
    monkeypatch.setattr(retrieval_node_module, "IndexManager", _FakeIndexManager)
    monkeypatch.setattr(retrieval_node_module, "get_embeddings", lambda: object())
    monkeypatch.setattr(retrieval_node_module, "create_retriever", _fake_create_retriever)
    monkeypatch.setattr(
        retrieval_node_module,
        "search_retriever_with_scores",
        _fake_search_with_scores,
    )

    result = retrieval_node_module.retrieval_node(
        {
            "learning_plan": {
                "topic": "LangChain RAG",
                "key_points": ["retrieval", "embedding"],
            },
            "index_name": "study_lab_docs",
            "messages": [],
        }
    )

    assert _FakeIndexManager.loaded_index_names == ["study_lab_docs"]
    assert len(_fake_create_retriever.calls) == 1
    assert result["current_step"] == "retrieval"
    assert result["retrieved_docs"] == [
        {
            "content": "RAG overview",
            "metadata": {"source": "a.md"},
            "relevance_score": 0.92,
        },
        {
            "content": "Vector search",
            "metadata": {"source": "b.md"},
            "relevance_score": 0.84,
        },
        {
            "content": "Extra retrieval",
            "metadata": {"source": "c.md"},
            "relevance_score": 0.65,
        },
    ]


def test_retrieval_node_does_not_guess_index_name() -> None:
    result = retrieval_node_module.retrieval_node(
        {
            "learning_plan": {
                "topic": "LangChain RAG",
                "key_points": ["retrieval"],
            },
            "messages": [],
        }
    )

    assert result["retrieved_docs"] == []
    assert result["current_step"] == "retrieval"