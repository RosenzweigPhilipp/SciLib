-- Add AI summary columns to papers table
-- This migration adds columns for storing AI-generated summaries
-- Run this migration manually: psql -d scilib_db -f 003_add_summary_columns.sql

-- Add summary columns
ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS ai_summary_short TEXT;

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS ai_summary_long TEXT;

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS ai_key_findings JSON;

ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS summary_generated_at TIMESTAMP WITH TIME ZONE;

-- Add comments for documentation
COMMENT ON COLUMN papers.ai_summary_short IS 'AI-generated short summary (~50 words) for quick overview';
COMMENT ON COLUMN papers.ai_summary_long IS 'AI-generated detailed summary (~200 words) with more context';
COMMENT ON COLUMN papers.ai_key_findings IS 'JSON array of key findings and bullet points extracted by AI';
COMMENT ON COLUMN papers.summary_generated_at IS 'Timestamp when the AI summary was last generated';
