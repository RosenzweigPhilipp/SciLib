"""
Celery tasks for background AI metadata extraction.
"""
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
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


def sanitize_filename(text: str, max_length: int = 100) -> str:
    """
    Sanitize text for use in filenames.
    
    Args:
        text: Text to sanitize
        max_length: Maximum length for the filename component
        
    Returns:
        Sanitized filename-safe string
    """
    if not text:
        return "Unknown"
    
    # Remove or replace invalid filename characters
    # Keep alphanumeric, spaces, hyphens, and underscores
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', str(text))
    
    # Replace multiple spaces with single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # Trim and limit length
    sanitized = sanitized.strip()[:max_length]
    
    return sanitized if sanitized else "Unknown"


def generate_organized_filename(metadata: Dict[str, Any]) -> Optional[str]:
    """
    Generate organized filename from metadata: {author} - {year} - {title}.pdf
    If multiple authors, use "First Author et al."
    
    Args:
        metadata: Extracted metadata dictionary
        
    Returns:
        Organized filename or None if required fields are missing
    """
    try:
        # Extract required fields
        title = metadata.get("title")
        year = metadata.get("year")
        authors = metadata.get("authors")
        
        # Check if we have minimum required info
        if not title:
            logger.info("Cannot organize PDF: missing title")
            return None
        
        # Process author(s)
        author_part = "Unknown Author"
        if authors:
            if isinstance(authors, list) and len(authors) > 0:
                # Get first author
                first_author = authors[0]
                if isinstance(first_author, dict):
                    # Structured author format
                    family = first_author.get("family", "")
                    given = first_author.get("given", "")
                    author_name = family if family else f"{given} {family}".strip()
                else:
                    # Simple string format
                    author_name = str(first_author).split(',')[0].strip()
                
                # Add "et al." if multiple authors
                if len(authors) > 1:
                    author_part = f"{author_name} et al"
                else:
                    author_part = author_name
            elif isinstance(authors, str):
                # String format like "Author1, Author2"
                author_list = authors.split(',')
                author_part = author_list[0].strip()
                if len(author_list) > 1:
                    author_part += " et al"
        
        # Process year
        year_part = ""
        if year:
            # Extract 4-digit year if present
            year_match = re.search(r'\d{4}', str(year))
            if year_match:
                year_part = year_match.group()
        
        if not year_part:
            year_part = "Unknown"
        
        # Sanitize components
        author_part = sanitize_filename(author_part, max_length=50)
        year_part = sanitize_filename(year_part, max_length=20)
        title_part = sanitize_filename(title, max_length=100)
        
        # Construct filename
        filename = f"{author_part} - {year_part} - {title_part}.pdf"
        
        logger.info(f"Generated organized filename: {filename}")
        return filename
        
    except Exception as e:
        logger.error(f"Error generating organized filename: {e}")
        return None


def organize_pdf_file(paper_id: int, current_path: str, metadata: Dict[str, Any]) -> Optional[str]:
    """
    Rename and organize PDF file based on metadata.
    
    Args:
        paper_id: Database ID of the paper
        current_path: Current path of the PDF file
        metadata: Extracted metadata
        
    Returns:
        New file path if successful, None otherwise
    """
    try:
        # Generate new filename
        new_filename = generate_organized_filename(metadata)
        if not new_filename:
            logger.info(f"Skipping PDF organization for paper {paper_id}: insufficient metadata")
            return None
        
        # Get the upload directory (same directory as current file)
        current_file = Path(current_path)
        if not current_file.exists():
            logger.error(f"Current PDF file does not exist: {current_path}")
            return None
        
        upload_dir = current_file.parent
        new_path = upload_dir / new_filename
        
        # Check if target filename already exists
        if new_path.exists() and new_path != current_file:
            # Add a counter to make it unique
            base_name = new_path.stem
            extension = new_path.suffix
            counter = 1
            while new_path.exists():
                new_path = upload_dir / f"{base_name} ({counter}){extension}"
                counter += 1
        
        # Don't rename if it's already the target name
        if new_path == current_file:
            logger.info(f"PDF already has organized name: {current_path}")
            return str(current_path)
        
        # Rename the file
        shutil.move(str(current_file), str(new_path))
        logger.info(f"Organized PDF for paper {paper_id}: {current_file.name} -> {new_path.name}")
        
        return str(new_path)
        
    except Exception as e:
        logger.error(f"Failed to organize PDF for paper {paper_id}: {e}")
        return None


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
        
        # Trigger smart collection classification and summary generation if extraction was successful
        summary_task_id = None
        if update_success and result["extraction_status"] == "completed":
            try:
                from ..database.models import Settings
                from ..database import SessionLocal
                
                db = SessionLocal()
                try:
                    # Trigger smart collection classification if enabled
                    smart_collections_enabled = Settings.get(db, "smart_collections_enabled", False)
                    if smart_collections_enabled:
                        logger.info(f"Triggering smart collection classification for paper {paper_id}")
                        classify_paper_smart_collections_task.delay(paper_id)
                    
                    # Check if LLM knows the paper and can provide summaries
                    logger.info(f"Checking if LLM has knowledge of paper {paper_id}")
                    summary_task = check_and_generate_summary_task.delay(paper_id)
                    summary_task_id = summary_task.id
                    logger.info(f"Summary task ID: {summary_task_id}")
                    
                finally:
                    db.close()
            except Exception as background_error:
                logger.error(f"Failed to trigger background tasks: {background_error}")
        
        # Final status
        final_status = "SUCCESS" if result["extraction_status"] == "completed" else "FAILURE"
        
        logger.info(f"Completed extraction for paper {paper_id} with status: {final_status}")
        logger.info(f"Returning summary_task_id: {summary_task_id}")
        
        result_dict = {
            "status": final_status,
            "paper_id": paper_id,
            "extraction_data": result,
            "completed_at": datetime.now().isoformat(),
            "summary_task_id": summary_task_id
        }
        
        logger.info(f"Full result dict: {result_dict}")
        
        return result_dict
        
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
                
                # Update extended BibTeX fields
                bibtex_fields = ["publisher", "volume", "issue", "pages", "booktitle", 
                                "series", "edition", "isbn", "url", "month", "note", "publication_type"]
                for field in bibtex_fields:
                    if metadata.get(field) and not getattr(paper, field, None):
                        setattr(paper, field, metadata[field])
            
            # Organize PDF file if extraction was successful
            if (paper.extraction_status == "completed" and 
                paper.extraction_confidence >= 0.7 and
                paper.file_path):
                
                logger.info(f"Attempting to organize PDF for paper {paper_id}")
                new_path = organize_pdf_file(paper_id, paper.file_path, extraction_result.get("metadata", {}))
                
                if new_path and new_path != paper.file_path:
                    # Update the file path in database
                    paper.file_path = new_path
                    logger.info(f"Updated file path for paper {paper_id}: {new_path}")
            
            # Commit changes
            db.commit()
            logger.info(f"Successfully updated paper {paper_id} with extraction results")
            return True
            
    except Exception as e:
        logger.error(f"Failed to get database connection or update paper {paper_id}: {e}")
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


@celery_app.task(bind=True, name="generate_paper_embedding")
def generate_paper_embedding_task(self, paper_id: int, force_regenerate: bool = False) -> Dict[str, Any]:
    """
    Celery task for generating embeddings for a paper.
    
    Args:
        paper_id: Database ID of the paper
        force_regenerate: If True, regenerate even if embedding already exists
        
    Returns:
        Dict with embedding generation results
    """
    try:
        # Update task status
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 100,
                "status": "Initializing embedding generation..."
            }
        )
        
        logger.info(f"Starting embedding generation for paper {paper_id} (task id: {getattr(self.request, 'id', None)}, force: {force_regenerate})")
        
        # Import here to avoid circular imports
        from ..database import SessionLocal
        from ..database import Paper as PaperModel
        from .services.embedding_service import EmbeddingService
        import asyncio
        
        # Get paper from database
        with SessionLocal() as db:
            paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
            if not paper:
                logger.error(f"Paper {paper_id} not found in database")
                return {
                    "status": "FAILURE",
                    "paper_id": paper_id,
                    "error": "Paper not found",
                    "failed_at": datetime.now().isoformat()
                }
            
            # Check if embedding already exists
            if paper.embedding_title_abstract is not None and not force_regenerate:
                logger.info(f"Paper {paper_id} already has embedding, skipping")
                return {
                    "status": "SUCCESS",
                    "paper_id": paper_id,
                    "message": "Embedding already exists",
                    "skipped": True,
                    "completed_at": datetime.now().isoformat()
                }
            
            # Extract title and abstract
            title = paper.title
            abstract = paper.abstract
            
            if not title:
                logger.error(f"Paper {paper_id} has no title, cannot generate embedding")
                return {
                    "status": "FAILURE",
                    "paper_id": paper_id,
                    "error": "Paper has no title",
                    "failed_at": datetime.now().isoformat()
                }
        
        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 30,
                "total": 100,
                "status": "Generating embedding..."
            }
        )
        
        # Generate embedding
        embedding = asyncio.run(EmbeddingService.generate_paper_embedding(title, abstract))
        
        if embedding is None:
            logger.error(f"Failed to generate embedding for paper {paper_id}")
            return {
                "status": "FAILURE",
                "paper_id": paper_id,
                "error": "Embedding generation failed",
                "failed_at": datetime.now().isoformat()
            }
        
        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 80,
                "total": 100,
                "status": "Saving embedding to database..."
            }
        )
        
        # Save to database
        with SessionLocal() as db:
            paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
            if paper:
                paper.embedding_title_abstract = embedding
                paper.embedding_generated_at = datetime.now()
                db.commit()
                logger.info(f"Successfully saved embedding for paper {paper_id}")
            else:
                logger.error(f"Paper {paper_id} not found when saving embedding")
                return {
                    "status": "FAILURE",
                    "paper_id": paper_id,
                    "error": "Paper not found when saving",
                    "failed_at": datetime.now().isoformat()
                }
        
        return {
            "status": "SUCCESS",
            "paper_id": paper_id,
            "embedding_dimension": len(embedding),
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Embedding generation failed for paper {paper_id}: {str(e)}", exc_info=True)
        return {
            "status": "FAILURE",
            "paper_id": paper_id,
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        }


@celery_app.task(bind=True, name="generate_paper_summary")
def generate_paper_summary_task(self, paper_id: int, force_regenerate: bool = False) -> Dict[str, Any]:
    """
    Celery task for generating AI summaries for a paper.
    
    Args:
        paper_id: Database ID of the paper
        force_regenerate: If True, regenerate even if summary already exists
        
    Returns:
        Dict with summary generation results
    """
    try:
        # Update task status
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 0,
                "total": 100,
                "status": "Initializing summary generation..."
            }
        )
        
        logger.info(f"Starting summary generation for paper {paper_id} (task id: {getattr(self.request, 'id', None)}, force: {force_regenerate})")
        
        # Import here to avoid circular imports
        from ..database import SessionLocal
        from ..database import Paper as PaperModel
        from .services.summary_service import SummaryService
        import asyncio
        
        # Get paper from database
        with SessionLocal() as db:
            paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
            if not paper:
                logger.error(f"Paper {paper_id} not found in database")
                return {
                    "status": "FAILURE",
                    "paper_id": paper_id,
                    "error": "Paper not found",
                    "failed_at": datetime.now().isoformat()
                }
            
            # Check if summary already exists
            if paper.ai_summary_short is not None and not force_regenerate:
                logger.info(f"Paper {paper_id} already has summary, skipping")
                return {
                    "status": "SUCCESS",
                    "paper_id": paper_id,
                    "message": "Summary already exists",
                    "skipped": True,
                    "completed_at": datetime.now().isoformat()
                }
            
            # Extract paper information
            title = paper.title
            abstract = paper.abstract
            
            if not title:
                logger.error(f"Paper {paper_id} has no title, cannot generate summary")
                return {
                    "status": "FAILURE",
                    "paper_id": paper_id,
                    "error": "Paper has no title",
                    "failed_at": datetime.now().isoformat()
                }
        
        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 20,
                "total": 100,
                "status": "Generating summaries..."
            }
        )
        
        # Generate all summaries in parallel (including ELI5)
        short_summary, detailed_summary, key_findings, eli5_summary = asyncio.run(
            SummaryService.generate_complete_summary(title, abstract)
        )
        
        # Check if at least one component was generated
        if short_summary is None and detailed_summary is None and key_findings is None and eli5_summary is None:
            logger.error(f"Failed to generate any summary components for paper {paper_id}")
            return {
                "status": "FAILURE",
                "paper_id": paper_id,
                "error": "All summary generation attempts failed",
                "failed_at": datetime.now().isoformat()
            }
        
        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "current": 80,
                "total": 100,
                "status": "Saving summaries to database..."
            }
        )
        
        # Save to database
        with SessionLocal() as db:
            paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
            if paper:
                if short_summary:
                    paper.ai_summary_short = short_summary
                if detailed_summary:
                    paper.ai_summary_long = detailed_summary
                if key_findings:
                    paper.ai_key_findings = key_findings
                if eli5_summary:
                    paper.ai_summary_eli5 = eli5_summary
                paper.summary_generated_at = datetime.now()
                paper.summary_generation_method = "manual"
                db.commit()
                
                logger.info(f"Successfully saved summaries for paper {paper_id}")
                logger.info(f"  - Short: {len(short_summary) if short_summary else 0} chars")
                logger.info(f"  - Detailed: {len(detailed_summary) if detailed_summary else 0} chars")
                logger.info(f"  - Findings: {len(key_findings) if key_findings else 0} items")
                logger.info(f"  - ELI5: {len(eli5_summary) if eli5_summary else 0} chars")
            else:
                logger.error(f"Paper {paper_id} not found when saving summaries")
                return {
                    "status": "FAILURE",
                    "paper_id": paper_id,
                    "error": "Paper not found when saving",
                    "failed_at": datetime.now().isoformat()
                }
        
        return {
            "status": "SUCCESS",
            "paper_id": paper_id,
            "generated_components": {
                "short_summary": short_summary is not None,
                "detailed_summary": detailed_summary is not None,
                "key_findings": key_findings is not None,
                "eli5_summary": eli5_summary is not None
            },
            "completed_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Summary generation failed for paper {paper_id}: {str(e)}", exc_info=True)
        return {
            "status": "FAILURE",
            "paper_id": paper_id,
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        }


@celery_app.task(bind=True, name="check_and_generate_summary")
def check_and_generate_summary_task(self, paper_id: int) -> Dict[str, Any]:
    """
    Check if LLM knows the paper, then generate summaries if it does.
    This is much more token-efficient than extracting from full text.
    
    Args:
        paper_id: Database ID of the paper
        
    Returns:
        Dict with check results and summary generation status
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Checking if LLM knows this paper..."}
        )
        
        logger.info(f"Checking LLM knowledge for paper {paper_id}")
        
        from ..database import SessionLocal
        from ..database.models import Paper
        from .services.paper_knowledge_check import PaperKnowledgeService
        
        db = SessionLocal()
        try:
            # Get paper
            paper = db.query(Paper).filter(Paper.id == paper_id).first()
            if not paper:
                return {
                    "status": "FAILURE",
                    "paper_id": paper_id,
                    "error": "Paper not found"
                }
            
            # Check if LLM knows the paper
            service = PaperKnowledgeService(os.getenv("OPENAI_API_KEY"))
            check_result = service.check_paper_knowledge(
                title=paper.title,
                authors=paper.authors,
                year=paper.year,
                doi=paper.doi
            )
            
            logger.info(f"LLM knowledge check for paper {paper_id}: has_knowledge={check_result['has_knowledge']}, confidence={check_result['confidence']}")
            
            # Save knowledge check result to database
            paper.llm_knowledge_check = check_result["has_knowledge"]
            paper.llm_knowledge_confidence = check_result["confidence"]
            paper.llm_knowledge_checked_at = datetime.now()
            db.commit()
            
            # If LLM knows the paper with good confidence, generate summaries
            if check_result["has_knowledge"] and check_result["confidence"] >= 0.7:
                self.update_state(
                    state="PROGRESS",
                    meta={"current": 50, "total": 100, "status": "LLM knows this paper! Generating summaries..."}
                )
                
                logger.info(f"Generating summaries from LLM knowledge for paper {paper_id}")
                summaries = service.generate_summaries_from_knowledge(
                    title=paper.title,
                    authors=paper.authors,
                    year=paper.year
                )
                
                logger.info(f"Summary generation result: {summaries}")
                
                if "error" not in summaries:
                    # Enrich metadata while LLM has knowledge of the paper
                    try:
                        from .agents.metadata_enrichment import enrich_metadata_with_llm
                        
                        existing_metadata = {
                            "title": paper.title,
                            "authors": paper.authors,
                            "year": paper.year,
                            "journal": paper.journal,
                            "doi": paper.doi,
                            "abstract": paper.abstract,
                            "publisher": paper.publisher,
                            "volume": paper.volume,
                            "issue": paper.issue,
                            "pages": paper.pages,
                            "booktitle": paper.booktitle,
                            "isbn": paper.isbn,
                            "url": paper.url,
                            "month": paper.month,
                            "publication_type": paper.publication_type
                        }
                        
                        logger.info(f"Enriching metadata for paper {paper_id}")
                        enriched_fields = service.run_async(
                            enrich_metadata_with_llm(
                                existing_metadata,
                                os.getenv("OPENAI_API_KEY")
                            )
                        )
                        
                        if enriched_fields:
                            logger.info(f"Enriched {len(enriched_fields)} fields: {list(enriched_fields.keys())}")
                            # Apply enriched fields to paper
                            for field, value in enriched_fields.items():
                                if hasattr(paper, field):
                                    setattr(paper, field, value)
                        else:
                            logger.info("No additional metadata enrichment available")
                    
                    except Exception as enrich_error:
                        logger.warning(f"Metadata enrichment failed for paper {paper_id}: {enrich_error}")
                        # Don't fail the whole task if enrichment fails
                    
                    # Save to database
                    short = summaries.get("short_summary")
                    long = summaries.get("long_summary")
                    findings = summaries.get("key_findings")
                    eli5 = summaries.get("eli5_summary")
                    
                    if short or long or findings or eli5:
                        paper.ai_summary_short = short
                        paper.ai_summary_long = long
                        paper.ai_key_findings = findings
                        paper.ai_summary_eli5 = eli5
                        paper.summary_generated_at = datetime.now()
                        paper.summary_generation_method = "llm_knowledge"
                        db.commit()
                        
                        logger.info(f"Successfully saved summaries for paper {paper_id}: short={bool(short)}, long={bool(long)}, findings={len(findings) if findings else 0}, eli5={bool(eli5)}")
                        
                        return {
                            "status": "SUCCESS",
                            "paper_id": paper_id,
                            "method": "llm_knowledge",
                            "check_result": check_result,
                            "summaries_generated": True,
                            "completed_at": datetime.now().isoformat()
                        }
                    else:
                        logger.warning(f"LLM returned empty summaries for paper {paper_id}")
                else:
                    logger.error(f"Error generating summaries from LLM knowledge: {summaries.get('error')}")
            
            # LLM doesn't know the paper well enough - user can manually trigger full extraction
            logger.info(f"LLM does not have sufficient knowledge of paper {paper_id} (confidence: {check_result['confidence']}). Manual summary generation available.")
            
            return {
                "status": "SUCCESS",
                "paper_id": paper_id,
                "method": "check_only",
                "check_result": check_result,
                "summaries_generated": False,
                "message": "LLM does not know this paper. Use manual summary generation.",
                "completed_at": datetime.now().isoformat()
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Knowledge check failed for paper {paper_id}: {str(e)}", exc_info=True)
        return {
            "status": "FAILURE",
            "paper_id": paper_id,
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        }


@celery_app.task(bind=True, name="classify_paper_smart_collections")
def classify_paper_smart_collections_task(self, paper_id: int) -> Dict[str, Any]:
    """
    Celery task for classifying a single paper into smart collections.
    
    Args:
        paper_id: Database ID of the paper
        
    Returns:
        Dict with classification results
    """
    try:
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Analyzing paper..."}
        )
        
        logger.info(f"Starting smart classification for paper {paper_id}")
        
        from ..database import SessionLocal
        from ..database.models import Paper, Collection, Settings
        from .services.smart_collection_service import SmartCollectionService
        
        db = SessionLocal()
        try:
            # Check if smart collections is enabled
            enabled = Settings.get(db, "smart_collections_enabled", False)
            if not enabled:
                return {
                    "status": "SKIPPED",
                    "paper_id": paper_id,
                    "message": "Smart collections is disabled"
                }
            
            # Get paper
            paper = db.query(Paper).filter(Paper.id == paper_id).first()
            if not paper:
                return {
                    "status": "FAILURE",
                    "paper_id": paper_id,
                    "error": "Paper not found"
                }
            
            # Classify paper
            self.update_state(
                state="PROGRESS",
                meta={"current": 30, "total": 100, "status": "Classifying with AI..."}
            )
            
            service = SmartCollectionService(os.getenv("OPENAI_API_KEY"))
            fields = service.classify_paper(paper.title, paper.abstract)
            
            if not fields:
                return {
                    "status": "FAILURE",
                    "paper_id": paper_id,
                    "error": "No fields identified"
                }
            
            # Create/get collections and add paper
            self.update_state(
                state="PROGRESS",
                meta={"current": 70, "total": 100, "status": "Adding to collections..."}
            )
            
            # First, remove existing smart collections from this paper
            existing_smart_collections = [c for c in paper.collections if c.is_smart]
            for collection in existing_smart_collections:
                paper.collections.remove(collection)
            
            added_collections = []
            for field_data in fields:
                field_name = field_data.get('name') if isinstance(field_data, dict) else field_data
                field_description = field_data.get('description', f"Auto-generated collection for {field_name} research") if isinstance(field_data, dict) else f"Auto-generated collection for {field_name} research"
                
                # Check if collection exists (smart or not)
                collection = db.query(Collection).filter(
                    Collection.name == field_name
                ).first()
                
                if not collection:
                    # Create new smart collection with AI-generated description
                    collection = Collection(
                        name=field_name,
                        description=field_description,
                        is_smart=True
                    )
                    db.add(collection)
                    db.flush()
                elif not collection.is_smart:
                    # Convert existing collection to smart with AI description
                    collection.is_smart = True
                    collection.description = field_description
                
                if collection not in paper.collections:
                    paper.collections.append(collection)
                    added_collections.append(field_name)
            
            db.commit()
            
            field_names = [f.get('name') if isinstance(f, dict) else f for f in fields]
            logger.info(f"Paper {paper_id} classified into: {field_names}")
            
            return {
                "status": "SUCCESS",
                "paper_id": paper_id,
                "fields": field_names,
                "added_collections": added_collections,
                "completed_at": datetime.now().isoformat()
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Smart classification failed for paper {paper_id}: {e}")
        return {
            "status": "FAILURE",
            "paper_id": paper_id,
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        }


@celery_app.task(bind=True, name="classify_all_papers_smart_collections")
def classify_all_papers_smart_collections_task(self) -> Dict[str, Any]:
    """
    Celery task for classifying all papers in the database.
    
    Returns:
        Dict with classification results for all papers
    """
    try:
        logger.info("Starting bulk smart classification")
        
        from ..database import SessionLocal
        from ..database.models import Paper, Settings
        
        db = SessionLocal()
        try:
            # Check if enabled
            enabled = Settings.get(db, "smart_collections_enabled", False)
            if not enabled:
                return {
                    "status": "SKIPPED",
                    "message": "Smart collections is disabled"
                }
            
            # Get all papers
            papers = db.query(Paper).all()
            total = len(papers)
            
            self.update_state(
                state="PROGRESS",
                meta={"current": 0, "total": total, "status": f"Dispatching {total} classification tasks..."}
            )
            
            # Dispatch classification tasks asynchronously
            task_ids = []
            for paper in papers:
                task = classify_paper_smart_collections_task.delay(paper.id)
                task_ids.append(task.id)
            
            logger.info(f"Dispatched {len(task_ids)} classification tasks")
            
            return {
                "status": "SUCCESS",
                "total_papers": total,
                "task_ids": task_ids,
                "message": f"Dispatched {total} classification tasks",
                "completed_at": datetime.now().isoformat()
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Bulk classification failed: {e}")
        return {
            "status": "FAILURE",
            "error": str(e),
            "failed_at": datetime.now().isoformat()
        }
