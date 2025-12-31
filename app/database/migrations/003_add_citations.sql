-- Citation Analysis Tables Migration
-- Adds tables for tracking citations between papers and external citation data

-- Create citations table (tracks relationships between papers in library)
CREATE TABLE IF NOT EXISTS citations (
    id SERIAL PRIMARY KEY,
    citing_paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    cited_paper_id INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    context TEXT,  -- Optional: citation context from text
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique citations (paper A cites paper B once)
    UNIQUE(citing_paper_id, cited_paper_id),
    
    -- Prevent self-citations
    CHECK (citing_paper_id != cited_paper_id)
);

-- Indexes for citation queries
CREATE INDEX IF NOT EXISTS idx_citations_citing ON citations(citing_paper_id);
CREATE INDEX IF NOT EXISTS idx_citations_cited ON citations(cited_paper_id);
CREATE INDEX IF NOT EXISTS idx_citations_both ON citations(citing_paper_id, cited_paper_id);

-- Add citation metadata to papers table
ALTER TABLE papers 
ADD COLUMN IF NOT EXISTS citation_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS reference_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS external_citation_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS h_index INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS influence_score FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS citations_updated_at TIMESTAMP WITH TIME ZONE;

-- Create indexes on new citation fields
CREATE INDEX IF NOT EXISTS idx_papers_citation_count ON papers(citation_count);
CREATE INDEX IF NOT EXISTS idx_papers_influence_score ON papers(influence_score);
CREATE INDEX IF NOT EXISTS idx_papers_h_index ON papers(h_index);

-- Function to update citation counts automatically
CREATE OR REPLACE FUNCTION update_citation_counts()
RETURNS TRIGGER AS $$
BEGIN
    -- Update cited paper's citation count
    UPDATE papers 
    SET citation_count = (
        SELECT COUNT(*) FROM citations WHERE cited_paper_id = NEW.cited_paper_id
    )
    WHERE id = NEW.cited_paper_id;
    
    -- Update citing paper's reference count
    UPDATE papers 
    SET reference_count = (
        SELECT COUNT(*) FROM citations WHERE citing_paper_id = NEW.citing_paper_id
    )
    WHERE id = NEW.citing_paper_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update counts on citation insert
CREATE TRIGGER update_citation_counts_trigger
AFTER INSERT ON citations
FOR EACH ROW
EXECUTE FUNCTION update_citation_counts();

-- Function to update counts on citation delete
CREATE OR REPLACE FUNCTION update_citation_counts_on_delete()
RETURNS TRIGGER AS $$
BEGIN
    -- Update cited paper's citation count
    UPDATE papers 
    SET citation_count = (
        SELECT COUNT(*) FROM citations WHERE cited_paper_id = OLD.cited_paper_id
    )
    WHERE id = OLD.cited_paper_id;
    
    -- Update citing paper's reference count
    UPDATE papers 
    SET reference_count = (
        SELECT COUNT(*) FROM citations WHERE citing_paper_id = OLD.citing_paper_id
    )
    WHERE id = OLD.citing_paper_id;
    
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update counts on citation delete
CREATE TRIGGER update_citation_counts_on_delete_trigger
AFTER DELETE ON citations
FOR EACH ROW
EXECUTE FUNCTION update_citation_counts_on_delete();

-- Comments
COMMENT ON TABLE citations IS 'Tracks citation relationships between papers in the library';
COMMENT ON COLUMN papers.citation_count IS 'Number of times this paper is cited by other papers in library';
COMMENT ON COLUMN papers.reference_count IS 'Number of papers this paper cites (references) in library';
COMMENT ON COLUMN papers.external_citation_count IS 'Total citations from external sources (Semantic Scholar, etc.)';
COMMENT ON COLUMN papers.h_index IS 'H-index based on library citations';
COMMENT ON COLUMN papers.influence_score IS 'Calculated influence score (0.0-1.0) based on citation network';
