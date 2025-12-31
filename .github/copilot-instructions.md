# SciLib AI Coding Agent Instructions

## Project Overview

SciLib is an AI-powered scientific literature manager with PDF metadata extraction. Built with FastAPI backend, PostgreSQL database, vanilla JavaScript frontend, and multi-stage AI pipeline using scientific APIs (CrossRef, arXiv, Semantic Scholar, OpenAlex) with optional GPT-4o-mini validation.

## Architecture

### Service Components
- **FastAPI App** (`app/main.py`): REST API with simple `X-API-Key` header auth
- **Celery Workers** (`app/celery_worker.py`): Background AI extraction tasks via Redis queue
- **PostgreSQL**: Paper metadata, collections, tags with many-to-many relationships
- **Frontend**: Vanilla JS modules in `static/` with localStorage-based session management

### AI Extraction Pipeline (`app/ai/agents/metadata_pipeline.py`)
Three-stage pipeline for PDF metadata extraction:
1. **PDF Extraction**: PyMuPDF/pdfplumber + OCR fallback (Tesseract)
2. **DOI-First Strategy**: Extract DOI from PDF → query scientific APIs directly (free, no LLM)
3. **API Search**: CrossRef, arXiv, Semantic Scholar, OpenAlex for metadata
4. **LLM Analysis** (optional): GPT-4o-mini only for validation/merging when APIs fail
5. **Confidence Scoring**: Merge sources, resolve conflicts, compute 0.0-1.0 confidence

**Key Design**: DOI-first approach minimizes LLM usage. `use_llm=False` by default for cost efficiency.

## Configuration & Environment

### Critical `.env` Variables
```bash
DATABASE_URL=postgresql://user:pass@localhost/scilib
API_KEY=your-secret-api-key-here              # Required for API auth
OPENAI_API_KEY=sk-...                         # Required for LLM features
REDIS_URL=redis://localhost:6379              # Required for Celery
CELERY_BROKER_URL=redis://localhost:6379
EXA_API_KEY=...                               # Optional: enhanced web search
CROSSREF_EMAIL=your@email.com                 # Optional: higher rate limits
```

Config loaded via Pydantic (`app/config.py`) with `.env` file. All API keys from environment—no hardcoded secrets.

## Database Schema (`app/database/models.py`)

### Core Models
- **Paper**: Main entity with AI extraction fields
  - Standard: `title`, `authors`, `abstract`, `keywords`, `year`, `journal`, `doi`, `file_path`
  - AI-specific: `extraction_status` (pending/processing/completed/failed), `extraction_confidence` (0.0-1.0), `extraction_sources` (JSON), `extraction_metadata` (JSON), `manual_override` (bool)
- **Collection**: Many-to-many with Papers via `paper_collections` table
- **Tag**: Many-to-many with Papers via `paper_tags` table

### SQLAlchemy Patterns
- Use `SessionLocal` from `app.database.connection` for DB sessions
- Models inherit from `Base` (declarative_base)
- JSON columns for flexible AI metadata storage
- DateTime fields use `func.now()` for server-side timestamps

## Developer Workflows

### Starting the Stack
Use the convenience script (handles all services):
```bash
./start_scilib.sh          # Production mode
./start_scilib.sh --dev    # Development with auto-reload
```

Or manually in 3 terminals:
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery worker
python app/celery_worker.py

# Terminal 3: FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing Workflows
- **Manual testing**: `minimals/` contains standalone examples (no pytest suite yet)
  - `example_crossref.py`: Test CrossRef API integration
  - `example_exa.py`: Test Exa search integration
- **Pipeline testing**: `minimals/pipeline/test_extraction.py` for metadata pipeline

### Debugging AI Extraction
Set `DEBUG=True` in `.env` to enable colored terminal output in `metadata_pipeline.py`:
- Tool execution status with ✓/✗ indicators
- Confidence scores and extracted fields
- DOI-first vs fallback strategy decisions

## Code Conventions

### API Structure
- Routes in `app/api/` (papers, collections, tags) + `app/ai/endpoints.py`
- All protected routes require `Depends(verify_api_key)` dependency
- Frontend uses `X-API-Key` header (managed by `ApiKeyManager` in `static/js/api.js`)
- Return Pydantic models for consistent serialization

### Frontend Patterns (`static/js/`)
- **Modular JS**: `api.js` (API client), `components.js` (UI), `main.js` (app logic)
- **API Client**: `API.request(endpoint, options)` handles auth headers automatically
- **Storage**: `ApiKeyManager` for localStorage key management
- **No Framework**: Pure DOM manipulation, event listeners, template literals

### AI Tools Organization (`app/ai/tools/`)
- Each external API wrapped in tool class: `CrossRefTool`, `ArxivTool`, `SemanticScholarTool`, `OpenAlexTool`
- Standard method signature: `search(title: str, authors: List[str]) -> Dict`
- Return standardized metadata dict or `None` on failure
- Timeout handling (default 10s) to prevent blocking

### Error Handling
- FastAPI: Raise `HTTPException(status_code=..., detail=...)` 
- Celery tasks: Update `self.update_state(state="FAILURE", meta={...})` on errors
- Frontend: `try/catch` in API calls, display error messages via `showErrorMessage()`

## Integration Points

### Celery Task Flow
1. Paper uploaded → `papers.router` creates DB entry with `extraction_status="pending"`
2. Celery task dispatched: `extract_pdf_metadata_task.delay(pdf_path, paper_id, use_llm=False)`
3. Task updates status: `self.update_state(state="PROGRESS", meta={...})`
4. Pipeline runs → results saved to `Paper.extraction_metadata` (JSON)
5. Frontend polls `/api/ai/status/{task_id}` for completion

### Scientific API Rate Limits
- **CrossRef**: 50 req/s with email, otherwise limited
- **arXiv**: 1 req/3s enforced in `ArxivTool` with `time.sleep()`
- **Semantic Scholar**: 100 req/5min (optional API key for 10x increase)
- **OpenAlex**: No rate limits (use as fallback)

### PDF Processing Chain
1. Direct text extraction: PyMuPDF (`fitz`) first
2. OCR fallback: Tesseract if no embedded text (see `MAX_OCR_PAGES=10`)
3. Regex-based extraction: DOI patterns, title/author heuristics
4. API validation: Cross-check extracted DOI against scientific databases

## Common Pitfalls

- **Celery not picking up tasks**: Check Redis is running (`redis-cli ping`)
- **API auth failures**: Ensure `X-API-Key` header matches `.env` file (frontend stores in localStorage)
- **Import errors in Celery**: Worker doesn't auto-reload; restart after code changes
- **Missing PDF files**: Check `UPLOAD_DIR=./uploads` exists and file paths are absolute
- **Low confidence scores**: DOI extraction is key—improve OCR quality or PDF text layer
- **LLM costs**: Default `use_llm=False`—only enable for critical high-accuracy needs

## Key Files Reference

- [`app/ai/agents/metadata_pipeline.py`](app/ai/agents/metadata_pipeline.py): Core AI extraction logic
- [`app/ai/tasks.py`](app/ai/tasks.py): Celery task definitions
- [`app/database/models.py`](app/database/models.py): SQLAlchemy ORM models
- [`app/main.py`](app/main.py): FastAPI app initialization and route registration
- [`app/config.py`](app/config.py): Pydantic settings from `.env`
- [`static/js/api.js`](static/js/api.js): Frontend API client
- [`start_scilib.sh`](start_scilib.sh): All-in-one startup script
- [`docs/AI_INTEGRATION.md`](docs/AI_INTEGRATION.md): Detailed AI pipeline documentation

## Development Tips

- Read [`docs/AI_INTEGRATION.md`](docs/AI_INTEGRATION.md) for complete AI system documentation
- Test API changes with `curl -H "X-API-Key: your-key" http://localhost:8000/api/...`
- Monitor Celery logs for task execution details
- Use `DEBUG=True` for verbose AI pipeline output
- Check `extraction_status` and `extraction_confidence` fields to debug metadata quality
- Frontend console logs API requests with sanitized key preview
