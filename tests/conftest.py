from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch


# Hardcoded test data: Federal, Texas, Dallas, Houston
FAKE_JURISDICTIONS = [
    {"id": 1, "type": "federal", "name": "Federal", "parent_id": None, "state_code": None},
    {"id": 2, "type": "state",   "name": "Texas",   "parent_id": None, "state_code": "TX"},
    {"id": 3, "type": "city",    "name": "Dallas",  "parent_id": 2,    "state_code": "TX"},
    {"id": 4, "type": "city",    "name": "Houston", "parent_id": 2,    "state_code": "TX"},
]

FAKE_ESA_CHUNKS = [
    {
        "id": 1,
        "chunk_text": (
            "Under the Fair Housing Act, 42 U.S.C. § 3604, landlords may not charge "
            "a fee or deposit for emotional support animals (ESA). Reasonable accommodation "
            "must be provided. HUD guidance (2020) confirms ESA exemption from pet fees."
        ),
        "similarity": 0.92,
        "metadata": {
            "jurisdiction_id": 1,
            "jurisdiction_type": "federal",
            "source_name": "HUD Fair Housing Guidelines",
            "url": "https://www.hud.gov/program_offices/fair_housing",
            "category": "Fair Housing",
        },
    },
    {
        "id": 2,
        "chunk_text": (
            "Texas Property Code § 92.103: Landlord must return security deposit within "
            "21 days of tenant vacating. Failure subjects landlord to penalty of $100 "
            "plus three times the wrongfully withheld amount, plus attorney fees."
        ),
        "similarity": 0.85,
        "metadata": {
            "jurisdiction_id": 2,
            "jurisdiction_type": "state",
            "source_name": "Texas Property Code",
            "url": "https://statutes.capitol.texas.gov/Docs/PR/htm/PR.92.htm",
            "category": "Security Deposit",
        },
    },
]


class FakeSupabaseResponse:
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count or 0


class FakeSupabaseClient:
    """In-memory fake Supabase client for testing."""

    def rpc(self, fn_name: str, params: dict):
        mock = MagicMock()
        mock.execute.return_value = FakeSupabaseResponse(data=FAKE_ESA_CHUNKS)
        return mock

    def table(self, name: str):
        mock = MagicMock()
        mock.select.return_value = mock
        mock.insert.return_value = mock
        mock.update.return_value = mock
        mock.delete.return_value = mock
        mock.upsert.return_value = mock
        mock.eq.return_value = mock
        mock.in_.return_value = mock
        mock.limit.return_value = mock
        mock.range.return_value = mock
        mock.order.return_value = mock
        mock.single.return_value = mock
        mock.execute.return_value = FakeSupabaseResponse(data=FAKE_JURISDICTIONS)
        return mock


@pytest.fixture
def mock_supabase_client():
    client = FakeSupabaseClient()
    with patch("db.client.get_db", return_value=client), \
         patch("core.rag.qa_system.get_qa") as mock_qa_factory, \
         patch("core.rag.hybrid.hybrid_search") as mock_hybrid:
        mock_hybrid.return_value = FAKE_ESA_CHUNKS
        yield client, mock_hybrid, mock_qa_factory
