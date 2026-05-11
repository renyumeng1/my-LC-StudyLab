from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore

from backend.rag import vector_stores


class _FakeEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        normalized = text.lower()
        if "python" in normalized:
            return [1.0, 0.0, 0.0]
        if "langchain" in normalized:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


class _FakeVectorStore:
    def __init__(self) -> None:
        self.documents: list[Document] = []
        self.search_calls: list[dict[str, Any]] = []

    def add_documents(self, documents: list[Document]) -> None:
        self.documents.extend(documents)

    def similarity_search_with_score(
        self, *, query: str, k: int
    ) -> list[tuple[Document, float]]:
        self.search_calls.append({"query": query, "k": k})
        return [
            (Document(page_content="high score", metadata={"rank": 1}), 0.9),
            (Document(page_content="low score", metadata={"rank": 2}), 0.2),
        ]


@pytest.fixture
def sample_documents() -> list[Document]:
    return [
        Document(page_content="Python testing guide", metadata={"source": "python"}),
        Document(page_content="LangChain vector store notes", metadata={"source": "langchain"}),
        Document(page_content="Cooking notes", metadata={"source": "cooking"}),
    ]


def test_create_vector_store_builds_inmemory_store(
    sample_documents: list[Document],
) -> None:
    vector_store = vector_stores.create_vector_store(
        sample_documents,
        _FakeEmbeddings(),
        store_type="inmemory",
    )

    assert isinstance(vector_store, InMemoryVectorStore)
    results = vector_store.similarity_search_with_score("python", k=1)
    assert results[0][0].metadata["source"] == "python"


def test_create_vector_store_rejects_empty_documents() -> None:
    with pytest.raises(ValueError):
        vector_stores.create_vector_store([], _FakeEmbeddings(), store_type="inmemory")


def test_create_vector_store_rejects_unsupported_store_type(
    sample_documents: list[Document],
) -> None:
    with pytest.raises(ValueError):
        vector_stores.create_vector_store(
            sample_documents,
            _FakeEmbeddings(),
            store_type="unknown",
        )


def test_add_documents_to_vector_store_adds_non_empty_documents() -> None:
    vector_store = _FakeVectorStore()
    documents = [Document(page_content="new document")]

    vector_stores.add_documents_to_vector_store(vector_store, documents)  # type: ignore[arg-type]

    assert vector_store.documents == documents


def test_add_documents_to_vector_store_ignores_empty_documents() -> None:
    vector_store = _FakeVectorStore()

    vector_stores.add_documents_to_vector_store(vector_store, [])  # type: ignore[arg-type]

    assert vector_store.documents == []


def test_search_vector_store_applies_k_and_score_threshold() -> None:
    vector_store = _FakeVectorStore()

    results = vector_stores.search_vector_store(
        vector_store,  # type: ignore[arg-type]
        "python",
        k=2,
        score_threshold=0.5,
    )

    assert vector_store.search_calls == [{"query": "python", "k": 2}]
    assert [doc.metadata["rank"] for doc, _ in results] == [1]


def test_get_vector_store_stats_reports_store_type() -> None:
    vector_store = _FakeVectorStore()

    stats = vector_stores.get_vector_store_stats(vector_store)  # type: ignore[arg-type]

    assert stats == {"type": "_FakeVectorStore"}


def test_save_vector_store_rejects_inmemory_store(
    sample_documents: list[Document],
    tmp_path: Path,
) -> None:
    vector_store = vector_stores.create_vector_store(
        sample_documents,
        _FakeEmbeddings(),
        store_type="inmemory",
    )

    with pytest.raises(ValueError, match="InMemoryVectorStore 不支持持久化"):
        vector_stores.save_vector_store(vector_store, tmp_path / "indexes" / "memory")

    assert (tmp_path / "indexes").exists()


def test_load_vector_store_raises_for_missing_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-index"

    with pytest.raises(FileNotFoundError):
        vector_stores.load_vector_store(
            missing_path,
            _FakeEmbeddings(),
            store_type="inmemory",
        )


def test_delete_vector_store_removes_directory(tmp_path: Path) -> None:
    vector_store_path = tmp_path / "indexes" / "old-index"
    vector_store_path.mkdir(parents=True)
    (vector_store_path / "index.faiss").write_text("fake index", encoding="utf-8")

    vector_stores.delete_vector_store(vector_store_path)

    assert not vector_store_path.exists()


def test_delete_vector_store_ignores_missing_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-index"

    vector_stores.delete_vector_store(missing_path)

    assert not missing_path.exists()
