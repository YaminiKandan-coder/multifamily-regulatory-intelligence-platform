from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class RuleResult:
    violation_type: str
    regulation_cited: str
    description: str
    fix: str
    suggested_revision: str


class RuleEngine:
    """Regex-based compliance rule engine. Works with zero API keys."""

    # ESA / Fair Housing
    _ESA_FEE_RE = re.compile(
        r"(emotional\s+support|ESA|assistance\s+animal).{0,80}(fee|deposit|charge|payment)",
        re.IGNORECASE | re.DOTALL,
    )
    _ESA_EXEMPTION_RE = re.compile(
        r"(reasonable\s+accommodation|fair\s+housing|ESA\s+exempt|assistance\s+animal\s+exempt)",
        re.IGNORECASE,
    )

    # Security deposit return timeline
    _DEPOSIT_RETURN_RE = re.compile(
        r"(security\s+deposit).{0,120}(return|refund)",
        re.IGNORECASE | re.DOTALL,
    )
    _DEPOSIT_DAYS_RE = re.compile(r"\b(\d+)\s*days?\b", re.IGNORECASE)

    # Late fees
    _LATE_FEE_RE = re.compile(
        r"late\s+(fee|charge|penalty).{0,60}\$\s*(\d+)",
        re.IGNORECASE | re.DOTALL,
    )

    # Rent increase caps
    _RENT_INCREASE_RE = re.compile(
        r"rent\s+(increase|raise).{0,60}(\d+)\s*%",
        re.IGNORECASE | re.DOTALL,
    )

    def check(self, clause_text: str) -> list[RuleResult]:
        results: list[RuleResult] = []
        results.extend(self._check_esa(clause_text))
        results.extend(self._check_deposit(clause_text))
        results.extend(self._check_late_fee(clause_text))
        results.extend(self._check_rent_increase(clause_text))
        return results

    def _check_esa(self, text: str) -> list[RuleResult]:
        violations: list[RuleResult] = []
        if self._ESA_FEE_RE.search(text) and not self._ESA_EXEMPTION_RE.search(text):
            violations.append(RuleResult(
                violation_type="ESA_FEE_VIOLATION",
                regulation_cited="Fair Housing Act, 42 U.S.C. § 3604; HUD Guidance 2020",
                description="Clause charges a fee for emotional support animals, which is prohibited under federal Fair Housing Act.",
                fix="Remove any fee, deposit, or charge requirement for ESA tenants.",
                suggested_revision="Tenant with a verified ESA under the Fair Housing Act shall not be charged a pet fee, deposit, or additional rent for the ESA.",
            ))
        return violations

    def _check_deposit(self, text: str) -> list[RuleResult]:
        violations: list[RuleResult] = []
        if self._DEPOSIT_RETURN_RE.search(text):
            days_matches = self._DEPOSIT_DAYS_RE.findall(text)
            for days_str in days_matches:
                days = int(days_str)
                if days > 30:
                    violations.append(RuleResult(
                        violation_type="DEPOSIT_RETURN_TIMELINE",
                        regulation_cited="Texas Property Code § 92.103 (21 days); varies by state",
                        description=f"Clause specifies {days} days to return security deposit, which may exceed state law limits.",
                        fix="Reduce the deposit return timeline to comply with applicable state law (e.g., 21 days in Texas).",
                        suggested_revision="Landlord shall return the security deposit within 21 days of tenant vacating the premises.",
                    ))
        return violations

    def _check_late_fee(self, text: str) -> list[RuleResult]:
        violations: list[RuleResult] = []
        for m in self._LATE_FEE_RE.finditer(text):
            amount = int(m.group(2))
            if amount >= 100:
                violations.append(RuleResult(
                    violation_type="UNREASONABLE_LATE_FEE",
                    regulation_cited="General reasonableness standard; state-specific caps may apply",
                    description=f"Late fee of ${amount} may be unreasonably high and unenforceable.",
                    fix="Reduce late fee to a reasonable amount (typically 5% of monthly rent or a fixed lower amount).",
                    suggested_revision=f"A late fee of no more than 5% of the monthly rent shall be charged for payments received after the grace period.",
                ))
        return violations

    def _check_rent_increase(self, text: str) -> list[RuleResult]:
        violations: list[RuleResult] = []
        for m in self._RENT_INCREASE_RE.finditer(text):
            pct = int(m.group(2))
            if pct > 10:
                violations.append(RuleResult(
                    violation_type="RENT_INCREASE_CAP",
                    regulation_cited="California AB 1482 (5% + CPI, max 10%); local ordinances may apply",
                    description=f"Rent increase of {pct}% may exceed statutory caps in rent-controlled jurisdictions.",
                    fix="Verify applicable rent increase cap for the jurisdiction and reduce if necessary.",
                    suggested_revision=f"Rent increases shall not exceed the maximum allowed by applicable local or state law.",
                ))
        return violations
