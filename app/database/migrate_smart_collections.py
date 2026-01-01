"""
Database migration for smart collections feature.
Adds is_smart column to collections table and creates settings table.
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app.database.connection import engine, SessionLocal
from app.database.models import Settings

def migrate():
    """Run migration to add smart collections support."""
    with engine.connect() as conn:
        # Add is_smart column to collections table
        try:
            conn.execute(text("""
                ALTER TABLE collections 
                ADD COLUMN IF NOT EXISTS is_smart BOOLEAN DEFAULT FALSE
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_collections_is_smart ON collections(is_smart)
            """))
            conn.commit()
            print("✓ Added is_smart column to collections table")
        except Exception as e:
            print(f"✗ Error adding is_smart column: {e}")
        
        # Create settings table
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS settings (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(100) NOT NULL UNIQUE,
                    value JSONB NOT NULL,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)
            """))
            conn.commit()
            print("✓ Created settings table")
        except Exception as e:
            print(f"✗ Error creating settings table: {e}")
    
    # Initialize smart collections setting
    db = SessionLocal()
    try:
        Settings.set(db, "smart_collections_enabled", False)
        print("✓ Initialized smart_collections_enabled setting")
    except Exception as e:
        print(f"✗ Error initializing setting: {e}")
    finally:
        db.close()
    
    print("\n✓ Migration completed successfully!")

if __name__ == "__main__":
    migrate()
