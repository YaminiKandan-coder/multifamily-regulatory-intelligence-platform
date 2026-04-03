from __future__ import annotations
import re
from typing import Any, Optional
from pydantic import BaseModel, Field
from config import LEGAL_DISCLAIMER
from core.compliance.rules import RuleEngine, RuleResult
from core.compliance.parser import Clause
from core.rag.utils import deduplicate_sources
from core.llm.prompts import COMPLIANCE_SYSTEM_PROMPT


class ComplianceIssue(BaseModel):
    clause_number: str
    clause_title: str
    violation_type: str
    regulation_cited: str
    description: str
    fix: str
    suggested_revision: str
    severity: str = "medium"  # low | medium | high


class ComplianceResult(BaseModel):
    issues: list[ComplianceIssue] = Field(default_factory=list)
    compliant_clauses: list[str] = Field(default_factory=list)
    overall_score: float = 1.0  # 0.0 – 1.0
    sources: list[dict[str, Any]] = Field(default_factory=list)
    disclaimer: str = LEGAL_DISCLAIMER


_rule_engine = RuleEngine()


def _rule_issues_to_compliance(
    clause: Clause, rule_results: list[RuleResult]
) -> list[ComplianceIssue]:
    return [
        ComplianceIssue(
            clause_number=clause.number,
            clause_title=clause.title,
            violation_type=r.violation_type,
            regulation_cited=r.regulation_cited,
            description=r.description,
            fix=r.fix,
            suggested_revision=r.suggested_revision,
        )
        for r in rule_results
    ]


def _llm_issues_to_compliance(
    clause: Clause, raw: list[dict[str, Any]]
) -> list[ComplianceIssue]:
    issues = []
    for item in raw:
        issues.append(ComplianceIssue(
            clause_number=clause.number,
            clause_title=clause.title,
            violation_type=item.get("violation_type", "UNKNOWN"),
            regulation_cited=item.get("regulation_cited", ""),
            description=item.get("description", ""),
            fix=item.get("fix", ""),
            suggested_revision=item.get("suggested_revision", ""),
            severity=item.get("severity", "medium"),
        ))
    return issues


class ComplianceChecker:
    def __init__(self, db_client: Any, llm_client: Any) -> None:
        self._db = db_client
        self._llm = llm_client

    def check_compliance(
        self,
        clauses: list[Clause],
        jurisdiction_id: Optional[int] = None,
    ) -> ComplianceResult:
        all_issues: list[ComplianceIssue] = []
        compliant: list[str] = []
        sources: list[dict[str, Any]] = []

        for clause in clauses:
            # Rule-based check (always runs)
            rule_results = _rule_engine.check(clause.content)
            rule_issues = _rule_issues_to_compliance(clause, rule_results)

            # LLM check (if available)
            llm_issues: list[ComplianceIssue] = []
            try:
                context = self._get_regulation_context(clause.content, jurisdiction_id)
                if context:
                    user_prompt = (
                        f"Jurisdiction ID: {jurisdiction_id}\n\n"
                        f"Regulation Context:\n{context}\n\n"
                        f"Lease Clause [{clause.number}] {clause.title}:\n{clause.content}"
                    )
                    raw = self._llm.ask_json(COMPLIANCE_SYSTEM_PROMPT, user_prompt)
                    items = raw if isinstance(raw, list) else raw.get("issues", [])
                    llm_issues = _llm_issues_to_compliance(clause, items)
                    # Collect sources
                    for src in raw.get("sources", []) if isinstance(raw, dict) else []:
                        sources.append(src)
            except Exception:
                pass

            combined = rule_issues + llm_issues
            if combined:
                all_issues.extend(combined)
            else:
                compliant.append(f"{clause.number} {clause.title}".strip())

        sources = deduplicate_sources(sources)
        score = 1.0 - (len(all_issues) / max(len(clauses), 1)) * 0.5
        score = max(0.0, min(1.0, score))

        return ComplianceResult(
            issues=all_issues,
            compliant_clauses=compliant,
            overall_score=round(score, 2),
            sources=sources,
        )

    def _get_regulation_context(
        self, clause_text: str, jurisdiction_id: Optional[int]
    ) -> str:
        try:
            embedding = self._llm.embed(clause_text)
            resp = self._db.rpc(
                "match_regulations",
                {
                    "query_embedding": embedding,
                    "match_count": 5,
                    "filter_jurisdiction": jurisdiction_id,
                },
            ).execute()
            chunks = resp.data or []
            return "\n\n".join(c.get("chunk_text", "") for c in chunks)
        except Exception:
            return ""
