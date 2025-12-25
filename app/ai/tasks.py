"""
Celery tasks for background AI metadata extraction.
"""
import os
from typing import Dict, Any
import logging
from datetime import datetime

try:
    from celery import Celery
except ImportError:
    # Handle case where Celery is not installed yet
    Celery = None

from ..agents.metadata_pipeline import MetadataExtractionPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
if Celery:
    celery_app = Celery(
        "scilib_ai",
        broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
    )
    
    # Celery configuration
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 minutes max
        task_soft_time_limit=240,  # 4 minutes soft limit
        worker_prefetch_multiplier=1,
        result_expires=3600,  # 1 hour
    )
else:
    celery_app = None


@celery_app.task(bind=True, name="extract_pdf_metadata")
def extract_pdf_metadata_task(self, pdf_path: str, paper_id: int, user_id: int) -> Dict[str, Any]:
    """
    Celery task for extracting metadata from PDF files.
    
    Args:
        pdf_path: Path to the PDF file
        paper_id: Database ID of the paper record
        user_id: ID of the user who uploaded the paper
        
    Returns:
        Dict with extraction results and metadata
    """
    try:
        # Update task status
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 100,
                "status": "Initializing AI extraction pipeline..."
            }
        )
        
        logger.info(f"Starting metadata extraction for paper {paper_id}, file: {pdf_path}")
        
        # Initialize the extraction pipeline
        pipeline = MetadataExtractionPipeline(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            exa_api_key=os.getenv("EXA_API_KEY"),
            crossref_email=os.getenv("CROSSREF_EMAIL"),
            semantic_scholar_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        )
        
        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 10,
                "total": 100,
                "status": "Starting PDF content extraction..."
            }
        )
        
        # Run the extraction pipeline
        import asyncio
        result = asyncio.run(pipeline.extract_metadata(pdf_path, paper_id))
        
        # Update progress throughout the pipeline
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 90,
                "total": 100,
                "status": "Finalizing results..."
            }
        )
        
        # Update database with results
        update_success = update_paper_extraction_results(paper_id, result)
        
        if not update_success:
            logger.error(f"Failed to update database for paper {paper_id}")
            result["errors"].append("Failed to update database")
        
        # Final status
        final_status = "SUCCESS" if result["extraction_status"] == "completed" else "FAILURE"
        
        logger.info(f"Completed extraction for paper {paper_id} with status: {final_status}")
        
        return {
            "status": final_status,
            "paper_id": paper_id,
            "user_id": user_id,
            "extraction_data": result,
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Extraction failed for paper {paper_id}: {str(e)}")
        
        # Update database with failure status
        try:
            update_paper_extraction_results(paper_id, {
                "extraction_status": "failed",
                "errors": [str(e)]
            })
        except Exception as db_error:
            logger.error(f"Failed to update database with error status: {db_error}")
        
        # Return failure result
        return {
            "status": "FAILURE",
            "paper_id": paper_id,
            "user_id": user_id,
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        }


def update_paper_extraction_results(paper_id: int, extraction_result: Dict) -> bool:
    """
    Update database with extraction results.
    
    Args:
        paper_id: Database ID of the paper
        extraction_result: Results from the extraction pipeline
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Import here to avoid circular imports
        from ...database.connection import get_db
        from ...database.models import Paper
        from sqlalchemy.orm import Session
        
        # Get database session
        db_gen = get_db()
        db: Session = next(db_gen)
        
        try:
            # Find the paper
            paper = db.query(Paper).filter(Paper.id == paper_id).first()
            if not paper:
                logger.error(f"Paper {paper_id} not found in database")
                return False
            
            # Update extraction fields
            paper.extraction_status = extraction_result.get("extraction_status", "failed")
            paper.extraction_confidence = extraction_result.get("confidence", 0.0)
            paper.extraction_sources = extraction_result.get("sources", [])
            paper.extraction_metadata = extraction_result.get("metadata", {})
            
            # If successful and high confidence, update main fields
            if (paper.extraction_status == "completed" and 
                paper.extraction_confidence >= 0.6):
                
                metadata = extraction_result.get("metadata", {})
                
                # Update title if not set or AI has better confidence
                if metadata.get("title") and (not paper.title or paper.extraction_confidence > 0.8):
                    paper.title = metadata["title"]
                
                # Update authors if not set
                if metadata.get("authors") and not paper.authors:
                    paper.authors = metadata["authors"]
                
                # Update year if not set
                if metadata.get("year") and not paper.year:
                    try:
                        import re
                        year_match = re.search(r'\d{4}', metadata["year"])
                        if year_match:
                            paper.year = int(year_match.group())
                    except (ValueError, AttributeError):
                        pass
                
                # Update DOI if not set
                if metadata.get("doi") and not paper.doi:
                    paper.doi = metadata["doi"]
                
                # Update abstract if not set
                if metadata.get("abstract") and not paper.abstract:
                    paper.abstract = metadata["abstract"]
                
                # Update journal if not set
                if metadata.get("journal") and not paper.journal:
                    paper.journal = metadata["journal"]
            
            # Commit changes
            db.commit()
            logger.info(f"Successfully updated paper {paper_id} with extraction results")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database error updating paper {paper_id}: {e}")
            return False
        
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to get database connection: {e}")
        return False


@celery_app.task(name="get_extraction_status")
def get_extraction_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of an extraction task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Dict with task status and progress information
    """
    try:
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id, app=celery_app)
        
        if task_result.state == "PENDING":
            response = {
                "state": task_result.state,
                "current": 0,
                "total": 100,
                "status": "Task is waiting to start..."
            }
        elif task_result.state == "PROGRESS":
            response = {
                "state": task_result.state,
                "current": task_result.info.get("current", 0),
                "total": task_result.info.get("total", 100),
                "status": task_result.info.get("status", "")
            }
        elif task_result.state == "SUCCESS":
            response = {
                "state": task_result.state,
                "current": 100,
                "total": 100,
                "result": task_result.result
            }
        else:  # FAILURE
            response = {
                "state": task_result.state,
                "current": 100,
                "total": 100,
                "error": str(task_result.info)
            }
        
        return response
        
    except Exception as e:
        return {
            "state": "ERROR",
            "error": f"Failed to get task status: {str(e)}"
        }


@celery_app.task(name="cleanup_old_tasks")
def cleanup_old_tasks():
    """
    Periodic task to clean up old task results.
    """
    try:
        # This would be run periodically to clean up old results
        logger.info("Cleaning up old task results")
        # Implementation depends on your Redis/broker setup
        return {"status": "completed", "cleaned_tasks": 0}
        
    except Exception as e:
        logger.error(f"Failed to cleanup old tasks: {e}")
        return {"status": "failed", "error": str(e)}


# Health check task
@celery_app.task(name="health_check")
def health_check() -> Dict[str, str]:
    """
    Simple health check task for monitoring.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "worker": "scilib_ai_worker"
    }