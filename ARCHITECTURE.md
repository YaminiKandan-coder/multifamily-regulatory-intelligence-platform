# Architecture

## Stack
- Python 3.11 + Streamlit (multi-page via `pages/`)
- Supabase (Postgres + pgvector)
- Primary LLM: Anthropic Claude `claude-sonnet-5`
- Fallback LLM: OpenAI GPT-4o
- Second fallback: Google Gemini
- Final fallback: rule-based engine (`core/compliance/rules.py`) — no API key required
- Embeddings: Google Gemini (default) or OpenAI `text-embedding-3-small`
- GitHub Actions for scheduled scraping

## LLM fallback order
1. `has_anthropic_key` → Claude Sonnet 4
2. `has_openai_key` → GPT-4o
3. `has_google_key` → Gemini
4. Rule-based engine (no API key)

## RAG pipeline (upgraded)
1. **Chunking:** legal-aware splitting (section/article boundaries) via `core/rag/chunking.py`, fallback to sliding window
2. **Retrieval:** hybrid search (vector + Postgres full-text) via `core/rag/hybrid.py`, fused with Reciprocal Rank Fusion
3. **Jurisdiction scoping:** explicit hierarchy (city→state→federal) via `core/rag/jurisdiction.py`
4. **Reranking:** deterministic scoring (jurisdiction match 30%, topic relevance 25%, citation density 20%, source quality 15%, recency 10%) via `core/rag/reranker.py`
5. **Grounding:** confidence assessment, source attribution, uncertainty handling via `core/rag/grounding.py`
6. **Answer generation:** grounded LLM prompt with jurisdiction labels, conflict notices, uncertainty instructions

## RAG config env vars
- `RAG_HYBRID_ENABLED` (bool, default true)
- `RAG_HYBRID_VECTOR_WEIGHT` (float, default 0.6)
- `RAG_RETRIEVAL_TOP_N` (int, default 15)
- `RAG_RERANK_TOP_K` (int, default 5)
- `RAG_LLM_RERANK_ENABLED` (bool, default false)
- `RAG_USE_LEGAL_CHUNKING` (bool, default true)

## Key architecture rules
- `pages/` imports from `core/` and `db/` only — no business logic in pages
- `core/` never imports streamlit
- All DB access via `db/client.py` only
- All LLM calls via `core/llm/client.py` only
- Zero hardcoded city/state/jurisdiction names in logic files
- All jurisdiction resolution via DB lookup by `jurisdiction_id` (int)
- Legal disclaimer appended to every compliance result
- Rule-based fallback always works without any API key
