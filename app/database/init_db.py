#!/usr/bin/env python3
"""
Database initialization script

This script creates all database tables based on the SQLAlchemy models.
Run this script to set up the database schema.

Usage:
    python -m app.database.init_db
"""

import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.database.connection import engine, Base
from app.database.models import Paper, Collection, Tag
from app.config import settings


def create_tables():
    """
    Create all database tables
    """
    print(f"Creating tables for database: {settings.database_url}")
    
    try:
        Base.metadata.create_all(bind=engine)
        print("✓ All tables created successfully!")
        
        # Print created tables
        print("\nCreated tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
            
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        sys.exit(1)


def main():
    """
    Main function to initialize the database
    """
    print("SciLib Database Initialization")
    print("==============================")
    
    create_tables()
    
    print("\n✓ Database initialization completed!")


if __name__ == "__main__":
    main()