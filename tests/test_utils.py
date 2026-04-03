from __future__ import annotations
from core.rag.utils import deduplicate_sources


def test_deduplicate_by_url():
    sources = [
        {"url": "https://example.com/reg1", "source": "Source A"},
        {"url": "https://example.com/reg1", "source": "Source A duplicate"},
        {"url": "https://example.com/reg2", "source": "Source B"},
    ]
    result = deduplicate_sources(sources)
    assert len(result) == 2
    urls = [r["url"] for r in result]
    assert "https://example.com/reg1" in urls
    assert "https://example.com/reg2" in urls


def test_deduplicate_by_source_name():
    sources = [
        {"source": "HUD Guidelines"},
        {"source": "HUD Guidelines"},
        {"source": "Texas Property Code"},
    ]
    result = deduplicate_sources(sources)
    assert len(result) == 2


def test_no_duplicates_passthrough():
    sources = [
        {"url": "https://a.gov/1"},
        {"url": "https://b.gov/2"},
        {"url": "https://c.gov/3"},
    ]
    result = deduplicate_sources(sources)
    assert len(result) == 3
