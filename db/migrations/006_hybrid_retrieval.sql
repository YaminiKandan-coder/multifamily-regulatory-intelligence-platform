-- Add tsvector column + GIN index for full-text search
ALTER TABLE regulation_embeddings
  ADD COLUMN IF NOT EXISTS chunk_tsv tsvector;

CREATE INDEX IF NOT EXISTS regulation_embeddings_tsv_idx
  ON regulation_embeddings USING GIN (chunk_tsv);

-- Auto-populate tsvector on insert/update
CREATE OR REPLACE FUNCTION regulation_embeddings_tsv_trigger()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.chunk_tsv := to_tsvector('english', NEW.chunk_text);
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS regulation_embeddings_tsv ON regulation_embeddings;
CREATE TRIGGER regulation_embeddings_tsv
  BEFORE INSERT OR UPDATE OF chunk_text ON regulation_embeddings
  FOR EACH ROW EXECUTE FUNCTION regulation_embeddings_tsv_trigger();

-- Backfill existing rows
UPDATE regulation_embeddings
  SET chunk_tsv = to_tsvector('english', chunk_text)
  WHERE chunk_tsv IS NULL;

-- Lexical / full-text search function (30s timeout)
CREATE OR REPLACE FUNCTION match_regulations_lexical(
  query_text          text,
  match_count         int,
  filter_jurisdiction int DEFAULT NULL
) RETURNS TABLE(id int, chunk_text text, rank float, metadata jsonb)
LANGUAGE plpgsql AS $$
BEGIN
  SET LOCAL statement_timeout = '30s';
  RETURN QUERY
    SELECT e.id,
           e.chunk_text,
           ts_rank(e.chunk_tsv, plainto_tsquery('english', query_text))::float AS rank,
           row_to_json(r)::jsonb AS metadata
    FROM regulation_embeddings e
    JOIN regulations r ON r.id = e.regulation_id
    WHERE r.is_current = true
      AND e.chunk_tsv @@ plainto_tsquery('english', query_text)
      AND (
        filter_jurisdiction IS NULL
        OR r.jurisdiction_id = filter_jurisdiction
        OR r.jurisdiction_id IN (SELECT j.id FROM jurisdictions j WHERE j.type = 'federal')
      )
    ORDER BY rank DESC
    LIMIT match_count;
END;
$$;

-- Vector search with jurisdiction array param (match_regulations_v3, 60s timeout)
CREATE OR REPLACE FUNCTION match_regulations_v3(
  query_embedding      vector(3072),
  match_count          int,
  jurisdiction_ids     int[]   DEFAULT NULL,
  category_filter      text    DEFAULT NULL
) RETURNS TABLE(id int, chunk_text text, similarity float, metadata jsonb)
LANGUAGE plpgsql AS $$
BEGIN
  SET LOCAL statement_timeout = '60s';
  RETURN QUERY
    SELECT e.id,
           e.chunk_text,
           1 - (e.embedding <=> query_embedding) AS similarity,
           row_to_json(r)::jsonb AS metadata
    FROM regulation_embeddings e
    JOIN regulations r ON r.id = e.regulation_id
    WHERE r.is_current = true
      AND (category_filter IS NULL OR r.category = category_filter)
      AND (
        jurisdiction_ids IS NULL
        OR r.jurisdiction_id = ANY(jurisdiction_ids)
      )
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
