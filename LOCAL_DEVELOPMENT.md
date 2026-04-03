# Local Development

## Prerequisites
- Python 3.11
- Supabase project with pgvector extension enabled

## Setup Steps

### 1. Install dependencies
```bat
py -3.9 -m pip install -r requirements.txt
```

### 2. Run database migrations
Run the 7 SQL migration files in `db/migrations/` in order (001 → 007) via the Supabase SQL Editor.

### 3. Configure environment
```bat
copy .env.example .env
```
Fill in your API keys and Supabase credentials in `.env`.

### 4. Seed the database
```bat
py -3.9 scripts\seed_jurisdictions.py
py -3.9 scripts\seed_db.py
py -3.9 scripts\index_regulations.py
```

### 5. (Optional) Grant anon role for local dev
Run this in Supabase SQL Editor to allow local dev without RLS:
```sql
ALTER TABLE jurisdictions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "allow_all" ON jurisdictions FOR ALL USING (true);
-- repeat for other tables as needed
```

### 6. Run the app
```bat
py -3.9 -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1 --server.headless=true
```
Open: http://127.0.0.1:8501
