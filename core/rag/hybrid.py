from __future__ import annotations
import re
from typing import Any, Optional
from config import settings


def _build_tsquery(text: str) -> str:
    tokens = re.findall(r"\w+", text.lower())
    stop_words = {"the", "a", "an", "is", "in", "of", "and", "or", "for", "to", "with"}
    tokens = [t for t in tokens if t not in stop_words and len(t) > 2]
    return " & ".join(tokens) if tokens else text


def _rrf_score(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)


def _fuse_results(
    vector_results: list[dict[str, Any]],
    keyword_results: list[dict[str, Any]],
    vector_weight: float,
) -> list[dict[str, Any]]:
    scores: dict[int, float] = {}
    chunks: dict[int, dict[str, Any]] = {}

    keyword_weight = 1.0 - vector_weight

    for rank, chunk in enumerate(vector_results):
        cid = chunk.get("id", rank)
        scores[cid] = scores.get(cid, 0.0) + vector_weight * _rrf_score(rank)
        chunks[cid] = chunk

    for rank, chunk in enumerate(keyword_results):
        cid = chunk.get("id", rank)
        scores[cid] = scores.get(cid, 0.0) + keyword_weight * _rrf_score(rank)
        chunks[cid] = chunk

    sorted_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    return [chunks[cid] for cid in sorted_ids]


def _python_keyword_fallback(
    query: str, chunks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    tokens = set(re.findall(r"\w+", query.lower()))
    scored = []
    for chunk in chunks:
        text = (chunk.get("chunk_text") or "").lower()
        overlap = sum(1 for t in tokens if t in text)
        scored.append((chunk, overlap))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored]


def hybrid_search(
    query: str,
    query_embedding: list[float],
    db_client: Any,
    top_n: int,
    jurisdiction_id: Optional[int] = None,
    vector_weight: Optional[float] = None,
) -> list[dict[str, Any]]:
    if vector_weight is None:
        vector_weight = settings.RAG_HYBRID_VECTOR_WEIGHT

    # Vector search via pgvector
    try:
        vec_response = db_client.rpc(
            "match_regulations_v3",
            {
                "query_embedding": query_embedding,
                "match_count": top_n,
                "jurisdiction_ids": [jurisdiction_id] if jurisdiction_id else None,
            },
        ).execute()
        vector_results = vec_response.data or []
    except Exception:
        try:
            vec_response = db_client.rpc(
                "match_regulations",
                {
                    "query_embedding": query_embedding,
                    "match_count": top_n,
                    "filter_jurisdiction": jurisdiction_id,
                },
            ).execute()
            vector_results = vec_response.data or []
        except Exception:
            vector_results = []

    if not settings.RAG_HYBRID_ENABLED:
        return vector_results

    # Keyword search via Postgres full-text
    try:
        kw_response = db_client.rpc(
            "match_regulations_lexical",
            {
                "query_text": query,
                "match_count": top_n,
                "filter_jurisdiction": jurisdiction_id,
            },
        ).execute()
        keyword_results = kw_response.data or []
    except Exception:
        keyword_results = _python_keyword_fallback(query, vector_results)

    return _fuse_results(vector_results, keyword_results, vector_weight)
