from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch
from tests.conftest import FakeSupabaseClient, FAKE_ESA_CHUNKS
from core.rag.qa_system import QASystem
from core.rag.grounding import GroundedAnswer


def _make_qa(db=None, llm=None):
    if db is None:
        db = FakeSupabaseClient()
    if llm is None:
        llm = MagicMock()
        llm.embed.return_value = [0.1] * 3072
        llm.ask.return_value = (
            "ESA tenants cannot be charged a pet fee under the Fair Housing Act. "
            "This is for informational purposes only and is not legal advice."
        )
    return QASystem(db_client=db, llm_client=llm)


def test_qa_answer_non_empty():
    with patch("core.rag.qa_system.hybrid_search", return_value=FAKE_ESA_CHUNKS):
        qa = _make_qa()
        result = qa.answer("Can a landlord charge an ESA fee?", jurisdiction_id=3)
    assert result.answer
    assert len(result.answer) > 10


def test_qa_empty_result_fallback():
    with patch("core.rag.qa_system.hybrid_search", return_value=[]):
        qa = _make_qa()
        result = qa.answer("Can a landlord charge an ESA fee?")
    assert result.confidence in ("out_of_scope", "weak_evidence")


def test_qa_jurisdiction_scoping():
    captured = {}

    def fake_hybrid(query, query_embedding, db_client, top_n, jurisdiction_id=None):
        captured["jurisdiction_id"] = jurisdiction_id
        return FAKE_ESA_CHUNKS

    with patch("core.rag.qa_system.hybrid_search", side_effect=fake_hybrid):
        qa = _make_qa()
        qa.answer("ESA rules", jurisdiction_id=3)  # Dallas

    assert captured.get("jurisdiction_id") == 3


def test_qa_out_of_scope():
    qa = _make_qa()
    result = qa.answer("What is the best pizza restaurant?")
    assert result.confidence == "out_of_scope"


def test_qa_confidence_field_present():
    with patch("core.rag.qa_system.hybrid_search", return_value=FAKE_ESA_CHUNKS):
        qa = _make_qa()
        result = qa.answer("ESA deposit rules", jurisdiction_id=1)
    assert hasattr(result, "confidence")
    assert result.confidence in ("grounded", "weak_evidence", "conflicting", "out_of_scope")


def test_qa_rule_based_fallback_no_keys():
    llm = MagicMock()
    llm.embed.side_effect = Exception("No API key")
    with patch("core.rag.qa_system.hybrid_search", return_value=[]):
        qa = _make_qa(llm=llm)
        result = qa.answer("Can landlord charge ESA fee?")
    assert result.answer


def test_reranking_preserves_top_results():
    from core.rag.reranker import rerank_deterministic
    chunks = FAKE_ESA_CHUNKS * 3
    result = rerank_deterministic(chunks, query="ESA", jurisdiction_id=1, top_k=2)
    assert len(result) == 2
