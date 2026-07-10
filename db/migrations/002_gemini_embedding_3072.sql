-- NOTE: originally upgraded embedding dimension from 1536 (OpenAI) to 3072 (Gemini).
-- This deployment is configured for OpenAI embeddings (EMBED_PROVIDER=openai), so this
-- migration is a no-op that keeps the column at 1536 to match text-embedding-3-small.
-- WARNING: Existing embeddings must be re-indexed after any future dimension change.

ALTER TABLE regulation_embeddings
  ALTER COLUMN embedding TYPE vector(1536);

-- Re-create the match_regulations function for the dimension in use
CREATE OR REPLACE FUNCTION match_regulations(
  query_embedding   vector(1536),
  match_count       int,
  filter_jurisdiction int DEFAULT NULL
) RETURNS TABLE(id int, chunk_text text, similarity float, metadata jsonb)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
    SELECT e.id,
           e.chunk_text,
           1 - (e.embedding <=> query_embedding) AS similarity,
           row_to_json(r)::jsonb AS metadata
    FROM regulation_embeddings e
    JOIN regulations r ON r.id = e.regulation_id
    WHERE r.is_current = true
      AND (
        filter_jurisdiction IS NULL
        OR r.jurisdiction_id = filter_jurisdiction
      )
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
