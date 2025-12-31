# Database Migrations

This directory contains SQL migration scripts for SciLib.

## Running Migrations

Migrations must be run manually in order. Connect to your PostgreSQL database and execute:

```bash
# Get database connection details from .env
source .env

# Run migrations in order
psql $DATABASE_URL -f 001_enable_pgvector.sql
psql $DATABASE_URL -f 002_add_embedding_columns.sql
```

Or if your DATABASE_URL is in format `postgresql://user:pass@host:port/dbname`:

```bash
psql -d scilib -f 001_enable_pgvector.sql
psql -d scilib -f 002_add_embedding_columns.sql
```

## Migration List

| File | Description | Status |
|------|-------------|--------|
| `001_enable_pgvector.sql` | Enable pgvector extension | ⬜ Not Run |
| `002_add_embedding_columns.sql` | Add embedding columns to papers table | ⬜ Not Run |

## Checking Migration Status

To verify if migrations have been applied:

```sql
-- Check if pgvector is installed
SELECT * FROM pg_extension WHERE extname = 'vector';

-- Check if embedding columns exist
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'papers' 
AND column_name LIKE 'embedding%';
```

## Rollback (if needed)

```sql
-- Remove embedding columns
ALTER TABLE papers DROP COLUMN IF EXISTS embedding_title_abstract;
ALTER TABLE papers DROP COLUMN IF EXISTS embedding_generated_at;

-- Remove extension (careful - removes all vector columns!)
DROP EXTENSION IF EXISTS vector CASCADE;
```

## Notes

- Migrations are idempotent (safe to run multiple times)
- pgvector must be installed on PostgreSQL server before running migrations
- Install pgvector: `brew install pgvector` (macOS) or see https://github.com/pgvector/pgvector
