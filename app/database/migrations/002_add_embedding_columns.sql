-- Add embedding columns to papers table
-- This migration adds vector columns for storing OpenAI embeddings (1536 dimensions)
-- Run this migration manually: psql -d <database_name> -f 002_add_embedding_columns.sql

-- Add vector column for title + abstract embeddings (text-embedding-3-small = 1536 dimensions)
ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS embedding_title_abstract vector(1536);

-- Add timestamp for when embedding was generated
ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS embedding_generated_at TIMESTAMP WITH TIME ZONE;

-- Create index for vector similarity search (using cosine distance)
CREATE INDEX IF NOT EXISTS papers_embedding_idx 
ON papers 
USING ivfflat (embedding_title_abstract vector_cosine_ops)
WITH (lists = 100);

-- Note: For small datasets (<10K rows), you might want to use HNSW instead:
-- CREATE INDEX IF NOT EXISTS papers_embedding_idx 
-- ON papers 
-- USING hnsw (embedding_title_abstract vector_cosine_ops);

-- Add comments for documentation
COMMENT ON COLUMN papers.embedding_title_abstract IS 'OpenAI text-embedding-3-small vector (1536 dimensions) for title + abstract';
COMMENT ON COLUMN papers.embedding_generated_at IS 'Timestamp when the embedding was last generated';
