#!/usr/bin/env python3
"""
Migration script: Add similar papers fields

Adds the following new columns to the papers table:
- similar_papers (JSONB): Cached list of similar paper IDs and scores
- similar_papers_updated_at (TIMESTAMP): When similarity search was last run

Usage:
    python scripts/migrate_add_similar_papers.py
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.database.connection import engine
from app.config import settings


def check_column_exists(connection, table, column):
    """Check if a column exists in the table."""
    result = connection.execute(text(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table}' AND column_name = '{column}'
    """))
    return result.fetchone() is not None


def add_column(connection, table, column, column_type):
    """Add a column to a table if it doesn't exist."""
    if check_column_exists(connection, table, column):
        print(f"  ⏭ Column '{column}' already exists, skipping")
        return False
    
    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"))
    print(f"  ✓ Added column '{column}'")
    return True


def migrate():
    """Run the migration."""
    print("SciLib Migration: Add Similar Papers Fields")
    print("=" * 50)
    print(f"Database: {settings.database_url}")
    print()
    
    new_columns = [
        ("similar_papers", "JSONB"),
        ("similar_papers_updated_at", "TIMESTAMP WITH TIME ZONE"),
    ]
    
    with engine.connect() as connection:
        with connection.begin():
            print("Adding columns to 'papers' table:")
            
            changes_made = 0
            for column, column_type in new_columns:
                if add_column(connection, "papers", column, column_type):
                    changes_made += 1
            
            print()
            if changes_made > 0:
                print(f"✅ Migration complete! Added {changes_made} column(s).")
            else:
                print("✅ No changes needed - all columns already exist.")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
