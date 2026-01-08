"""
Test script for RAG Q&A Search functionality

Tests the new /api/search/qa endpoint with RAG-based question answering.
"""
import os
import sys
import requests
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY", settings.api_key)

def print_section(title):
    """Print a section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}\n")

def test_qa_search():
    """Test Q&A search endpoint"""
    print_section("Testing Q&A Search Endpoint")
    
    # Test questions
    questions = [
        "What are transformers and how do they work?",
        "How do attention mechanisms improve neural networks?",
        "What is the state of the art in machine translation?",
    ]
    
    headers = {"X-API-Key": API_KEY}
    
    for question in questions:
        print(f"Question: {question}")
        print("-" * 60)
        
        # Make request
        response = requests.post(
            f"{BASE_URL}/api/search/qa",
            headers=headers,
            json={
                "question": question,
                "max_papers": 5
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print(f"✓ Success!")
            print(f"  Papers used: {result['context_papers_count']}")
            print(f"  Has sources: {result['has_sources']}")
            print(f"\n  Answer:")
            print(f"  {result['answer'][:300]}...")
            
            if result['sources']:
                print(f"\n  Source papers:")
                for i, source in enumerate(result['sources'][:3], 1):
                    print(f"    {i}. {source['title']}")
                    print(f"       Relevance: {source['relevance_score']:.2f}")
        else:
            print(f"✗ Failed: {response.status_code}")
            print(f"  {response.text}")
        
        print()

def test_qa_with_filters():
    """Test Q&A search with filters"""
    print_section("Testing Q&A Search with Filters")
    
    question = "What recent advances have been made in deep learning?"
    
    headers = {"X-API-Key": API_KEY}
    
    # Test with year filter
    response = requests.post(
        f"{BASE_URL}/api/search/qa",
        headers=headers,
        json={
            "question": question,
            "max_papers": 5,
            "year_from": 2020
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Question with year filter (2020+)")
        print(f"  Papers found: {result['context_papers_count']}")
        print(f"  Answer preview: {result['answer'][:200]}...")
    else:
        print(f"✗ Failed: {response.status_code}")

def test_qa_no_papers():
    """Test Q&A when no relevant papers exist"""
    print_section("Testing Q&A with No Relevant Papers")
    
    question = "What is the best recipe for chocolate chip cookies?"
    
    headers = {"X-API-Key": API_KEY}
    
    response = requests.post(
        f"{BASE_URL}/api/search/qa",
        headers=headers,
        json={
            "question": question,
            "max_papers": 5
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✓ Request successful")
        print(f"  Has sources: {result['has_sources']}")
        print(f"  Answer: {result['answer']}")
    else:
        print(f"✗ Failed: {response.status_code}")

def check_server():
    """Check if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/")
        return response.status_code == 200
    except:
        return False

if __name__ == "__main__":
    print_section("RAG Q&A Search Test Suite")
    
    # Check if server is running
    if not check_server():
        print("❌ Error: Server is not running at http://localhost:8000")
        print("   Please start the server with: uvicorn app.main:app --reload")
        sys.exit(1)
    
    print("✓ Server is running")
    
    # Run tests
    try:
        test_qa_search()
        test_qa_with_filters()
        test_qa_no_papers()
        
        print_section("All Tests Complete")
        print("✓ RAG Q&A search is working correctly!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
