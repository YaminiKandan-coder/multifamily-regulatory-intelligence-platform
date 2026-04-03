from __future__ import annotations
import pytest
from core.compliance.rules import RuleEngine


@pytest.fixture
def engine():
    return RuleEngine()


def test_esa_fee_detection(engine):
    clause = "Tenant must pay a $500 deposit for emotional support animals."
    results = engine.check(clause)
    assert any(r.violation_type == "ESA_FEE_VIOLATION" for r in results)


def test_missing_esa_exemption(engine):
    clause = "All pets including ESA require a monthly fee of $50."
    results = engine.check(clause)
    assert any(r.violation_type == "ESA_FEE_VIOLATION" for r in results)


def test_compliant_esa_clause(engine):
    clause = (
        "Reasonable accommodation is provided for emotional support animals under the "
        "Fair Housing Act. ESA are exempt from pet deposits and fees."
    )
    results = engine.check(clause)
    assert not any(r.violation_type == "ESA_FEE_VIOLATION" for r in results)


def test_deposit_timeline_violation(engine):
    clause = "Landlord will return the security deposit within 45 days of move-out."
    results = engine.check(clause)
    assert any(r.violation_type == "DEPOSIT_RETURN_TIMELINE" for r in results)
