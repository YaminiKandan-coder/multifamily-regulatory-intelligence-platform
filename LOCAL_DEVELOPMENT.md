# Local Development

## Prerequisites
- Python 3.11
- Supabase project with pgvector extension enabled

## Setup Steps

### 1. Install dependencies
```bat
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Run database migrations
Run the 7 SQL migration files in `db/migrations/` in order (001 → 007) via the Supabase SQL Editor.
This deployment uses OpenAI embeddings (1536-dim) — if you switch `EMBED_PROVIDER` to `gemini`,
you'll need to bump every `vector(1536)` in migrations 002-006 back to `vector(3072)` first.

### 3. Configure environment
```bat
copy .env.example .env
```
Fill in your API keys and Supabase credentials in `.env`.

### 4. Seed the database
Run these as modules (`-m`), not as bare scripts — running them directly fails with
`ModuleNotFoundError: No module named 'db'` because the project root isn't on `sys.path`
unless invoked this way:
```bat
.venv\Scripts\python.exe -m scripts.seed_jurisdictions
.venv\Scripts\python.exe -m scripts.seed_db
.venv\Scripts\python.exe -m scripts.index_regulations
```

### 5. (Optional) Grant anon role for local dev
Row Level Security is intentionally left disabled on the core tables (jurisdictions, regulations,
regulation_embeddings, etc.) since this app is a server-side Streamlit tool that talks to Supabase
directly with the anon key — it's never exposed to end-user browsers. If you later add a public
client-side integration, enable RLS with explicit policies:
```sql
ALTER TABLE jurisdictions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all" ON jurisdictions FOR ALL USING (true);
-- repeat for other tables as needed
```

### 6. Run the app
```bat
.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1 --server.headless=true
```
Open: http://127.0.0.1:8501
