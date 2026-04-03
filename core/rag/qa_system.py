from __future__ import annotations
from typing import Any, Optional
from config import settings, LEGAL_DISCLAIMER
from core.rag.hybrid import hybrid_search
from core.rag.reranker import rerank
from core.rag.grounding import build_grounded_answer, build_grounded_context, GroundedAnswer
from core.rag.utils import deduplicate_sources
from core.rag.jurisdiction import detect_jurisdiction_conflicts
from core.llm.prompts import QA_SYSTEM_PROMPT

_SCOPE_KEYWORDS = {
    "rent", "lease", "tenant", "landlord", "eviction", "deposit", "pet",
    "esa", "section 8", "housing", "habitability", "notice", "repair",
    "discrimination", "fair housing", "regulation", "law", "code",
    "insurance", "renter", "rental",
}


def _is_in_scope(query: str) -> bool:
    lower = query.lower()
    return any(kw in lower for kw in _SCOPE_KEYWORDS)


def _resolve_followup(query: str, history: list[dict[str, str]]) -> str:
    """Expand follow-up questions using conversation history."""
    pronouns = {"it", "this", "that", "they", "them", "those", "these"}
    tokens = set(query.lower().split())
    if not tokens.intersection(pronouns):
        return query
    # Prepend last user message as context
    for turn in reversed(history):
        if turn.get("role") == "user":
            return f"{turn['content']} — {query}"
    return query


def _sanitize_answer(answer: str) -> str:
    if LEGAL_DISCLAIMER.lower() not in answer.lower():
        answer = answer.rstrip() + f"\n\n{LEGAL_DISCLAIMER}"
    return answer


class QASystem:
    def __init__(self, db_client: Any, llm_client: Any) -> None:
        self._db = db_client
        self._llm = llm_client

    def answer(
        self,
        query: str,
        jurisdiction_id: Optional[int] = None,
        history: Optional[list[dict[str, str]]] = None,
        top_k: Optional[int] = None,
    ) -> GroundedAnswer:
        history = history or []
        top_n = settings.RAG_RETRIEVAL_TOP_N
        top_k = top_k or settings.RAG_RERANK_TOP_K

        if not _is_in_scope(query):
            from core.rag.grounding import GroundedAnswer
            return GroundedAnswer(
                answer="This question appears to be outside the scope of US housing regulations.",
                confidence="out_of_scope",
                sources=[],
                uncertainty_prefix="",
            )

        resolved_query = _resolve_followup(query, history)
        is_cross_jurisdiction = detect_jurisdiction_conflicts(resolved_query)

        try:
            embedding = self._llm.embed(resolved_query)
        except Exception:
            embedding = None

        chunks: list[dict[str, Any]] = []
        if embedding is not None:
            chunks = hybrid_search(
                query=resolved_query,
                query_embedding=embedding,
                db_client=self._db,
                top_n=top_n,
                jurisdiction_id=None if is_cross_jurisdiction else jurisdiction_id,
            )

        # Fallback: broaden search
        if not chunks and jurisdiction_id is not None:
            if embedding is not None:
                chunks = hybrid_search(
                    query=resolved_query,
                    query_embedding=embedding,
                    db_client=self._db,
                    top_n=top_n,
                    jurisdiction_id=None,
                )

        reranked = rerank(
            chunks,
            query=resolved_query,
            jurisdiction_id=jurisdiction_id,
            top_k=top_k,
        )

        # Diversify sources
        seen_sources: set[str] = set()
        diverse: list[dict[str, Any]] = []
        for chunk in reranked:
            src = (chunk.get("metadata") or {}).get("source_name", "")
            if src not in seen_sources or len(diverse) < 2:
                diverse.append(chunk)
                seen_sources.add(src)

        context = build_grounded_context(diverse)

        if not context.strip():
            return GroundedAnswer(
                answer=f"No regulation information was found for this query. {LEGAL_DISCLAIMER}",
                confidence="out_of_scope",
                sources=[],
                uncertainty_prefix="",
            )

        try:
            user_prompt = f"Context:\n{context}\n\nQuestion: {resolved_query}"
            raw_answer = self._llm.ask(QA_SYSTEM_PROMPT, user_prompt)
        except Exception:
            raw_answer = f"Unable to generate an answer at this time. {LEGAL_DISCLAIMER}"

        answer = _sanitize_answer(raw_answer)
        grounded = build_grounded_answer(answer, diverse)
        grounded.sources = deduplicate_sources(grounded.sources)
        return grounded


# Global singleton — initialized lazily
_qa_instance: Optional[QASystem] = None


def get_qa() -> QASystem:
    global _qa_instance
    if _qa_instance is None:
        from db.client import get_db
        from core.llm.client import llm
        _qa_instance = QASystem(db_client=get_db(), llm_client=llm)
    return _qa_instance


qa = get_qa  # callable alias
