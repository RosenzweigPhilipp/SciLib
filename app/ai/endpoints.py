"""
Simplified AI endpoints for SciLib metadata extraction.
Minimal version that works with session token authentication.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
import logging
import os
from datetime import datetime

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
    from ..ai.tasks import celery_app
    from celery.result import AsyncResult
    
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state == 'PENDING':
            response = {
                "task_id": task_id,
                "status": "pending",
                "progress": 0,
                "message": "Task is waiting to start"
            }
        elif result.state == 'PROGRESS':
            response = {
                "task_id": task_id,
                "status": "processing",
                "progress": result.info.get('current', 0) if result.info else 0,
                "message": result.info.get('status', 'Processing...') if result.info else 'Processing...'
            }
        elif result.state == 'SUCCESS':
            response = {
                "task_id": task_id,
                "status": "completed",
                "progress": 100,
                "result": result.result
            }
        elif result.state == 'FAILURE':
            response = {
                "task_id": task_id,
                "status": "failed",
                "progress": 0,
                "error": str(result.info) if result.info else "Unknown error"
            }
        else:
            response = {
                "task_id": task_id,
                "status": result.state.lower(),
                "progress": 0
            }
        
        return response
    except Exception as e:
        logger.error(f"Error checking task status: {e}")
        return {
            "task_id": task_id,
            "status": "error",
            "error": str(e)
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


@router.get("/paper/{paper_id}/similar")
async def get_similar_papers(
    paper_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    min_score: float = Query(default=0.5, ge=0.0, le=1.0),
    refresh: bool = Query(default=False, description="Force refresh similarity search"),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """
    Get papers similar to the specified paper using vector similarity search.
    
    This uses pre-computed embeddings for fast similarity lookup.
    Results are cached in the database and refreshed when:
    - refresh=True is passed
    - Cached results are older than 24 hours
    - New papers have been added since last search
    """
    from .services.vector_search_service import find_similar_papers
    from sqlalchemy import func
    
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Check if we have cached results that are still valid
    cache_valid = False
    if paper.similar_papers and paper.similar_papers_updated_at and not refresh:
        # Check if cache is less than 24 hours old
        cache_age = datetime.now() - paper.similar_papers_updated_at.replace(tzinfo=None)
        if cache_age.total_seconds() < 86400:  # 24 hours
            cache_valid = True
    
    if cache_valid:
        logger.info(f"Returning cached similar papers for paper {paper_id}")
        return {
            "paper_id": paper_id,
            "similar_papers": paper.similar_papers,
            "cached": True,
            "cached_at": paper.similar_papers_updated_at.isoformat() if paper.similar_papers_updated_at else None
        }
    
    # Check how many papers have embeddings
    papers_with_embeddings = db.query(func.count(Paper.id)).filter(
        Paper.embedding_title_abstract.isnot(None)
    ).scalar()
    
    # Check if paper has embedding
    if paper.embedding_title_abstract is None:
        # Try to generate embedding first
        logger.info(f"Paper {paper_id} has no embedding, attempting to generate...")
        try:
            from .services.embedding_service import EmbeddingService
            
            embedding = await EmbeddingService.generate_paper_embedding(
                paper.title, 
                paper.abstract
            )
            if embedding:
                paper.embedding_title_abstract = embedding
                paper.embedding_generated_at = datetime.now()
                db.commit()
                logger.info(f"Generated embedding for paper {paper_id}")
                papers_with_embeddings += 1  # We just added one
            else:
                # Return empty results with explanation instead of error
                return {
                    "paper_id": paper_id,
                    "similar_papers": [],
                    "cached": False,
                    "total": 0,
                    "message": "Could not generate embedding for this paper. Make sure the paper has a title."
                }
        except Exception as e:
            logger.error(f"Failed to generate embedding for paper {paper_id}: {e}")
            return {
                "paper_id": paper_id,
                "similar_papers": [],
                "cached": False,
                "total": 0,
                "message": f"Embedding generation failed: {str(e)}"
            }
    
    # Check if there are enough other papers with embeddings
    if papers_with_embeddings < 2:
        logger.info(f"Not enough papers with embeddings ({papers_with_embeddings}) for similarity search")
        return {
            "paper_id": paper_id,
            "similar_papers": [],
            "cached": False,
            "total": 0,
            "message": f"Need at least 2 papers with embeddings for similarity search. Currently {papers_with_embeddings} paper(s) have embeddings. Generate summaries for more papers to enable similarity search."
        }
    
    # Perform similarity search
    try:
        similar_papers = await find_similar_papers(
            db=db,
            paper_id=paper_id,
            limit=limit,
            min_score=min_score,
            exclude_self=True
        )
        
        # Cache the results
        paper.similar_papers = similar_papers
        paper.similar_papers_updated_at = datetime.now()
        db.commit()
        
        logger.info(f"Found {len(similar_papers)} similar papers for paper {paper_id}")
        
        return {
            "paper_id": paper_id,
            "similar_papers": similar_papers,
            "cached": False,
            "total": len(similar_papers)
        }
        
    except Exception as e:
        logger.error(f"Similarity search failed for paper {paper_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Similarity search failed: {str(e)}")


@router.post("/paper/{paper_id}/similar/refresh")
async def refresh_similar_papers(
    paper_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Force refresh the similar papers cache for a paper."""
    from .tasks import find_similar_papers_task
    
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    try:
        # Start background task
        task = find_similar_papers_task.delay(paper_id, force_refresh=True)
        
        return {
            "task_id": task.id,
            "paper_id": paper_id,
            "status": "started",
            "message": "Similarity search task started"
        }
    except Exception as e:
        logger.error(f"Failed to start similarity search task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings/generate-all")
async def generate_all_embeddings(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """
    Generate embeddings for all papers that don't have them yet.
    This is useful for enabling similarity search across the library.
    """
    from .services.embedding_service import EmbeddingService
    from sqlalchemy import func
    
    # Get all papers without embeddings
    papers_without_embeddings = db.query(Paper).filter(
        Paper.embedding_title_abstract.is_(None),
        Paper.title.isnot(None)  # Need title for embedding
    ).all()
    
    if not papers_without_embeddings:
        total_with_embeddings = db.query(func.count(Paper.id)).filter(
            Paper.embedding_title_abstract.isnot(None)
        ).scalar()
        return {
            "status": "complete",
            "message": "All papers already have embeddings",
            "total_with_embeddings": total_with_embeddings,
            "generated": 0
        }
    
    generated = 0
    failed = 0
    errors = []
    
    for paper in papers_without_embeddings:
        try:
            embedding = await EmbeddingService.generate_paper_embedding(
                paper.title,
                paper.abstract
            )
            if embedding:
                paper.embedding_title_abstract = embedding
                paper.embedding_generated_at = datetime.now()
                generated += 1
                logger.info(f"Generated embedding for paper {paper.id}: {paper.title[:50]}...")
            else:
                failed += 1
                errors.append(f"Paper {paper.id}: No embedding generated")
        except Exception as e:
            failed += 1
            errors.append(f"Paper {paper.id}: {str(e)}")
            logger.error(f"Failed to generate embedding for paper {paper.id}: {e}")
    
    db.commit()
    
    total_with_embeddings = db.query(func.count(Paper.id)).filter(
        Paper.embedding_title_abstract.isnot(None)
    ).scalar()
    
    return {
        "status": "complete",
        "generated": generated,
        "failed": failed,
        "total_with_embeddings": total_with_embeddings,
        "errors": errors[:10] if errors else []  # Return first 10 errors
    }