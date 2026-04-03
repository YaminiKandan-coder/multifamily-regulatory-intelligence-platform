from __future__ import annotations
import re
from typing import Any, Optional
from config import settings

# Citation patterns
_CITATION_RE = re.compile(
    r"(§\s*\d+|U\.S\.C\.|C\.F\.R\.|Public Law|Pub\. L\.)", re.IGNORECASE
)
_GOV_DOMAIN_RE = re.compile(r"\.(gov|us)(/|$)", re.IGNORECASE)

# Scoring weights
_WEIGHTS = {
    "jurisdiction_match": 0.30,
    "topic_relevance": 0.25,
    "citation_density": 0.20,
    "source_quality": 0.15,
    "recency": 0.10,
}


def _jurisdiction_score(chunk: dict[str, Any], jurisdiction_id: Optional[int]) -> float:
    if jurisdiction_id is None:
        return 0.5
    meta = chunk.get("metadata") or {}
    if meta.get("jurisdiction_id") == jurisdiction_id:
        return 1.0
    j_type = meta.get("jurisdiction_type", "")
    if j_type == "federal":
        return 0.7
    return 0.3


def _topic_score(chunk: dict[str, Any], query: str) -> float:
    text = (chunk.get("chunk_text") or "").lower()
    query_tokens = set(query.lower().split())
    if not query_tokens:
        return 0.0
    matches = sum(1 for t in query_tokens if t in text)
    return min(matches / len(query_tokens), 1.0)


def _citation_score(chunk: dict[str, Any]) -> float:
    text = chunk.get("chunk_text") or ""
    hits = len(_CITATION_RE.findall(text))
    return min(hits / 5.0, 1.0)


def _source_quality_score(chunk: dict[str, Any]) -> float:
    meta = chunk.get("metadata") or {}
    url = meta.get("url") or ""
    if _GOV_DOMAIN_RE.search(url):
        return 1.0
    return 0.5


def _recency_score(chunk: dict[str, Any]) -> float:
    meta = chunk.get("metadata") or {}
    if meta.get("effective_date"):
        return 0.8
    return 0.5


def _score(chunk: dict[str, Any], query: str, jurisdiction_id: Optional[int]) -> float:
    return (
        _WEIGHTS["jurisdiction_match"] * _jurisdiction_score(chunk, jurisdiction_id)
        + _WEIGHTS["topic_relevance"] * _topic_score(chunk, query)
        + _WEIGHTS["citation_density"] * _citation_score(chunk)
        + _WEIGHTS["source_quality"] * _source_quality_score(chunk)
        + _WEIGHTS["recency"] * _recency_score(chunk)
    )


def rerank_deterministic(
    chunks: list[dict[str, Any]],
    query: str,
    jurisdiction_id: Optional[int] = None,
    top_k: Optional[int] = None,
) -> list[dict[str, Any]]:
    scored = [(c, _score(c, query, jurisdiction_id)) for c in chunks]
    scored.sort(key=lambda x: x[1], reverse=True)
    result = [c for c, _ in scored]
    if top_k is not None:
        result = result[:top_k]
    return result


def rerank_llm(
    chunks: list[dict[str, Any]],
    query: str,
    jurisdiction_id: Optional[int] = None,
    top_k: Optional[int] = None,
) -> list[dict[str, Any]]:
    try:
        from core.llm.client import llm
        # Build prompt for LLM reranking
        context = "\n\n".join(
            f"[{i}] {c.get('chunk_text', '')[:300]}" for i, c in enumerate(chunks)
        )
        system = "Rank the following regulation chunks by relevance to the query. Return a JSON array of indices in order of relevance (most relevant first)."
        user = f"Query: {query}\n\nChunks:\n{context}"
        indices = llm.ask_json(system, user)
        reranked = [chunks[i] for i in indices if i < len(chunks)]
        if top_k is not None:
            reranked = reranked[:top_k]
        return reranked
    except Exception:
        return rerank_deterministic(chunks, query, jurisdiction_id, top_k)


def rerank(
    chunks: list[dict[str, Any]],
    query: str,
    jurisdiction_id: Optional[int] = None,
    top_k: Optional[int] = None,
) -> list[dict[str, Any]]:
    if settings.RAG_LLM_RERANK_ENABLED:
        return rerank_llm(chunks, query, jurisdiction_id, top_k)
    return rerank_deterministic(chunks, query, jurisdiction_id, top_k)
