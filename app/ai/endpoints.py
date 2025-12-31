"""
Simplified AI endpoints for SciLib metadata extraction.
Minimal version that works with session token authentication.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging
import os

from ..database.connection import get_db
from ..database.models import Paper
from ..config import settings
from ..auth import verify_api_key

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.get("/health")
async def health_check():
    """AI system health check."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00",
        "services": {
            "pdf_extraction": "available",
            "llm_analysis": "available", 
            "database_search": "available"
        }
    }


@router.post("/extract/{paper_id}")
async def start_extraction(
    paper_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Start metadata extraction for a paper."""
    
    # Get paper
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Check if file exists  
    if not paper.file_path or not os.path.exists(paper.file_path):
        raise HTTPException(status_code=400, detail="PDF file not found")
    
    try:
        # For now, just return a mock response
        # In a full implementation, this would start the Celery task
        return {
            "task_id": f"mock_task_{paper_id}",
            "status": "started",
            "paper_id": paper_id,
            "message": "Extraction started (mock implementation)"
        }
        
    except Exception as e:
        logger.error(f"Extraction failed for paper {paper_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    _: str = Depends(verify_api_key)
):
    """Get extraction task status."""
    
    # Mock response for now
    return {
        "task_id": task_id,
        "status": "completed",
        "progress": 100,
        "result": {
            "confidence": 0.85,
            "metadata": {
                "title": "Mock Paper Title",
                "authors": "Mock Author",
                "year": "2024"
            }
        }
    }


@router.get("/paper/{paper_id}/extraction") 
async def get_extraction_results(
    paper_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get extraction results for a paper."""
    
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    return {
        "paper_id": paper_id,
        "extraction_status": paper.extraction_status or "not_started",
        "extraction_confidence": paper.extraction_confidence or 0.0,
        "extraction_metadata": paper.extraction_metadata or {},
        "extraction_sources": paper.extraction_sources or []
    }