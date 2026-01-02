# Extended Metadata Extraction - Testing Guide

## Overview

The `extended-meta-data-extraction` branch adds complete BibTeX-compatible metadata extraction to SciLib. This guide explains how to test the new features.

## What Changed

### Database Schema
Added 12 new fields to the `papers` table:
- `publisher` - Publisher name (e.g., "Springer", "IEEE", "ACM")
- `volume` - Volume number
- `issue` - Issue/number
- `pages` - Page range (e.g., "123-145")
- `booktitle` - Conference/book title for proceedings/chapters
- `series` - Book series name
- `edition` - Edition number
- `isbn` - ISBN number
- `url` - Paper URL (DOI-based or direct)
- `month` - Publication month (1-12)
- `note` - Additional notes (e.g., arXiv category)
- `publication_type` - BibTeX entry type (article, inproceedings, etc.)

### API Tool Enhancements
All scientific APIs now extract extended metadata:
- **CrossRef**: Volume, issue, pages, publisher, URL, ISBN, edition, month, conference detection
- **Semantic Scholar**: Booktitle (conference vs article detection), volume, pages, ISBN, month
- **OpenAlex**: Publisher from host_organization, publication_type mapping, month from date
- **arXiv**: Month extraction, arXiv category in note field

### LLM Metadata Enrichment
New `MetadataEnricher` class uses GPT-4o-mini to fill missing BibTeX fields:
- Automatically called during summary generation when LLM knows the paper
- Validates field-specific formats (month 1-12, ISBN structure, URL format)
- Only adds high-confidence fields, leaves unknowns as null

### BibTeX Export
New `/papers/{id}/bibtex` endpoint:
- Returns properly formatted BibTeX entry
- Generates citation keys in `author_year_keyword` format
- Supports all standard entry types (article, inproceedings, book, etc.)
- Escapes LaTeX special characters
- Downloads as `.bib` file

### Frontend Updates
- Paper details modal shows publisher, volume, issue, pages, booktitle
- "Export BibTeX" button downloads complete citation
- Metadata grid automatically adapts to available fields

## Testing Instructions

### 1. Database Migration
First, ensure the database schema is updated:

```bash
# Drop existing database (if needed for clean test)
python -c "from app.database import engine, Base; Base.metadata.drop_all(engine); Base.metadata.create_all(engine)"

# Or use init_db.py
python app/database/init_db.py
```

### 2. Start Services
Use the convenience script:

```bash
./start_scilib.sh --dev
```

Or manually:
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery
python app/celery_worker.py

# Terminal 3: FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test Cases

#### Test Case 1: Journal Article with DOI
**Paper**: "Attention Is All You Need" (Vaswani et al., 2017)  
**Expected**: CrossRef should provide volume, issue, pages, publisher  
**Steps**:
1. Upload a PDF or create paper manually with DOI: `10.5555/3295222.3295349`
2. Trigger AI extraction
3. Check paper details modal for:
   - Publisher: "Curran Associates Inc."
   - Volume/Issue/Pages if available
4. Export BibTeX and verify format

#### Test Case 2: Conference Paper
**Paper**: Any NeurIPS, ICML, or CVPR paper  
**Expected**: Semantic Scholar should detect conference and set booktitle  
**Steps**:
1. Upload conference paper PDF
2. Verify `booktitle` is set to conference name (not expanded as journal)
3. Verify `publication_type` is "inproceedings"
4. BibTeX export should use `@inproceedings{...}` with `booktitle` field

#### Test Case 3: arXiv Preprint
**Paper**: Any paper from arxiv.org  
**Expected**: arXiv tool should extract month and category  
**Steps**:
1. Upload arXiv PDF (e.g., from cs.AI, cs.LG)
2. Check `month` is set (1-12)
3. Check `note` contains arXiv category (e.g., "arXiv:cs.AI")
4. BibTeX export includes `note` field

#### Test Case 4: LLM Enrichment
**Paper**: Well-known paper like "BERT" or "GPT-3"  
**Expected**: LLM enriches missing fields when generating summary  
**Steps**:
1. Upload paper with minimal metadata
2. Trigger summary generation (automatic knowledge check)
3. If LLM knows paper (confidence >= 0.7):
   - Check logs for "Enriching metadata for paper..."
   - Verify enriched fields appear in paper details
4. Fields should be validated (e.g., month is 1-12, not "June")

#### Test Case 5: BibTeX Export
**Paper**: Any complete paper  
**Expected**: Valid BibTeX entry that imports into Zotero/LaTeX  
**Steps**:
1. Click "Export BibTeX" button in paper details
2. Download `.bib` file
3. Verify format:
   ```bibtex
   @article{author2023keyword,
     title = {{Paper Title}},
     author = {Last1, First1 and Last2, First2},
     year = 2023,
     journal = {Journal Name},
     volume = 42,
     number = 3,
     pages = {123--145},
     doi = {10.1234/example},
     publisher = {Publisher Name}
   }
   ```
4. Test import:
   - **Zotero**: File → Import → select .bib file
   - **LaTeX**: Add to bibliography, compile with BibTeX/BibLaTeX

### 4. Edge Cases to Test

#### Missing Fields
- Paper with no DOI → Exa fallback, LLM enrichment
- Paper with incomplete CrossRef metadata → OpenAlex/S2 should fill gaps
- Very old paper (pre-digital) → May lack volume/issue/pages

#### Special Characters
- Title with LaTeX symbols ($, {, }, \) → Should be escaped in BibTeX
- Non-ASCII characters (ü, é, ñ) → Should preserve or escape properly
- Long author lists → BibTeX `and` separator between authors

#### Publication Types
- **Article**: Standard journal paper
- **Inproceedings**: Conference/workshop paper
- **Book**: Complete book
- **Inbook**: Book chapter
- **Phdthesis**: Dissertation

### 5. Validation Checklist

- [ ] New database fields appear in paper details modal
- [ ] API tools extract extended metadata (check logs with `DEBUG=True`)
- [ ] Metadata pipeline merges fields from multiple sources
- [ ] LLM enrichment adds missing fields during summary generation
- [ ] BibTeX export generates valid `.bib` file
- [ ] BibTeX imports successfully into Zotero/LaTeX
- [ ] Frontend displays all available metadata fields
- [ ] Export button downloads file with correct MIME type
- [ ] Citation keys are generated correctly (author_year_keyword)
- [ ] Month is stored as integer (1-12), not string

## Debugging Tips

### Enable Debug Output
```bash
# In .env
DEBUG=True
```

Look for colored terminal output showing:
- ✓ Field extraction from each API
- Enrichment attempts and results
- Confidence scores per field

### Check Database Values
```sql
SELECT id, title, publisher, volume, issue, pages, booktitle, publication_type 
FROM papers 
WHERE id = <paper_id>;
```

### Test BibTeX Endpoint Manually
```bash
curl -H "X-API-Key: your-key" http://localhost:8000/api/papers/1/bibtex
```

### Verify LLM Enrichment
Check Celery logs for:
```
Enriching metadata for paper <id>
Enriched 5 fields: ['publisher', 'volume', 'issue', 'pages', 'month']
```

## Common Issues

### Fields Not Extracted
- **Cause**: API source doesn't have metadata
- **Solution**: LLM enrichment should fill gaps (requires LLM knowledge of paper)

### Wrong Publication Type
- **Cause**: API classification error
- **Solution**: Manual override or adjust detection heuristics in tools

### BibTeX Import Fails
- **Cause**: Special character escaping or field format
- **Solution**: Check LaTeX escape sequences, validate BibTeX syntax

### Enrichment Not Running
- **Cause**: LLM confidence < 0.7 or OPENAI_API_KEY not set
- **Solution**: Check knowledge check result, verify API key in `.env`

## Next Steps

After successful testing:
1. Test with diverse paper types (journal, conference, preprint, book chapter)
2. Verify BibTeX exports import correctly into common tools
3. Check logs for any errors or warnings
4. Consider adding user-editable metadata fields in frontend
5. Potentially add batch export (multiple papers to single .bib file)

## Rollback

If issues arise, switch back to main branch:
```bash
git checkout main
```

Database schema is backward-compatible (all new fields nullable).
