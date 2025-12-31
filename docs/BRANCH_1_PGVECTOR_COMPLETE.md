# Branch 1: pgvector-setup - Implementation Complete ✅

## What Was Implemented

All core functionality for vector embeddings has been implemented:

### ✅ 1. Dependencies Added
- `pgvector>=0.2.4` - PostgreSQL vector extension Python client
- `numpy>=1.24.0` - For vector operations (cosine similarity)

### ✅ 2. Database Schema Updates
**Files Created:**
- [app/database/migrations/001_enable_pgvector.sql](../app/database/migrations/001_enable_pgvector.sql)
- [app/database/migrations/002_add_embedding_columns.sql](../app/database/migrations/002_add_embedding_columns.sql)
- [app/database/migrations/README.md](../app/database/migrations/README.md)

**Model Updates:**
- Added `embedding_title_abstract` column (Vector(1536))
- Added `embedding_generated_at` timestamp
- Imported `pgvector.sqlalchemy.Vector` type

### ✅ 3. Embedding Service
**File:** [app/ai/services/embedding_service.py](../app/ai/services/embedding_service.py)

**Features:**
- `generate_embedding(text)` - Generate embedding for any text
- `generate_paper_embedding(title, abstract)` - Generate embedding for papers
- `cosine_similarity(vec1, vec2)` - Calculate similarity (for testing)
- Uses OpenAI `text-embedding-3-small` model (1536 dimensions)
- Automatic text truncation if too long
- Comprehensive error handling and logging

### ✅ 4. Celery Background Task
**File:** [app/ai/tasks.py](../app/ai/tasks.py)

**New Task:** `generate_paper_embedding_task(paper_id, force_regenerate)`
- Generates embedding for a paper
- Skips if embedding already exists (unless forced)
- Updates database with embedding and timestamp
- Progress tracking via Celery state updates
- Comprehensive error handling

### ✅ 5. Test Suite
**File:** [minimals/test_pgvector.py](../minimals/test_pgvector.py)

**Tests:**
1. Check pgvector extension installed
2. Check embedding columns exist
3. Test embedding generation
4. Test embedding storage/retrieval
5. Test vector similarity search

---

## ⚠️ Manual Installation Required

**Issue:** pgvector is installed via Homebrew but only for PostgreSQL 17/18. You're using PostgreSQL 14.

### Option 1: Link Extension Files (Quick)

Run these commands in your terminal:

```bash
# Link pgvector files to PostgreSQL 14
sudo ln -sf /opt/homebrew/Cellar/pgvector/0.8.1/share/postgresql@17/extension/* /opt/homebrew/share/postgresql@14/extension/
sudo ln -sf /opt/homebrew/Cellar/pgvector/0.8.1/lib/postgresql@17/* /opt/homebrew/lib/postgresql@14/
```

### Option 2: Build from Source (Recommended)

```bash
cd /tmp
git clone --branch v0.8.1 https://github.com/pgvector/pgvector.git
cd pgvector
make PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config
sudo make install PG_CONFIG=/opt/homebrew/opt/postgresql@14/bin/pg_config
```

### Then Run Migrations

After installing pgvector for PostgreSQL 14:

```bash
# Enable pgvector extension
psql postgresql://scilib_user:scilib_password@localhost/scilib_db -f app/database/migrations/001_enable_pgvector.sql

# Add embedding columns
psql postgresql://scilib_user:scilib_password@localhost/scilib_db -f app/database/migrations/002_add_embedding_columns.sql
```

### Run Test Suite

```bash
python minimals/test_pgvector.py
```

This will verify:
- pgvector extension is enabled
- Embedding columns exist
- Embedding generation works
- Vector similarity search works

---

## Usage Examples

### Generate Embedding for a Paper

```python
from app.ai.tasks import generate_paper_embedding_task

# Background task (recommended)
task = generate_paper_embedding_task.delay(paper_id=123)

# Check status
result = task.get()
print(result)
```

### Trigger After Paper Upload

In [app/api/papers.py](../app/api/papers.py), after metadata extraction:

```python
# In the upload endpoint, after creating the paper
from app.ai.tasks import generate_paper_embedding_task

# Trigger embedding generation in background
generate_paper_embedding_task.delay(paper.id)
```

### Similarity Search (SQL)

```python
from sqlalchemy import text

# Find papers similar to a query
query_embedding = await EmbeddingService.generate_embedding("transformers in NLP")

results = db.execute(text("""
    SELECT 
        id, 
        title, 
        1 - (embedding_title_abstract <=> :query_vector) AS similarity
    FROM papers
    WHERE embedding_title_abstract IS NOT NULL
    ORDER BY embedding_title_abstract <=> :query_vector
    LIMIT 10
"""), {"query_vector": str(query_embedding)})
```

---

## Next Steps

Once pgvector is installed and migrations are run:

1. **Commit this branch:**
   ```bash
   git add .
   git commit -m "feat: Add pgvector foundation for semantic search
   
   - Add pgvector and numpy dependencies
   - Create database migrations for vector columns
   - Implement EmbeddingService with OpenAI embeddings
   - Add Celery task for background embedding generation
   - Add comprehensive test suite
   
   Refs: Implementation Roadmap Branch 1"
   ```

2. **Test the implementation:**
   ```bash
   python minimals/test_pgvector.py
   ```

3. **Merge to main** (after testing):
   ```bash
   git checkout main
   git merge feature/pgvector-setup
   git push origin main
   ```

4. **Move to Branch 2:** `feature/paper-summarization`

---

## Files Changed/Created

### Created:
- `app/database/migrations/` (directory)
  - `001_enable_pgvector.sql`
  - `002_add_embedding_columns.sql`
  - `README.md`
- `app/ai/services/` (directory)
  - `__init__.py`
  - `embedding_service.py`
- `minimals/test_pgvector.py`

### Modified:
- `requirements.txt` - Added pgvector, numpy
- `app/database/models.py` - Added embedding columns and Vector import
- `app/ai/tasks.py` - Added generate_paper_embedding_task

---

## Cost Estimation

- **Embedding generation:** ~$0.00002 per paper (OpenAI text-embedding-3-small)
- **100 papers:** ~$0.002 (negligible)
- **1000 papers:** ~$0.02
- **10,000 papers:** ~$0.20

Embeddings can be cached indefinitely and only regenerated when paper metadata changes.

---

## Troubleshooting

### "pgvector extension not found"
- Follow manual installation steps above
- Verify: `psql -d scilib_db -c "SELECT * FROM pg_extension WHERE extname = 'vector'"`

### "Embedding columns don't exist"
- Run migration: `psql -d scilib_db -f app/database/migrations/002_add_embedding_columns.sql`
- Verify: `psql -d scilib_db -c "\d papers"`

### "OpenAI API error"
- Check `OPENAI_API_KEY` in `.env`
- Verify API key has access to embeddings endpoint

### Import errors
- Ensure packages installed: `pip install pgvector numpy`
- Restart Celery worker after code changes

---

## Architecture Notes

- **Embedding Model:** text-embedding-3-small (1536 dimensions, cost-effective)
- **Distance Metric:** Cosine distance (via `<=>` operator in PostgreSQL)
- **Index Type:** IVFFlat for now (suitable for <100K papers), can upgrade to HNSW later
- **Async Design:** Service uses async/await for non-blocking operations
- **Background Processing:** Celery task prevents blocking API requests

---

**Status:** ✅ Code Complete, ⚠️ Manual Installation Required
