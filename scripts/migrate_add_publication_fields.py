#!/usr/bin/env python3
"""
Migration script: Add publication-type specific fields

Adds the following new columns to the papers table:
- chapter (String(100)): Chapter number/title for inbook/incollection
- institution (String(255)): Institution for techreport, thesis
- report_number (String(100)): Report/tech report number

Usage:
    python scripts/migrate_add_publication_fields.py
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
    print("SciLib Migration: Add Publication Fields")
    print("=" * 45)
    print(f"Database: {settings.database_url}")
    print()
    
    new_columns = [
        ("chapter", "VARCHAR(100)"),
        ("institution", "VARCHAR(255)"),
        ("report_number", "VARCHAR(100)"),
    ]
    
    with engine.connect() as connection:
        with connection.begin():
            print("Adding new columns to 'papers' table:")
            
            added_count = 0
            for column, col_type in new_columns:
                if add_column(connection, "papers", column, col_type):
                    added_count += 1
            
            print()
            if added_count > 0:
                print(f"✓ Migration completed! Added {added_count} new column(s)")
            else:
                print("✓ Migration completed! No new columns needed")


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        sys.exit(1)
