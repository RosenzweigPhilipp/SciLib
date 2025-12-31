"""
Test script for pgvector setup and embedding generation.

This script tests:
1. pgvector extension is installed
2. Embedding columns exist in database
3. Embedding generation works
4. Vector similarity search works
"""

import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal, Paper
from app.ai.services.embedding_service import EmbeddingService
from sqlalchemy import text


def test_pgvector_extension():
    """Test if pgvector extension is installed"""
    print("\n" + "="*80)
    print("TEST 1: Check pgvector extension")
    print("="*80)
    
    try:
        with SessionLocal() as db:
            result = db.execute(text("SELECT * FROM pg_extension WHERE extname = 'vector'"))
            row = result.fetchone()
            
            if row:
                print("✓ pgvector extension is installed")
                return True
            else:
                print("✗ pgvector extension NOT installed")
                print("\nTo install, run:")
                print("  psql -d scilib -f app/database/migrations/001_enable_pgvector.sql")
                return False
                
    except Exception as e:
        print(f"✗ Error checking extension: {e}")
        return False


def test_embedding_columns():
    """Test if embedding columns exist"""
    print("\n" + "="*80)
    print("TEST 2: Check embedding columns")
    print("="*80)
    
    try:
        with SessionLocal() as db:
            result = db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'papers' 
                AND column_name LIKE 'embedding%'
                ORDER BY column_name
            """))
            
            columns = result.fetchall()
            
            if len(columns) == 2:
                print("✓ Embedding columns exist:")
                for col in columns:
                    print(f"  - {col[0]}: {col[1]}")
                return True
            else:
                print(f"✗ Expected 2 embedding columns, found {len(columns)}")
                if len(columns) == 0:
                    print("\nTo add columns, run:")
                    print("  psql -d scilib -f app/database/migrations/002_add_embedding_columns.sql")
                return False
                
    except Exception as e:
        print(f"✗ Error checking columns: {e}")
        return False


async def test_embedding_generation():
    """Test embedding generation"""
    print("\n" + "="*80)
    print("TEST 3: Test embedding generation")
    print("="*80)
    
    try:
        # Test with sample text
        test_text = "Attention is all you need: A neural machine translation model based solely on attention mechanisms"
        
        print(f"Generating embedding for: '{test_text[:60]}...'")
        embedding = await EmbeddingService.generate_embedding(test_text)
        
        if embedding:
            print(f"✓ Successfully generated embedding")
            print(f"  - Dimension: {len(embedding)}")
            print(f"  - First 5 values: {embedding[:5]}")
            return embedding
        else:
            print("✗ Failed to generate embedding")
            return None
            
    except Exception as e:
        print(f"✗ Error generating embedding: {e}")
        return None


async def test_embedding_storage():
    """Test storing and retrieving embeddings"""
    print("\n" + "="*80)
    print("TEST 4: Test embedding storage")
    print("="*80)
    
    try:
        with SessionLocal() as db:
            # Find a paper to test with
            paper = db.query(Paper).first()
            
            if not paper:
                print("✗ No papers in database to test with")
                print("\nUpload a paper first to test embedding storage")
                return False
            
            print(f"Testing with paper: '{paper.title[:60]}...'")
            
            # Generate embedding
            embedding = await EmbeddingService.generate_paper_embedding(
                paper.title, 
                paper.abstract
            )
            
            if not embedding:
                print("✗ Failed to generate embedding for paper")
                return False
            
            # Store embedding
            from datetime import datetime
            paper.embedding_title_abstract = embedding
            paper.embedding_generated_at = datetime.now()
            db.commit()
            
            print(f"✓ Successfully stored embedding for paper ID {paper.id}")
            
            # Retrieve and verify
            db.refresh(paper)
            if paper.embedding_title_abstract is not None:
                print(f"✓ Successfully retrieved embedding from database")
                print(f"  - Dimension: {len(paper.embedding_title_abstract)}")
                return True
            else:
                print("✗ Failed to retrieve embedding from database")
                return False
                
    except Exception as e:
        print(f"✗ Error testing storage: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_similarity_search():
    """Test vector similarity search"""
    print("\n" + "="*80)
    print("TEST 5: Test similarity search")
    print("="*80)
    
    try:
        with SessionLocal() as db:
            # Check if any papers have embeddings
            papers_with_embeddings = db.query(Paper).filter(
                Paper.embedding_title_abstract.isnot(None)
            ).count()
            
            if papers_with_embeddings == 0:
                print("✗ No papers with embeddings to search")
                print("\nRun test 4 first to generate embeddings")
                return False
            
            print(f"Found {papers_with_embeddings} paper(s) with embeddings")
            
            # Generate query embedding
            query = "transformer neural networks"
            print(f"\nSearching for: '{query}'")
            
            query_embedding = await EmbeddingService.generate_embedding(query)
            if not query_embedding:
                print("✗ Failed to generate query embedding")
                return False
            
            # Perform similarity search using raw SQL
            # Using cosine distance (1 - cosine_similarity)
            result = db.execute(text("""
                SELECT 
                    id, 
                    title, 
                    1 - (embedding_title_abstract <=> CAST(:query_embedding AS vector)) AS similarity
                FROM papers
                WHERE embedding_title_abstract IS NOT NULL
                ORDER BY embedding_title_abstract <=> CAST(:query_embedding AS vector)
                LIMIT 5
            """), {"query_embedding": str(query_embedding)})
            
            results = result.fetchall()
            
            if results:
                print(f"✓ Found {len(results)} similar papers:")
                for i, (paper_id, title, similarity) in enumerate(results, 1):
                    print(f"\n  {i}. [{similarity:.3f}] {title[:70]}")
                    if len(title) > 70:
                        print(f"     {title[70:]}")
                return True
            else:
                print("✗ No results found")
                return False
                
    except Exception as e:
        print(f"✗ Error testing similarity search: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "pgvector Setup Test Suite" + " "*33 + "║")
    print("╚" + "="*78 + "╝")
    
    results = []
    
    # Test 1: Extension
    results.append(("pgvector extension", test_pgvector_extension()))
    
    # Test 2: Columns
    results.append(("Embedding columns", test_embedding_columns()))
    
    # Test 3: Generation
    embedding = await test_embedding_generation()
    results.append(("Embedding generation", embedding is not None))
    
    # Test 4: Storage (only if previous tests passed)
    if all(r[1] for r in results):
        storage_ok = await test_embedding_storage()
        results.append(("Embedding storage", storage_ok))
        
        # Test 5: Search (only if storage worked)
        if storage_ok:
            search_ok = await test_similarity_search()
            results.append(("Similarity search", search_ok))
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! pgvector setup is complete.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
