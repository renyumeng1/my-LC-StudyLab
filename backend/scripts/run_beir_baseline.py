from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from langchain_core.documents import Document

from backend.rag.embeddings import get_embeddings
from backend.rag.evaluation import (
    QueryEvaluation,
    aggregate_evaluations,
    evaluate_query,
    load_beir_corpus,
    load_beir_queries,
)
from backend.rag.retrievers import TermOverlapReranker
from backend.rag.vector_stores import create_vector_store, load_vector_store, save_vector_store


def _index_exists(index_path: Path) -> bool:
    return (index_path / "index.faiss").exists() and (index_path / "index.pkl").exists()


def _truncate_documents(documents: list[Any], max_chars: int | None) -> list[Any]:
    if max_chars is None or max_chars <= 0:
        return documents

    for document in documents:
        if len(document.page_content) > max_chars:
            document.page_content = document.page_content[:max_chars]
    return documents


def _json_ready(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def _query_embedding_cache_path(
    data_root: Path,
    dataset: str,
    embedding_ctx_length: int | None,
) -> Path:
    suffix = embedding_ctx_length if embedding_ctx_length is not None else "default"
    return data_root / f"{dataset}-query-embeddings-ctx{suffix}.json"


def _load_or_create_query_embeddings(
    data_root: Path,
    dataset: str,
    judgements: list[Any],
    embeddings: Any,
    embedding_ctx_length: int | None,
    query_sleep: float,
) -> dict[str, list[float]]:
    cache_path = _query_embedding_cache_path(data_root, dataset, embedding_ctx_length)
    vectors: dict[str, list[float]] = {}
    if cache_path.exists():
        vectors = json.loads(cache_path.read_text(encoding="utf-8"))

    for judgement in judgements:
        if judgement.query_id in vectors:
            continue
        vectors[judgement.query_id] = embeddings.embed_query(judgement.query)
        cache_path.write_text(
            json.dumps(vectors, ensure_ascii=False),
            encoding="utf-8",
        )
        if query_sleep > 0:
            time.sleep(query_sleep)
    return vectors


def _extract_doc_ids(documents: list[Document], k: int) -> list[str]:
    doc_ids = []
    for document in documents[:k]:
        doc_id = document.metadata.get("doc_id")
        if doc_id is not None:
            doc_ids.append(str(doc_id))
    return doc_ids


def _retrieve_by_mode(
    vector_store: Any,
    query_vector: list[float],
    query_text: str,
    mode: str,
    k: int,
    fetch_k: int,
    candidate_k: int | None,
) -> list[Document]:
    if mode == "similarity":
        return vector_store.similarity_search_by_vector(query_vector, k=k, fetch_k=fetch_k)
    if mode == "mmr":
        return vector_store.max_marginal_relevance_search_by_vector(
            query_vector,
            k=k,
            fetch_k=fetch_k,
        )
    if mode == "rerank":
        candidates = vector_store.similarity_search_by_vector(
            query_vector,
            k=candidate_k or fetch_k,
            fetch_k=max(fetch_k, candidate_k or fetch_k),
        )
        return TermOverlapReranker().rerank(query_text, candidates, top_k=k)
    raise ValueError(f"Unsupported retrieval mode: {mode}")


def evaluate_vector_store(
    vector_store: Any,
    judgements: list[Any],
    query_vectors: dict[str, list[float]],
    mode: str,
    k: int,
    fetch_k: int,
    candidate_k: int | None,
) -> Any:
    per_query: list[QueryEvaluation] = []
    for judgement in judgements:
        documents = _retrieve_by_mode(
            vector_store=vector_store,
            query_vector=query_vectors[judgement.query_id],
            query_text=judgement.query,
            mode=mode,
            k=k,
            fetch_k=fetch_k,
            candidate_k=candidate_k,
        )
        per_query.append(
            evaluate_query(
                query_id=judgement.query_id,
                retrieved_doc_ids=_extract_doc_ids(documents, k),
                relevant_doc_ids=judgement.relevant_doc_ids,
                k=k,
            )
        )
    return aggregate_evaluations(per_query, k=k)


def run_dataset(
    dataset: str,
    data_root: Path,
    index_root: Path,
    k: int,
    retrieval_mode: str,
    fetch_k: int,
    candidate_k: int | None,
    embedding_batch_size: int | None,
    embedding_ctx_length: int | None,
    max_doc_chars: int | None,
    include_per_query: bool,
    query_sleep: float,
    rebuild: bool,
) -> dict[str, Any]:
    dataset_path = data_root / dataset
    index_path = index_root / f"{dataset}-faiss"

    started = time.perf_counter()
    corpus = _truncate_documents(load_beir_corpus(dataset_path), max_doc_chars)
    judgements = load_beir_queries(dataset_path, split="test")
    embedding_kwargs: dict[str, Any] = {
        "tiktoken_enabled": False,
        "check_embedding_ctx_length": False,
    }
    if embedding_ctx_length is not None and embedding_ctx_length > 0:
        embedding_kwargs["embedding_ctx_length"] = embedding_ctx_length
    embeddings = get_embeddings(batch_size=embedding_batch_size, **embedding_kwargs)

    built_index = False
    if rebuild or not _index_exists(index_path):
        vector_store = create_vector_store(corpus, embeddings, store_type="faiss")
        save_vector_store(vector_store, index_path)
        built_index = True
    else:
        vector_store = load_vector_store(index_path, embeddings, store_type="faiss")

    query_vectors = _load_or_create_query_embeddings(
        data_root=data_root,
        dataset=dataset,
        judgements=judgements,
        embeddings=embeddings,
        embedding_ctx_length=embedding_ctx_length,
        query_sleep=query_sleep,
    )
    report = evaluate_vector_store(
        vector_store=vector_store,
        judgements=judgements,
        query_vectors=query_vectors,
        mode=retrieval_mode,
        k=k,
        fetch_k=fetch_k,
        candidate_k=candidate_k,
    )

    elapsed_seconds = round(time.perf_counter() - started, 3)
    result = _json_ready(asdict(report))
    if not include_per_query:
        result.pop("per_query", None)
    result.update(
        {
            "dataset": dataset,
            "corpus_count": len(corpus),
            "index_path": str(index_path.relative_to(PROJECT_ROOT)),
            "built_index": built_index,
            "retrieval_mode": retrieval_mode,
            "query_embedding_cache": str(
                _query_embedding_cache_path(data_root, dataset, embedding_ctx_length).relative_to(PROJECT_ROOT)
            ),
            "candidate_k": candidate_k,
            "embedding_ctx_length": embedding_ctx_length,
            "max_doc_chars": max_doc_chars,
            "elapsed_seconds": elapsed_seconds,
        }
    )
    return result


def run_dataset_modes(
    dataset: str,
    modes: list[str],
    data_root: Path,
    index_root: Path,
    k: int,
    fetch_k: int,
    candidate_k: int | None,
    embedding_batch_size: int | None,
    embedding_ctx_length: int | None,
    max_doc_chars: int | None,
    include_per_query: bool,
    query_sleep: float,
    rebuild: bool,
) -> list[dict[str, Any]]:
    results = []
    for index, mode in enumerate(modes):
        results.append(
            run_dataset(
                dataset=dataset,
                data_root=data_root,
                index_root=index_root,
                k=k,
                retrieval_mode=mode,
                fetch_k=fetch_k,
                candidate_k=candidate_k,
                embedding_batch_size=embedding_batch_size,
                embedding_ctx_length=embedding_ctx_length,
                max_doc_chars=max_doc_chars,
                include_per_query=include_per_query,
                query_sleep=query_sleep,
                rebuild=rebuild and index == 0,
            )
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", default=["scifact", "nfcorpus"])
    parser.add_argument("--data-root", type=Path, default=PROJECT_ROOT / "data" / "beir")
    parser.add_argument(
        "--index-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "indexes" / "beir",
    )
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "beir" / "retrieval-comparison.json")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--modes", nargs="+", default=["similarity"])
    parser.add_argument("--fetch-k", type=int, default=20)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--embedding-batch-size", type=int, default=32)
    parser.add_argument("--embedding-ctx-length", type=int, default=512)
    parser.add_argument("--max-doc-chars", type=int, default=1500)
    parser.add_argument("--query-sleep", type=float, default=0.0)
    parser.add_argument("--include-per-query", action="store_true")
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()

    args.index_root.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    results = []
    for dataset in args.datasets:
        results.extend(
            run_dataset_modes(
                dataset=dataset,
                modes=args.modes,
                data_root=args.data_root,
                index_root=args.index_root,
                k=args.k,
                fetch_k=args.fetch_k,
                candidate_k=args.candidate_k,
                embedding_batch_size=args.embedding_batch_size,
                embedding_ctx_length=args.embedding_ctx_length,
                max_doc_chars=args.max_doc_chars,
                include_per_query=args.include_per_query,
                query_sleep=args.query_sleep,
                rebuild=args.rebuild,
            )
        )

    payload = {
        "k": args.k,
        "modes": args.modes,
        "embedding_ctx_length": args.embedding_ctx_length,
        "max_doc_chars": args.max_doc_chars,
        "datasets": results,
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
