-- Enable pgvector extension
-- This migration adds the pgvector extension to support vector similarity search
-- Run this migration manually: psql -d <database_name> -f 001_enable_pgvector.sql

-- Create extension if it doesn't exist
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension is installed
SELECT * FROM pg_extension WHERE extname = 'vector';
