"""
Smart Collections API endpoints.
Handles AI-powered automatic paper classification.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any
import logging

from ..database.connection import get_db
from ..database.models import Paper, Collection, Settings
from ..auth import verify_api_key
from ..ai.tasks import classify_paper_smart_collections_task, classify_all_papers_smart_collections_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/collections/smart", tags=["Smart Collections"])


class SmartCollectionsToggleRequest(BaseModel):
    enabled: bool


@router.post("/toggle")
async def toggle_smart_collections(
    request: SmartCollectionsToggleRequest,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Toggle smart collections feature on/off."""
    try:
        Settings.set(db, "smart_collections_enabled", request.enabled)
        
        # If enabling, trigger classification of all papers
        if request.enabled:
            task = classify_all_papers_smart_collections_task.delay()
            return {
                "enabled": request.enabled,
                "task_id": task.id,
                "message": "Smart collections enabled. Classifying all papers..."
            }
        else:
            return {
                "enabled": request.enabled,
                "message": "Smart collections disabled"
            }
            
    except Exception as e:
        logger.error(f"Error toggling smart collections: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_smart_collections_status(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get smart collections status and statistics."""
    try:
        enabled = Settings.get(db, "smart_collections_enabled", False)
        
        # Count smart collections
        smart_collections = db.query(Collection).filter(Collection.is_smart == True).all()
        total_smart_collections = len(smart_collections)
        
        # Count papers in smart collections
        papers_in_smart_collections = set()
        for collection in smart_collections:
            papers_in_smart_collections.update(p.id for p in collection.papers)
        
        total_papers = db.query(Paper).count()
        
        return {
            "enabled": enabled,
            "total_smart_collections": total_smart_collections,
            "smart_collections": [
                {
                    "id": c.id,
                    "name": c.name,
                    "paper_count": len(c.papers)
                }
                for c in smart_collections
            ],
            "total_papers": total_papers,
            "classified_papers": len(papers_in_smart_collections),
            "unclassified_papers": total_papers - len(papers_in_smart_collections)
        }
        
    except Exception as e:
        logger.error(f"Error getting smart collections status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify-all")
async def classify_all_papers(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Trigger classification of all papers."""
    try:
        enabled = Settings.get(db, "smart_collections_enabled", False)
        if not enabled:
            raise HTTPException(
                status_code=400,
                detail="Smart collections is not enabled. Enable it first."
            )
        
        task = classify_all_papers_smart_collections_task.delay()
        
        return {
            "task_id": task.id,
            "status": "started",
            "message": "Classifying all papers in background"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering bulk classification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classify/{paper_id}")
async def classify_single_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Trigger classification of a single paper."""
    try:
        # Check paper exists
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="Paper not found")
        
        enabled = Settings.get(db, "smart_collections_enabled", False)
        if not enabled:
            raise HTTPException(
                status_code=400,
                detail="Smart collections is not enabled. Enable it first."
            )
        
        task = classify_paper_smart_collections_task.delay(paper_id)
        
        return {
            "paper_id": paper_id,
            "task_id": task.id,
            "status": "started",
            "message": "Classifying paper in background"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering paper classification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_smart_collections(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Remove all smart collections (keeps manual ones)."""
    try:
        # Get all smart collections
        smart_collections = db.query(Collection).filter(Collection.is_smart == True).all()
        
        count = len(smart_collections)
        
        # Delete them
        for collection in smart_collections:
            db.delete(collection)
        
        db.commit()
        
        return {
            "deleted_count": count,
            "message": f"Removed {count} smart collections"
        }
        
    except Exception as e:
        logger.error(f"Error clearing smart collections: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
