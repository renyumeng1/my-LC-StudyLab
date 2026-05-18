from __future__ import annotations

import argparse
import json
import pickle
import re
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.rag.embeddings import get_embeddings
from backend.rag.evaluation import (
    QueryEvaluation,
    aggregate_evaluations,
    evaluate_query,
    load_beir_corpus,
    load_beir_queries,
    reciprocal_rank_fusion,
)
from backend.rag.retrievers import TermOverlapReranker
from backend.rag.vector_stores import create_vector_store, load_vector_store, save_vector_store


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _index_exists(index_path: Path) -> bool:
    return (index_path / "index.faiss").exists() and (index_path / "index.pkl").exists()


def _json_ready(value: Any) -> Any:
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return value


def _query_embedding_cache_path(
    data_root: Path,
    dataset: str,
    embedding_model: str | None,
    embedding_ctx_length: int | None,
) -> Path:
    model_slug = _slugify(embedding_model or "default")
    suffix = embedding_ctx_length if embedding_ctx_length is not None else "default"
    return data_root / f"{dataset}-query-embeddings-{model_slug}-ctx{suffix}.json"


def _load_or_create_query_embeddings(
    data_root: Path,
    dataset: str,
    judgements: list[Any],
    embeddings: Any,
    embedding_model: str | None,
    embedding_ctx_length: int | None,
    query_sleep: float,
) -> dict[str, list[float]]:
    cache_path = _query_embedding_cache_path(data_root, dataset, embedding_model, embedding_ctx_length)
    vectors: dict[str, list[float]] = {}
    if cache_path.exists():
        vectors = json.loads(cache_path.read_text(encoding="utf-8"))

    cache_path.parent.mkdir(parents=True, exist_ok=True)
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


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.lower())


def _slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-").lower()


def _chunk_document(
    document: Document,
    chunk_size_chars: int,
    chunk_overlap_chars: int,
) -> list[Document]:
    doc_id = str(document.metadata["doc_id"])
    title = str(document.metadata.get("title") or "")
    content = document.page_content
    if title and content.startswith(title):
        content = content[len(title) :].lstrip()
    content = content.strip() or title

    step = chunk_size_chars - chunk_overlap_chars
    chunks: list[Document] = []
    start = 0
    chunk_index = 0
    while start < len(content):
        text = content[start : start + chunk_size_chars].strip()
        if text:
            chunk_id = f"{doc_id}::chunk-{chunk_index}"
            page_content = f"{title}\n\n{text}".strip() if title else text
            chunks.append(
                Document(
                    page_content=page_content,
                    metadata={
                        "doc_id": doc_id,
                        "source": doc_id,
                        "title": title,
                        "chunk_id": chunk_id,
                        "chunk_index": chunk_index,
                        "chunk_start": start,
                    },
                )
            )
            chunk_index += 1
        if start + chunk_size_chars >= len(content):
            break
        start += step
    return chunks


def chunk_corpus(
    corpus: list[Document],
    chunk_size_chars: int,
    chunk_overlap_chars: int,
) -> list[Document]:
    if chunk_size_chars <= 0:
        raise ValueError("chunk_size_chars must be positive")
    if chunk_overlap_chars < 0 or chunk_overlap_chars >= chunk_size_chars:
        raise ValueError("chunk_overlap_chars must be >= 0 and < chunk_size_chars")

    chunks: list[Document] = []
    for document in corpus:
        chunks.extend(_chunk_document(document, chunk_size_chars, chunk_overlap_chars))
    return chunks


def _build_or_load_dense_index(
    chunks: list[Document],
    embeddings: Any,
    index_path: Path,
    rebuild: bool,
) -> tuple[Any, bool]:
    if rebuild or not _index_exists(index_path):
        vector_store = create_vector_store(chunks, embeddings, store_type="faiss")
        save_vector_store(vector_store, index_path)
        return vector_store, True
    return load_vector_store(index_path, embeddings, store_type="faiss"), False


def _bm25_cache_path(
    index_root: Path,
    dataset: str,
    chunk_size_chars: int,
    chunk_overlap_chars: int,
) -> Path:
    return index_root / f"{dataset}-bm25-c{chunk_size_chars}-o{chunk_overlap_chars}.pkl"


def _build_or_load_bm25(
    chunks: list[Document],
    cache_path: Path,
    rebuild: bool,
) -> tuple[BM25Okapi, list[str], bool]:
    if cache_path.exists() and not rebuild:
        with cache_path.open("rb") as file:
            payload = pickle.load(file)
        return payload["bm25"], payload["chunk_ids"], False

    tokenized_corpus = [_tokenize(document.page_content) for document in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    chunk_ids = [str(document.metadata["chunk_id"]) for document in chunks]
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("wb") as file:
        pickle.dump({"bm25": bm25, "chunk_ids": chunk_ids}, file)
    return bm25, chunk_ids, True


def _chunk_ids(documents: list[Document]) -> list[str]:
    return [str(document.metadata["chunk_id"]) for document in documents]


def _unique_doc_ids_from_chunk_ids(
    ranked_chunk_ids: list[str],
    chunk_to_doc: dict[str, str],
    doc_top_k: int,
) -> list[str]:
    doc_ids: list[str] = []
    seen: set[str] = set()
    for chunk_id in ranked_chunk_ids:
        doc_id = chunk_to_doc.get(chunk_id)
        if doc_id is None or doc_id in seen:
            continue
        seen.add(doc_id)
        doc_ids.append(doc_id)
        if len(doc_ids) >= doc_top_k:
            break
    return doc_ids


def _bm25_retrieve_chunk_ids(
    bm25: BM25Okapi,
    bm25_chunk_ids: list[str],
    query: str,
    chunk_top_k: int,
) -> list[str]:
    tokens = _tokenize(query)
    if not tokens:
        return []
    scores = bm25.get_scores(tokens)
    positive_indexes = np.flatnonzero(scores > 0)
    if positive_indexes.size == 0:
        return []
    limit = min(chunk_top_k, positive_indexes.size)
    top_indexes = positive_indexes[np.argpartition(scores[positive_indexes], -limit)[-limit:]]
    ordered_indexes = top_indexes[np.argsort(scores[top_indexes])[::-1]]
    return [bm25_chunk_ids[int(index)] for index in ordered_indexes]


def _retrieve_chunk_ids_by_mode(
    vector_store: Any,
    query_vector: list[float],
    query_text: str,
    mode: str,
    chunk_top_k: int,
) -> list[str]:
    if mode == "dense_similarity":
        documents = vector_store.similarity_search_by_vector(
            query_vector,
            k=chunk_top_k,
            fetch_k=chunk_top_k,
        )
        return _chunk_ids(documents)
    if mode == "dense_mmr":
        documents = vector_store.max_marginal_relevance_search_by_vector(
            query_vector,
            k=chunk_top_k,
            fetch_k=chunk_top_k,
        )
        return _chunk_ids(documents)
    if mode == "dense_rerank":
        candidates = vector_store.similarity_search_by_vector(
            query_vector,
            k=chunk_top_k,
            fetch_k=chunk_top_k,
        )
        return _chunk_ids(TermOverlapReranker().rerank(query_text, candidates, top_k=chunk_top_k))
    raise ValueError(f"Unsupported dense mode: {mode}")


def evaluate_dataset_modes(
    judgements: list[Any],
    query_vectors: dict[str, list[float]],
    vector_store: Any,
    bm25: BM25Okapi,
    bm25_chunk_ids: list[str],
    chunk_to_doc: dict[str, str],
    modes: list[str],
    doc_top_k: int,
    chunk_top_k: int,
    rrf_k: int,
    rrf_weights: tuple[float, float],
) -> dict[str, Any]:
    mode_evaluations: dict[str, list[QueryEvaluation]] = {mode: [] for mode in modes}

    total = len(judgements)
    for index, judgement in enumerate(judgements, start=1):
        if index == 1 or index % 50 == 0 or index == total:
            print(f"evaluating query {index}/{total}", flush=True)
        dense_cache: dict[str, list[str]] = {}
        bm25_ranked = _bm25_retrieve_chunk_ids(
            bm25=bm25,
            bm25_chunk_ids=bm25_chunk_ids,
            query=judgement.query,
            chunk_top_k=chunk_top_k,
        )

        for mode in modes:
            if mode in {"dense_similarity", "dense_mmr", "dense_rerank"}:
                dense_ranked = dense_cache.get(mode)
                if dense_ranked is None:
                    dense_ranked = _retrieve_chunk_ids_by_mode(
                        vector_store=vector_store,
                        query_vector=query_vectors[judgement.query_id],
                        query_text=judgement.query,
                        mode=mode,
                        chunk_top_k=chunk_top_k,
                    )
                    dense_cache[mode] = dense_ranked
                retrieved_doc_ids = _unique_doc_ids_from_chunk_ids(
                    dense_ranked,
                    chunk_to_doc=chunk_to_doc,
                    doc_top_k=doc_top_k,
                )
            elif mode == "bm25":
                retrieved_doc_ids = _unique_doc_ids_from_chunk_ids(
                    bm25_ranked,
                    chunk_to_doc=chunk_to_doc,
                    doc_top_k=doc_top_k,
                )
            elif mode == "hybrid_rrf":
                dense_ranked = dense_cache.get("dense_similarity")
                if dense_ranked is None:
                    dense_ranked = _retrieve_chunk_ids_by_mode(
                        vector_store=vector_store,
                        query_vector=query_vectors[judgement.query_id],
                        query_text=judgement.query,
                        mode="dense_similarity",
                        chunk_top_k=chunk_top_k,
                    )
                    dense_cache["dense_similarity"] = dense_ranked
                fused = reciprocal_rank_fusion(
                    ranked_lists=[dense_ranked, bm25_ranked],
                    k=rrf_k,
                    weights=rrf_weights,
                )
                retrieved_doc_ids = _unique_doc_ids_from_chunk_ids(
                    [chunk_id for chunk_id, _ in fused],
                    chunk_to_doc=chunk_to_doc,
                    doc_top_k=doc_top_k,
                )
            else:
                raise ValueError(f"Unsupported mode: {mode}")

            mode_evaluations[mode].append(
                evaluate_query(
                    query_id=judgement.query_id,
                    retrieved_doc_ids=retrieved_doc_ids,
                    relevant_doc_ids=judgement.relevant_doc_ids,
                    k=doc_top_k,
                )
            )

    return {
        mode: _json_ready(asdict(aggregate_evaluations(evaluations, k=doc_top_k)))
        for mode, evaluations in mode_evaluations.items()
    }


def run_dataset(
    dataset: str,
    data_root: Path,
    index_root: Path,
    modes: list[str],
    doc_top_k: int,
    chunk_top_k: int,
    chunk_size_chars: int,
    chunk_overlap_chars: int,
    embedding_model: str | None,
    embedding_batch_size: int | None,
    embedding_ctx_length: int | None,
    query_sleep: float,
    include_per_query: bool,
    rebuild_dense: bool,
    rebuild_bm25: bool,
    rrf_k: int,
    dense_weight: float,
    bm25_weight: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    dataset_path = data_root / dataset
    model_slug = _slugify(embedding_model or "default")
    dense_index_path = (
        index_root
        / f"{dataset}-chunks-faiss-{model_slug}-c{chunk_size_chars}-o{chunk_overlap_chars}"
    )
    bm25_path = _bm25_cache_path(index_root, dataset, chunk_size_chars, chunk_overlap_chars)

    corpus = load_beir_corpus(dataset_path)
    judgements = load_beir_queries(dataset_path, split="test")
    chunks = chunk_corpus(corpus, chunk_size_chars, chunk_overlap_chars)
    chunk_to_doc = {
        str(document.metadata["chunk_id"]): str(document.metadata["doc_id"])
        for document in chunks
    }

    embedding_kwargs: dict[str, Any] = {
        "tiktoken_enabled": False,
        "check_embedding_ctx_length": False,
    }
    if embedding_ctx_length is not None and embedding_ctx_length > 0:
        embedding_kwargs["embedding_ctx_length"] = embedding_ctx_length
    embeddings = get_embeddings(model=embedding_model, batch_size=embedding_batch_size, **embedding_kwargs)

    vector_store, built_dense_index = _build_or_load_dense_index(
        chunks=chunks,
        embeddings=embeddings,
        index_path=dense_index_path,
        rebuild=rebuild_dense,
    )
    bm25, bm25_chunk_ids, built_bm25_index = _build_or_load_bm25(
        chunks=chunks,
        cache_path=bm25_path,
        rebuild=rebuild_bm25,
    )
    query_vectors = _load_or_create_query_embeddings(
        data_root=data_root,
        dataset=dataset,
        judgements=judgements,
        embeddings=embeddings,
        embedding_model=embedding_model,
        embedding_ctx_length=embedding_ctx_length,
        query_sleep=query_sleep,
    )
    reports = evaluate_dataset_modes(
        judgements=judgements,
        query_vectors=query_vectors,
        vector_store=vector_store,
        bm25=bm25,
        bm25_chunk_ids=bm25_chunk_ids,
        chunk_to_doc=chunk_to_doc,
        modes=modes,
        doc_top_k=doc_top_k,
        chunk_top_k=chunk_top_k,
        rrf_k=rrf_k,
        rrf_weights=(dense_weight, bm25_weight),
    )
    if not include_per_query:
        for report in reports.values():
            report.pop("per_query", None)

    elapsed_seconds = round(time.perf_counter() - started, 3)
    return {
        "dataset": dataset,
        "corpus_count": len(corpus),
        "chunk_count": len(chunks),
        "doc_top_k": doc_top_k,
        "chunk_top_k": chunk_top_k,
        "chunk_size_chars": chunk_size_chars,
        "chunk_overlap_chars": chunk_overlap_chars,
        "dense_index_path": str(dense_index_path.relative_to(PROJECT_ROOT)),
        "bm25_index_path": str(bm25_path.relative_to(PROJECT_ROOT)),
        "built_dense_index": built_dense_index,
        "built_bm25_index": built_bm25_index,
        "embedding_model": embedding_model,
        "embedding_ctx_length": embedding_ctx_length,
        "query_embedding_cache": str(
            _query_embedding_cache_path(data_root, dataset, embedding_model, embedding_ctx_length).relative_to(
                PROJECT_ROOT
            )
        ),
        "rrf_k": rrf_k,
        "rrf_weights": {"dense": dense_weight, "bm25": bm25_weight},
        "elapsed_seconds": elapsed_seconds,
        "modes": reports,
    }


def _print_table(results: list[dict[str, Any]], modes: list[str]) -> None:
    headers = ["dataset", "mode", "recall", "precision", "mrr", "ndcg"]
    print("\t".join(headers))
    for result in results:
        for mode in modes:
            report = result["modes"][mode]
            print(
                "\t".join(
                    [
                        result["dataset"],
                        mode,
                        f"{report['recall_at_k']:.4f}",
                        f"{report['precision_at_k']:.4f}",
                        f"{report['mrr_at_k']:.4f}",
                        f"{report['ndcg_at_k']:.4f}",
                    ]
                )
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", default=["scifact", "nfcorpus"])
    parser.add_argument("--data-root", type=Path, default=PROJECT_ROOT / "data" / "beir")
    parser.add_argument(
        "--index-root",
        type=Path,
        default=PROJECT_ROOT / "data" / "indexes" / "beir",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "beir" / "hybrid-chunk-comparison-k200.json",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["dense_similarity", "dense_mmr", "dense_rerank", "bm25", "hybrid_rrf"],
    )
    parser.add_argument("--doc-k", type=int, default=200)
    parser.add_argument("--chunk-top-k", type=int, default=1000)
    parser.add_argument("--chunk-size-chars", type=int, default=700)
    parser.add_argument("--chunk-overlap-chars", type=int, default=100)
    parser.add_argument("--embedding-model", type=str, default=None)
    parser.add_argument("--embedding-batch-size", type=int, default=32)
    parser.add_argument("--embedding-ctx-length", type=int, default=384)
    parser.add_argument("--query-sleep", type=float, default=0.0)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--dense-weight", type=float, default=1.0)
    parser.add_argument("--bm25-weight", type=float, default=1.0)
    parser.add_argument("--include-per-query", action="store_true")
    parser.add_argument("--rebuild-dense", action="store_true")
    parser.add_argument("--rebuild-bm25", action="store_true")
    args = parser.parse_args()

    args.index_root.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    results = [
        run_dataset(
            dataset=dataset,
            data_root=args.data_root,
            index_root=args.index_root,
            modes=args.modes,
            doc_top_k=args.doc_k,
            chunk_top_k=args.chunk_top_k,
            chunk_size_chars=args.chunk_size_chars,
            chunk_overlap_chars=args.chunk_overlap_chars,
            embedding_model=args.embedding_model,
            embedding_batch_size=args.embedding_batch_size,
            embedding_ctx_length=args.embedding_ctx_length,
            query_sleep=args.query_sleep,
            include_per_query=args.include_per_query,
            rebuild_dense=args.rebuild_dense,
            rebuild_bm25=args.rebuild_bm25,
            rrf_k=args.rrf_k,
            dense_weight=args.dense_weight,
            bm25_weight=args.bm25_weight,
        )
        for dataset in args.datasets
    ]
    payload = {
        "target": "offline_doc_level_recall_at_200_candidate_pool",
        "modes": args.modes,
        "doc_top_k": args.doc_k,
        "chunk_top_k": args.chunk_top_k,
        "chunk_size_chars": args.chunk_size_chars,
        "chunk_overlap_chars": args.chunk_overlap_chars,
        "embedding_model": args.embedding_model,
        "rrf_k": args.rrf_k,
        "rrf_weights": {"dense": args.dense_weight, "bm25": args.bm25_weight},
        "datasets": results,
    }
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _print_table(results, args.modes)


if __name__ == "__main__":
    main()
