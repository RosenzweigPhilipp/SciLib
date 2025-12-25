"""
API endpoints for AI metadata extraction functionality.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import logging
import os

from ..database.connection import get_db
from ..database.models import Paper
from ..auth import verify_session_token
from .tasks import extract_pdf_metadata_task, get_extraction_status, celery_app

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/ai", tags=["AI Extraction"])


@router.post("/extract/{paper_id}")
async def trigger_metadata_extraction(
    paper_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Trigger AI metadata extraction for a paper.
    
    Args:
        paper_id: ID of the paper to extract metadata for
        background_tasks: FastAPI background tasks
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Dict with task information
    """
    try:
        # Get the paper
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paper not found"
            )
        
        # Check if user owns this paper or is admin
        if paper.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to extract metadata for this paper"
            )
        
        # Check if paper has a PDF file
        if not paper.file_path or not os.path.exists(paper.file_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No PDF file found for this paper"
            )
        
        # Check if extraction is already in progress
        if paper.extraction_status == "processing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Extraction already in progress for this paper"
            )
        
        # Update status to processing
        paper.extraction_status = "processing"
        paper.extraction_confidence = 0.0
        paper.extraction_sources = []
        paper.extraction_metadata = {}
        db.commit()
        
        # Start the extraction task
        if celery_app:
            task = extract_pdf_metadata_task.delay(
                pdf_path=paper.file_path,
                paper_id=paper.id,
                user_id=current_user.id
            )
            task_id = task.id
        else:
            # Fallback: run in background task if Celery not available
            task_id = f"bg_{paper_id}_{current_user.id}"
            background_tasks.add_task(
                run_extraction_fallback,
                paper.file_path,
                paper.id,
                current_user.id
            )
        
        logger.info(f"Started metadata extraction task {task_id} for paper {paper_id}")
        
        return {
            "task_id": task_id,
            "paper_id": paper_id,
            "status": "started",
            "message": "Metadata extraction started in background"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start extraction for paper {paper_id}: {e}")
        
        # Reset status on error
        try:
            paper.extraction_status = "failed"
            db.commit()
        except:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start metadata extraction: {str(e)}"
        )


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the status of a metadata extraction task.
    
    Args:
        task_id: Celery task ID
        current_user: Authenticated user
        
    Returns:
        Dict with task status and progress
    """
    try:
        if celery_app:
            status_result = get_extraction_status(task_id)
            return status_result
        else:
            # Fallback for background tasks
            return {
                "state": "PROGRESS",
                "current": 50,
                "total": 100,
                "status": "Processing in background (Celery not available)"
            }
            
    except Exception as e:
        logger.error(f"Failed to get status for task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.get("/paper/{paper_id}/extraction")
async def get_paper_extraction_data(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get extraction results for a paper.
    
    Args:
        paper_id: ID of the paper
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Dict with extraction data
    """
    try:
        # Get the paper
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paper not found"
            )
        
        # Check access
        if paper.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view extraction data for this paper"
            )
        
        return {
            "paper_id": paper.id,
            "extraction_status": paper.extraction_status,
            "extraction_confidence": paper.extraction_confidence,
            "extraction_sources": paper.extraction_sources or [],
            "extraction_metadata": paper.extraction_metadata or {},
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "doi": paper.doi,
            "abstract": paper.abstract,
            "journal": paper.journal,
            "updated_at": paper.updated_at.isoformat() if paper.updated_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get extraction data for paper {paper_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get extraction data: {str(e)}"
        )


@router.post("/paper/{paper_id}/approve")
async def approve_extraction_results(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Approve and apply AI extraction results to the paper.
    
    Args:
        paper_id: ID of the paper
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    try:
        # Get the paper
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paper not found"
            )
        
        # Check access
        if paper.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to approve extraction for this paper"
            )
        
        # Check if there are extraction results
        if not paper.extraction_metadata:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No extraction results to approve"
            )
        
        # Apply extraction results to main paper fields
        metadata = paper.extraction_metadata
        
        if metadata.get("title"):
            paper.title = metadata["title"]
        
        if metadata.get("authors"):
            paper.authors = metadata["authors"]
        
        if metadata.get("year"):
            try:
                import re
                year_match = re.search(r'\d{4}', metadata["year"])
                if year_match:
                    paper.year = int(year_match.group())
            except (ValueError, AttributeError):
                pass
        
        if metadata.get("doi"):
            paper.doi = metadata["doi"]
        
        if metadata.get("abstract"):
            paper.abstract = metadata["abstract"]
        
        if metadata.get("journal"):
            paper.journal = metadata["journal"]
        
        # Mark extraction as approved
        paper.extraction_status = "approved"
        
        db.commit()
        
        logger.info(f"Approved extraction results for paper {paper_id}")
        
        return {
            "message": "Extraction results approved and applied",
            "paper_id": paper_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve extraction for paper {paper_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve extraction results: {str(e)}"
        )


@router.post("/paper/{paper_id}/reject")
async def reject_extraction_results(
    paper_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Reject AI extraction results for a paper.
    
    Args:
        paper_id: ID of the paper
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Success message
    """
    try:
        # Get the paper
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paper not found"
            )
        
        # Check access
        if paper.user_id != current_user.id and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to reject extraction for this paper"
            )
        
        # Mark extraction as rejected
        paper.extraction_status = "rejected"
        paper.extraction_confidence = 0.0
        
        db.commit()
        
        logger.info(f"Rejected extraction results for paper {paper_id}")
        
        return {
            "message": "Extraction results rejected",
            "paper_id": paper_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject extraction for paper {paper_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject extraction results: {str(e)}"
        )


@router.get("/health")
async def ai_health_check() -> Dict[str, Any]:
    """
    Health check for AI extraction services.
    
    Returns:
        Health status information
    """
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check Celery
    if celery_app:
        try:
            # Simple task to check if worker is available
            from .tasks import health_check
            task = health_check.delay()
            result = task.get(timeout=5)
            health_status["services"]["celery"] = "healthy"
        except Exception as e:
            health_status["services"]["celery"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["celery"] = "not available"
    
    # Check required API keys
    required_keys = ["OPENAI_API_KEY"]
    optional_keys = ["EXA_API_KEY", "SEMANTIC_SCHOLAR_API_KEY"]
    
    health_status["services"]["api_keys"] = {}
    
    for key in required_keys:
        if os.getenv(key):
            health_status["services"]["api_keys"][key] = "configured"
        else:
            health_status["services"]["api_keys"][key] = "missing"
            health_status["status"] = "degraded"
    
    for key in optional_keys:
        if os.getenv(key):
            health_status["services"]["api_keys"][key] = "configured"
        else:
            health_status["services"]["api_keys"][key] = "not configured"
    
    return health_status


async def run_extraction_fallback(pdf_path: str, paper_id: int, user_id: int):
    """
    Fallback function to run extraction without Celery.
    
    Args:
        pdf_path: Path to PDF file
        paper_id: Paper ID
        user_id: User ID
    """
    try:
        logger.info(f"Running extraction fallback for paper {paper_id}")
        
        # Import and run the extraction
        from .agents.metadata_pipeline import MetadataExtractionPipeline
        
        pipeline = MetadataExtractionPipeline(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            exa_api_key=os.getenv("EXA_API_KEY"),
            crossref_email=os.getenv("CROSSREF_EMAIL"),
            semantic_scholar_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        )
        
        result = await pipeline.extract_metadata(pdf_path, paper_id)
        
        # Update database
        from .tasks import update_paper_extraction_results
        update_paper_extraction_results(paper_id, result)
        
        logger.info(f"Completed extraction fallback for paper {paper_id}")
        
    except Exception as e:
        logger.error(f"Extraction fallback failed for paper {paper_id}: {e}")
        
        # Update database with failure
        try:
            from .tasks import update_paper_extraction_results
            update_paper_extraction_results(paper_id, {
                "extraction_status": "failed",
                "errors": [str(e)]
            })
        except Exception:
            pass