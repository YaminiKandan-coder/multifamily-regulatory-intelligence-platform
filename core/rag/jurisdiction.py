from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional

# Hierarchy order: lower number = broader scope
_HIERARCHY_ORDER = {"federal": 0, "state": 1, "county": 2, "city": 3}

_COMPARISON_PHRASES = [
    "compare", "vs", "versus", "difference between", "both", "either",
    "in california and", "in texas and", "in new york and",
]


@dataclass
class ScopedJurisdiction:
    id: int
    type: str
    name: str
    parent_id: Optional[int] = None
    state_code: Optional[str] = None

    @property
    def scope_label(self) -> str:
        return f"{self.name} ({self.type})"


def resolve_hierarchy(jurisdiction: ScopedJurisdiction, all_jurisdictions: list[ScopedJurisdiction]) -> list[ScopedJurisdiction]:
    """Return ordered search list from jurisdiction up through parents + federal."""
    result: list[ScopedJurisdiction] = [jurisdiction]
    by_id = {j.id: j for j in all_jurisdictions}

    current = jurisdiction
    while current.parent_id is not None:
        parent = by_id.get(current.parent_id)
        if parent is None:
            break
        result.append(parent)
        current = parent

    # Always include federal
    federal = [j for j in all_jurisdictions if j.type == "federal"]
    for f in federal:
        if f.id not in {j.id for j in result}:
            result.append(f)

    return result


def build_retrieval_plan(
    jurisdictions: list[ScopedJurisdiction],
) -> dict[str, Any]:
    if len(jurisdictions) == 1:
        return {"mode": "single", "jurisdiction_ids": [jurisdictions[0].id]}
    return {
        "mode": "cross",
        "jurisdiction_ids": [j.id for j in jurisdictions],
    }


def detect_jurisdiction_conflicts(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in _COMPARISON_PHRASES)
