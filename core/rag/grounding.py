from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class GroundedAnswer:
    answer: str
    confidence: str  # grounded | weak_evidence | conflicting | out_of_scope
    sources: list[dict[str, Any]] = field(default_factory=list)
    uncertainty_prefix: str = ""


def assess_confidence(chunks: list[dict[str, Any]], answer: str) -> str:
    if not chunks:
        return "out_of_scope"
    if len(chunks) >= 2 and len(answer) >= 220:
        return "grounded"
    if len(chunks) == 1:
        return "weak_evidence"
    # Heuristic: detect conflicting signals
    jurisdictions = {c.get("metadata", {}).get("jurisdiction_id") for c in chunks if c.get("metadata")}
    if len(jurisdictions) > 2:
        return "conflicting"
    return "weak_evidence"


def format_uncertainty_prefix(confidence: str) -> str:
    if confidence == "grounded":
        return ""
    if confidence == "weak_evidence":
        return "Based on limited available information: "
    if confidence == "conflicting":
        return "Note: sources may conflict across jurisdictions. "
    return "This topic may be outside the available regulation database. "


def extract_sources(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = []
    for chunk in chunks:
        meta = chunk.get("metadata") or {}
        source = {
            "source": meta.get("source_name", "Unknown"),
            "url": meta.get("url", ""),
            "category": meta.get("category", ""),
        }
        sources.append(source)
    return sources


def build_grounded_context(chunks: list[dict[str, Any]]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata") or {}
        label = meta.get("source_name", f"Source {i}")
        jurisdiction = meta.get("jurisdiction_id", "")
        parts.append(f"[{label} | jurisdiction_id={jurisdiction}]\n{chunk.get('chunk_text', '')}")
    return "\n\n---\n\n".join(parts)


def build_grounded_answer(
    answer: str,
    chunks: list[dict[str, Any]],
) -> GroundedAnswer:
    confidence = assess_confidence(chunks, answer)
    prefix = format_uncertainty_prefix(confidence)
    sources = extract_sources(chunks)
    return GroundedAnswer(
        answer=answer,
        confidence=confidence,
        sources=sources,
        uncertainty_prefix=prefix,
    )
