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

from .agents.metadata_pipeline import MetadataExtractionPipeline

# Load environment variables (helpful when Celery spawns workers)
try:
    from dotenv import load_dotenv
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    load_dotenv(os.path.join(project_root, '.env'))
except Exception:
    pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
if Celery:
    celery_app = Celery(
        "scilib_ai",
        broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        backend=os.getenv("CELERY_RESULT_BACKEND", os.getenv("DATABASE_URL", "postgresql://username:password@localhost/scilib"))
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
def extract_pdf_metadata_task(self, pdf_path: str, paper_id: int, use_llm: bool = False) -> Dict[str, Any]:
    """
    Celery task for extracting metadata from PDF files.
    
    Args:
        pdf_path: Path to the PDF file
        paper_id: Database ID of the paper record
        use_llm: Whether to use LLM for higher accuracy (slower and costs tokens)
        
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
                "status": "Initializing AI extraction pipeline..." + (" (High-Accuracy Mode)" if use_llm else "")
            }
        )
        
        logger.info(f"Starting metadata extraction for paper {paper_id}, file: {pdf_path} (task id: {getattr(self.request, 'id', None)}, use_llm: {use_llm})")
        
        # Initialize the extraction pipeline
        pipeline = MetadataExtractionPipeline(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            exa_api_key=os.getenv("EXA_API_KEY"),
            crossref_email=os.getenv("CROSSREF_EMAIL"),
            semantic_scholar_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
            use_llm=use_llm  # Use provided parameter
        )

        # Log missing credentials for easier debugging
        if use_llm and not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not set in worker environment; LLM calls will fail or fallback will be used.")
        
        # Import asyncio for running async pipeline
        import asyncio
        
        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 10,
                "total": 100,
                "status": "Starting PDF content extraction..."
            }
        )
        
        # Run the extraction pipeline (same call used in minimals/pipeline/test_extraction.py)
        import asyncio
        try:
            logger.info("Invoking MetadataExtractionPipeline.extract_metadata()")
            
            # If use_llm is True (manual re-extraction), force LLM to run even if APIs have results
            force_llm = use_llm
            result = asyncio.run(pipeline.extract_metadata(pdf_path, paper_id, force_llm=force_llm))
            logger.info(f"Pipeline returned for paper {paper_id}: extraction_status={result.get('extraction_status')} confidence={result.get('confidence')} sources={result.get('sources')}")
            
            # If confidence is low (<80%) and LLM is available but not used, retry with LLM
            confidence = result.get('confidence', 0)
            logger.info(f"Checking retry conditions: confidence={confidence:.2%}, use_llm={use_llm}, OPENAI_API_KEY={'set' if os.getenv('OPENAI_API_KEY') else 'not set'}")
            
            if confidence < 0.80 and not use_llm and os.getenv("OPENAI_API_KEY"):
                logger.warning(f"🔄 TRIGGERING LLM RETRY: Low confidence ({confidence:.1%}) detected for paper {paper_id}")
                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": 50,
                        "total": 100,
                        "status": f"Low confidence ({confidence:.0%}), improving with LLM analysis..."
                    }
                )
                
                # Create new pipeline with LLM enabled
                pipeline_with_llm = MetadataExtractionPipeline(
                    openai_api_key=os.getenv("OPENAI_API_KEY"),
                    exa_api_key=os.getenv("EXA_API_KEY"),
                    crossref_email=os.getenv("CROSSREF_EMAIL"),
                    semantic_scholar_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
                    use_llm=True
                )
                
                # Re-run with force_llm=True
                logger.info(f"Re-running extraction with LLM for paper {paper_id}")
                result = asyncio.run(pipeline_with_llm.extract_metadata(pdf_path, paper_id, force_llm=True))
                new_confidence = result.get('confidence', 0)
                
                if new_confidence > confidence:
                    logger.warning(f"✅ LLM improved confidence for paper {paper_id}: {confidence:.1%} → {new_confidence:.1%}")
                else:
                    logger.info(f"LLM confidence for paper {paper_id}: {new_confidence:.1%}")
            elif confidence >= 0.80:
                logger.info(f"Confidence {confidence:.1%} is acceptable, no LLM retry needed")
            elif use_llm:
                logger.info(f"LLM already enabled with force_llm={force_llm}, extraction complete")
            else:
                logger.warning(f"OPENAI_API_KEY not set, cannot retry with LLM")
                    
        except Exception as e:
            logger.error(f"Pipeline invocation raised exception for paper {paper_id}: {e}")
            raise
        
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
        logger.info(f"Database update success: {update_success} for paper {paper_id}")
        
        if not update_success:
            logger.error(f"Failed to update database for paper {paper_id}")
            result["errors"].append("Failed to update database")
        
        # Final status
        final_status = "SUCCESS" if result["extraction_status"] == "completed" else "FAILURE"
        
        logger.info(f"Completed extraction for paper {paper_id} with status: {final_status}")
        
        return {
            "status": final_status,
            "paper_id": paper_id,
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
        from ..database import SessionLocal
        from ..database import Paper as PaperModel
        
        # Create database session with context manager
        with SessionLocal() as db:
            # Find the paper
            paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
            if not paper:
                logger.error(f"Paper {paper_id} not found in database")
                return False
            
            # Store old confidence for comparison
            old_confidence = paper.extraction_confidence or 0.0
            new_confidence = extraction_result.get("confidence", 0.0)
            
            # Only update if new confidence is higher or this is the first extraction
            if new_confidence >= old_confidence:
                logger.info(f"Updating paper {paper_id}: new confidence {new_confidence:.2%} >= old confidence {old_confidence:.2%}")
                
                # Update extraction fields
                paper.extraction_status = extraction_result.get("extraction_status", "failed")
                paper.extraction_confidence = new_confidence
                paper.extraction_sources = extraction_result.get("sources", {})
                paper.extraction_metadata = extraction_result.get("metadata", {})
                paper.extracted_at = datetime.now()
            else:
                logger.info(f"Keeping old data for paper {paper_id}: new confidence {new_confidence:.2%} < old confidence {old_confidence:.2%}")
                # Still update status to completed but keep old data
                paper.extraction_status = extraction_result.get("extraction_status", "completed")
                paper.extracted_at = datetime.now()
                # Don't update confidence, sources, or metadata - keep the better ones
            
            # If successful and high confidence, update main fields
            # Only update if we actually updated the extraction data (new confidence >= old)
            if (paper.extraction_status == "completed" and 
                paper.extraction_confidence >= 0.6 and
                new_confidence >= old_confidence):
                
                metadata = extraction_result.get("metadata", {})
                
                # Update title if not set or AI has better confidence
                if metadata.get("title") and (not paper.title or paper.extraction_confidence > 0.8):
                    paper.title = metadata["title"]
                
                # Update authors if not set or is "Unknown Authors"
                if metadata.get("authors") and (not paper.authors or paper.authors == "Unknown Authors"):
                    # Convert structured authors list to string
                    authors = metadata["authors"]
                    if isinstance(authors, list):
                        author_names = []
                        for author in authors:
                            if isinstance(author, dict):
                                given = author.get("given", "")
                                family = author.get("family", "")
                                name = f"{given} {family}".strip()
                                if name:
                                    author_names.append(name)
                            else:
                                author_names.append(str(author))
                        paper.authors = ", ".join(author_names)
                    else:
                        paper.authors = str(authors)
                
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
        logger.error(f\"Failed to get database connection or update paper {paper_id}: {e}\")
        return False


def run_extraction_sync(pdf_path: str, paper_id: int) -> Dict[str, Any]:
    """
    Run the extraction pipeline synchronously (useful as a fallback when Celery is unavailable).
    This mirrors the behavior in `minimals/pipeline/test_extraction.py`.
    """
    try:
        pipeline = MetadataExtractionPipeline(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            exa_api_key=os.getenv("EXA_API_KEY"),
            crossref_email=os.getenv("CROSSREF_EMAIL"),
            semantic_scholar_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        )
        import asyncio
        logger.info(f"Running synchronous extraction for paper {paper_id}")
        result = asyncio.run(pipeline.extract_metadata(pdf_path, paper_id))
        update_paper_extraction_results(paper_id, result)
        return result
    except Exception as e:
        logger.error(f"Synchronous extraction failed for paper {paper_id}: {e}")
        # Ensure DB reflects failure
        update_paper_extraction_results(paper_id, {"extraction_status": "failed", "errors": [str(e)]})
        return {"extraction_status": "failed", "errors": [str(e)]}


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