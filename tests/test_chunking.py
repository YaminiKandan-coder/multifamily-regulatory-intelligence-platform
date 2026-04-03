from __future__ import annotations
import pytest
from core.rag.chunking import chunk_legal_text, _sliding_window_chunks, ChunkMeta
from core.rag.reranker import rerank_deterministic


def test_sliding_window_basic():
    text = "word " * 400  # 2000 chars
    chunks = _sliding_window_chunks(text)
    assert len(chunks) >= 2
    for chunk_text, meta in chunks:
        assert isinstance(meta, ChunkMeta)
        assert len(chunk_text) <= 900  # CHUNK_SIZE + some tolerance


def test_section_boundary_detection():
    text = (
        "Section 1. General Provisions\n"
        "All tenants must comply with local regulations.\n\n"
        "Section 2. Pet Policy\n"
        "No pets allowed except as required by law.\n\n"
        "Section 3. Security Deposit\n"
        "A deposit of one month's rent is required.\n"
    )
    chunks = chunk_legal_text(text)
    assert len(chunks) >= 2
    titles = [meta.section_title for _, meta in chunks]
    assert any("Section" in t for t in titles)


def test_article_boundary_detection():
    text = (
        "ARTICLE I. LEASE TERM\nThe lease begins on January 1.\n\n"
        "ARTICLE II. RENT PAYMENT\nRent is due on the first of each month.\n"
    )
    chunks = chunk_legal_text(text)
    assert len(chunks) >= 1


def test_legal_chunking_definitions_flag():
    text = "Section 1. Definitions\n\"Tenant\" means the person named above.\n"
    chunks = chunk_legal_text(text)
    assert any(meta.has_definitions for _, meta in chunks)


def test_legal_chunking_effective_date_flag():
    text = "Section 2. Term\nEffective January 1, 2025, this lease is in force.\n"
    chunks = chunk_legal_text(text)
    assert any(meta.has_effective_date for _, meta in chunks)


def test_oversized_section_subsplits():
    # Section larger than CHUNK_SIZE should be sub-split
    long_section = "Section 1. Long Section\n" + "word " * 500
    chunks = chunk_legal_text(long_section)
    assert len(chunks) >= 2


def test_sequential_indices():
    text = "Section 1. A\n" + "word " * 100 + "\nSection 2. B\n" + "word " * 100
    chunks = chunk_legal_text(text)
    indices = [meta.chunk_index for _, meta in chunks]
    assert indices == list(range(len(chunks)))


def test_reranker_smoke():
    chunks = [
        {"id": 1, "chunk_text": "ESA deposit rules under Fair Housing Act § 3604", "metadata": {"jurisdiction_id": 1, "url": "https://hud.gov/esa"}},
        {"id": 2, "chunk_text": "General pet policy information", "metadata": {"jurisdiction_id": 2, "url": ""}},
    ]
    result = rerank_deterministic(chunks, query="ESA deposit", jurisdiction_id=1, top_k=2)
    assert len(result) == 2
    # ESA chunk should rank first
    assert result[0]["id"] == 1
