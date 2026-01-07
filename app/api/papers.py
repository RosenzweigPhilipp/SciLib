from fastapi import APIRouter, HTTPException, UploadFile, File, Query, status, Depends
from sqlalchemy.orm import Session
from typing import List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
import os
import shutil
from ..database import get_db, Paper as PaperModel
from ..config import settings

# Import AI task for metadata extraction
try:
    from ..ai.tasks import extract_pdf_metadata_task
except ImportError:
    extract_pdf_metadata_task = None

router = APIRouter(prefix="/papers", tags=["papers"])


# Nested schemas for relationships
class CollectionBase(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_smart: Optional[bool] = False
    
    class Config:
        from_attributes = True


class TagBase(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    
    class Config:
        from_attributes = True


class Paper(BaseModel):
    id: int
    title: str
    authors: str
    abstract: Optional[str] = None
    keywords: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    file_path: str
    created_at: datetime
    updated_at: datetime
    
    # Extended BibTeX fields
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    booktitle: Optional[str] = None
    series: Optional[str] = None
    edition: Optional[str] = None
    chapter: Optional[str] = None
    isbn: Optional[str] = None
    url: Optional[str] = None
    month: Optional[int] = None
    note: Optional[str] = None
    institution: Optional[str] = None
    report_number: Optional[str] = None
    publication_type: Optional[str] = None
    
    # AI Extraction fields
    extraction_status: Optional[str] = None
    extraction_confidence: Optional[float] = None
    extraction_sources: Optional[Any] = None  # Can be JSON string or parsed object
    extraction_metadata: Optional[Any] = None  # Can be JSON string or parsed object
    extracted_at: Optional[datetime] = None
    
    # AI Summary fields
    ai_summary_short: Optional[str] = None
    ai_summary_long: Optional[str] = None
    ai_summary_eli5: Optional[str] = None
    ai_key_findings: Optional[List[str]] = None
    summary_generated_at: Optional[datetime] = None
    summary_generation_method: Optional[str] = None
    
    # LLM Knowledge Check fields
    llm_knowledge_check: Optional[bool] = None
    llm_knowledge_confidence: Optional[float] = None
    llm_knowledge_checked_at: Optional[datetime] = None
    
    # Relationships
    collections: List[CollectionBase] = []
    tags: List[TagBase] = []
    
    class Config:
        from_attributes = True


class PaperCreate(BaseModel):
    title: str
    authors: str
    abstract: Optional[str] = None
    keywords: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    booktitle: Optional[str] = None
    series: Optional[str] = None
    edition: Optional[str] = None
    chapter: Optional[str] = None
    isbn: Optional[str] = None
    url: Optional[str] = None
    month: Optional[int] = None
    note: Optional[str] = None
    institution: Optional[str] = None
    report_number: Optional[str] = None
    publication_type: Optional[str] = None


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    keywords: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    booktitle: Optional[str] = None
    series: Optional[str] = None
    edition: Optional[str] = None
    chapter: Optional[str] = None
    isbn: Optional[str] = None
    url: Optional[str] = None
    month: Optional[int] = None
    note: Optional[str] = None
    institution: Optional[str] = None
    report_number: Optional[str] = None
    publication_type: Optional[str] = None


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_paper(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a new paper PDF. Returns created paper and background task id (if started)."""
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Create upload directory if it doesn't exist
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    # Save the uploaded file
    file_path = os.path.join(settings.upload_dir, file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    
    # Create paper record in database
    paper = PaperModel(
        title=file.filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ').title(),
        authors="Unknown Authors",
        file_path=file_path,
        extraction_status="pending",  # Mark for AI extraction
        extraction_confidence=0.0
    )
    
    db.add(paper)
    db.commit()
    db.refresh(paper)
    
    # Trigger AI metadata extraction task if available
    task_id = None
    if extract_pdf_metadata_task:
        try:
            # Start the background task for metadata extraction
            task = extract_pdf_metadata_task.delay(
                pdf_path=file_path,
                paper_id=paper.id
            )
            task_id = task.id
            print(f"DEBUG: Started AI extraction task {task.id} for paper {paper.id}")
            try:
                # Mark paper as processing so UI reflects background work
                paper.extraction_status = "processing"
                db.add(paper)
                db.commit()
                db.refresh(paper)
            except Exception:
                pass
        except Exception as e:
            print(f"DEBUG: Failed to start AI extraction task: {e}")
    else:
        print("DEBUG: AI extraction task not available")

    # Return paper and task id so frontend can poll for status
    return {
        "paper": paper,
        "task_id": task_id
    }


@router.post("/upload-batch", status_code=status.HTTP_201_CREATED)
async def upload_papers_batch(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """
    Upload multiple paper PDFs in a batch.
    
    Returns a list of results for each file, including paper data and task IDs
    for parallel metadata extraction.
    """
    results = []
    
    # Create upload directory if it doesn't exist
    os.makedirs(settings.upload_dir, exist_ok=True)
    
    for file in files:
        result = {
            "filename": file.filename,
            "success": False,
            "paper": None,
            "task_id": None,
            "error": None
        }
        
        # Validate file type
        if not file.filename.endswith('.pdf'):
            result["error"] = "Only PDF files are allowed"
            results.append(result)
            continue
        
        # Save the uploaded file
        file_path = os.path.join(settings.upload_dir, file.filename)
        
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            result["error"] = f"Failed to save file: {str(e)}"
            results.append(result)
            continue
        
        # Create paper record in database
        try:
            paper = PaperModel(
                title=file.filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ').title(),
                authors="Unknown Authors",
                file_path=file_path,
                extraction_status="pending",
                extraction_confidence=0.0
            )
            
            db.add(paper)
            db.commit()
            db.refresh(paper)
            
            result["success"] = True
            result["paper"] = {
                "id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "file_path": paper.file_path,
                "extraction_status": paper.extraction_status
            }
            
            # Trigger AI metadata extraction task if available
            if extract_pdf_metadata_task:
                try:
                    task = extract_pdf_metadata_task.delay(
                        pdf_path=file_path,
                        paper_id=paper.id
                    )
                    result["task_id"] = task.id
                    print(f"DEBUG: Started AI extraction task {task.id} for paper {paper.id}")
                    
                    # Mark paper as processing
                    paper.extraction_status = "processing"
                    db.add(paper)
                    db.commit()
                except Exception as e:
                    print(f"DEBUG: Failed to start AI extraction task: {e}")
                    result["error"] = f"Upload succeeded but extraction task failed: {str(e)}"
            
        except Exception as e:
            result["error"] = f"Failed to create paper record: {str(e)}"
            # Clean up the file if database insert failed
            try:
                os.remove(file_path)
            except:
                pass
        
        results.append(result)
    
    return {
        "total": len(files),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results
    }


@router.get("/", response_model=List[Paper])
async def list_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List papers with pagination and optional search"""
    from sqlalchemy.orm import joinedload
    query = db.query(PaperModel).options(
        joinedload(PaperModel.collections),
        joinedload(PaperModel.tags)
    )
    
    if search:
        query = query.filter(
            (PaperModel.title.contains(search)) |
            (PaperModel.authors.contains(search)) |
            (PaperModel.abstract.contains(search))
        )
    
    papers = query.offset(skip).limit(limit).all()
    return papers


@router.get("/{paper_id}", response_model=Paper)
async def get_paper(paper_id: int, db: Session = Depends(get_db)):
    """Get a specific paper by ID"""
    from sqlalchemy.orm import joinedload
    paper = db.query(PaperModel).options(
        joinedload(PaperModel.collections),
        joinedload(PaperModel.tags)
    ).filter(PaperModel.id == paper_id).first()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    return paper


@router.put("/{paper_id}", response_model=Paper)
async def update_paper(paper_id: int, paper_update: PaperUpdate, db: Session = Depends(get_db)):
    """Update paper metadata"""
    paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    update_data = paper_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(paper, field, value)
    
    db.commit()
    db.refresh(paper)
    return paper


@router.delete("/clear-all", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all_papers(db: Session = Depends(get_db)):
    """Delete all papers and uploaded files (administrative action)."""
    try:
        from ..database.models import paper_collections, paper_tags
        
        # Delete association tables first (foreign key constraints)
        db.execute(paper_collections.delete())
        db.execute(paper_tags.delete())
        
        # Get all papers
        papers = db.query(PaperModel).all()
        
        # Delete files from disk
        for p in papers:
            try:
                if p.file_path and os.path.exists(p.file_path):
                    os.remove(p.file_path)
            except Exception:
                # ignore file removal errors
                pass

        # Delete all papers
        db.query(PaperModel).delete()
        db.commit()
        return
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear papers: {e}")


@router.delete("/clear-database", status_code=status.HTTP_204_NO_CONTENT)
async def clear_entire_database(db: Session = Depends(get_db)):
    """Delete ALL data from the database including papers, collections, tags, and associations (administrative action)."""
    try:
        from ..database.models import Collection, Tag, paper_collections, paper_tags
        
        # Delete association tables first (foreign key constraints)
        db.execute(paper_collections.delete())
        db.execute(paper_tags.delete())
        
        # Delete papers and their files
        papers = db.query(PaperModel).all()
        for p in papers:
            try:
                if p.file_path and os.path.exists(p.file_path):
                    os.remove(p.file_path)
            except Exception:
                # ignore file removal errors
                pass
        
        # Delete all main tables
        db.query(PaperModel).delete()
        db.query(Collection).delete()
        db.query(Tag).delete()
        
        db.commit()
        return
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear database: {e}")


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    """Delete a paper"""
    paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    # Delete the actual file
    if os.path.exists(paper.file_path):
        os.remove(paper.file_path)
    
    db.delete(paper)
    db.commit()
    return


class ReExtractRequest(BaseModel):
    use_llm: bool = True


@router.post("/{paper_id}/re-extract")
async def re_extract_metadata(paper_id: int, request: ReExtractRequest, db: Session = Depends(get_db)):
    """Re-extract metadata for a paper with higher accuracy using LLM"""
    paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    if not os.path.exists(paper.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper file not found"
        )
    
    # Mark paper as processing
    paper.extraction_status = "processing"
    db.commit()
    db.refresh(paper)
    
    # Trigger AI metadata extraction task with LLM enabled
    task_id = None
    if extract_pdf_metadata_task:
        try:
            # Start the background task with use_llm flag directly
            logger_msg = f"Triggering re-extraction for paper {paper.id} with use_llm={request.use_llm}"
            print(f"DEBUG: {logger_msg}")
            
            task = extract_pdf_metadata_task.apply_async(
                args=[paper.file_path, paper.id],
                kwargs={'use_llm': request.use_llm}
            )
            task_id = task.id
            print(f"DEBUG: Started high-accuracy extraction task {task.id} for paper {paper.id} (LLM: {request.use_llm})")
            print(f"DEBUG: Task state: {task.state}, Task ready: {task.ready()}")
            
        except Exception as e:
            print(f"ERROR: Failed to start re-extraction task: {e}")
            import traceback
            traceback.print_exc()
            paper.extraction_status = "failed"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to start re-extraction: {str(e)}"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI extraction service not available"
        )
    
    return {
        "paper_id": paper.id,
        "task_id": task_id,
        "status": "processing",
        "message": "High-accuracy extraction started with LLM" if request.use_llm else "Standard extraction started"
    }


@router.get("/{paper_id}/summary")
async def get_paper_summary(paper_id: int, db: Session = Depends(get_db)):
    """
    Get AI-generated summary for a paper.
    
    Returns short summary, detailed summary, and key findings if available.
    """
    paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
    
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    return {
        "paper_id": paper.id,
        "title": paper.title,
        "short_summary": paper.ai_summary_short,
        "detailed_summary": paper.ai_summary_long,
        "key_findings": paper.ai_key_findings,
        "generated_at": paper.summary_generated_at,
        "has_summary": paper.ai_summary_short is not None
    }


class SummarizePaperRequest(BaseModel):
    force_regenerate: bool = False


@router.post("/{paper_id}/summarize")
async def generate_paper_summary(
    paper_id: int, 
    request: SummarizePaperRequest = SummarizePaperRequest(),
    db: Session = Depends(get_db)
):
    """
    Generate or regenerate AI summary for a paper.
    
    Triggers a background task to generate short summary, detailed summary, 
    and key findings.
    """
    # Import task here to avoid circular dependency
    try:
        from ..ai.tasks import generate_paper_summary_task
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Summarization service not available"
        )
    
    paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
    
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    # Check if summary already exists
    if paper.ai_summary_short and not request.force_regenerate:
        return {
            "paper_id": paper.id,
            "status": "exists",
            "message": "Summary already exists. Use force_regenerate=true to regenerate."
        }
    
    # Trigger summarization task
    try:
        task = generate_paper_summary_task.apply_async(
            args=[paper.id],
            kwargs={'force_regenerate': request.force_regenerate}
        )
        task_id = task.id
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start summarization: {str(e)}"
        )
    
    return {
        "paper_id": paper.id,
        "task_id": task_id,
        "status": "processing",
        "message": "Summary generation started"
    }


# ============================================
# Recommendation Endpoints
# ============================================

class RecommendationResponse(BaseModel):
    """Single recommendation response"""
    paper_id: int
    title: str
    authors: str
    abstract: Optional[str]
    year: Optional[int]
    journal: Optional[str]
    doi: Optional[str]
    score: float
    primary_reason: str
    strategy_scores: dict
    has_summary: bool
    has_embedding: bool


class RecommendationsResponse(BaseModel):
    """List of recommendations for a paper"""
    paper_id: int
    total_recommendations: int
    from_cache: bool
    generated_at: Optional[str] = None
    recommendations: List[RecommendationResponse]


@router.get("/{paper_id}/recommendations", response_model=RecommendationsResponse)
def get_paper_recommendations(
    paper_id: int,
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations"),
    force_refresh: bool = Query(False, description="Force regenerate recommendations"),
    db: Session = Depends(get_db)
):
    """
    Get recommendations for a paper.
    
    Returns similar papers from the library based on multiple strategies:
    - Vector similarity (semantic content)
    - Tag similarity (shared tags)
    - Collection similarity (same collections)
    - Author similarity (shared authors)
    - Year proximity (published around same time)
    
    Results are cached for 7 days by default.
    """
    # Check paper exists
    paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    # Import here to avoid circular imports
    from app.ai.services import get_recommendations
    
    # Get recommendations (uses cache if available)
    try:
        recommendations = get_recommendations(
            db=db,
            paper_id=paper_id,
            limit=limit,
            use_cache=True,
            force_refresh=force_refresh
        )
        
        # Check if from cache
        from_cache = False
        generated_at = None
        if not force_refresh and paper.extraction_metadata:
            cached = paper.extraction_metadata.get("recommendations")
            if cached:
                from_cache = True
                generated_at = cached.get("generated_at")
        
        return RecommendationsResponse(
            paper_id=paper_id,
            total_recommendations=len(recommendations),
            from_cache=from_cache,
            generated_at=generated_at,
            recommendations=[RecommendationResponse(**rec) for rec in recommendations]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


@router.post("/{paper_id}/recommendations/refresh")
def refresh_paper_recommendations(
    paper_id: int,
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Force refresh recommendations for a paper.
    
    Regenerates recommendations even if cached results exist.
    """
    # Check paper exists
    paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    from app.ai.services import get_recommendations
    
    try:
        recommendations = get_recommendations(
            db=db,
            paper_id=paper_id,
            limit=limit,
            use_cache=False,
            force_refresh=True
        )
        
        return {
            "paper_id": paper_id,
            "status": "completed",
            "total_recommendations": len(recommendations),
            "message": f"Generated {len(recommendations)} fresh recommendations"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh recommendations: {str(e)}"
        )


@router.get("/{paper_id}/bibtex")
async def get_paper_bibtex(
    paper_id: int,
    db: Session = Depends(get_db)
):
    """
    Export paper metadata as BibTeX entry.
    
    Returns a properly formatted BibTeX entry with all available metadata fields.
    """
    from fastapi.responses import PlainTextResponse
    
    # Get paper
    paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    # Generate BibTeX citation key (author_year_keyword format)
    def generate_cite_key(paper):
        # Get first author's last name
        author_key = "unknown"
        if paper.authors:
            authors_list = paper.authors.split(";")[0].strip()
            if authors_list:
                # Get last name (assuming "First Last" or "Last, First" format)
                if "," in authors_list:
                    author_key = authors_list.split(",")[0].strip()
                else:
                    parts = authors_list.split()
                    author_key = parts[-1] if parts else "unknown"
                # Clean non-alphanumeric
                author_key = "".join(c for c in author_key if c.isalnum())
        
        # Get year
        year_key = str(paper.year) if paper.year else "nodate"
        
        # Get first significant word from title
        title_key = "paper"
        if paper.title:
            title_words = paper.title.lower().split()
            # Skip common words
            skip_words = {"the", "a", "an", "of", "in", "on", "for", "to", "and", "or", "with"}
            for word in title_words:
                clean_word = "".join(c for c in word if c.isalnum())
                if clean_word and clean_word not in skip_words and len(clean_word) > 3:
                    title_key = clean_word[:10]
                    break
        
        return f"{author_key}{year_key}{title_key}"
    
    cite_key = generate_cite_key(paper)
    
    # Determine BibTeX entry type
    entry_type = paper.publication_type if paper.publication_type else "article"
    
    # Build BibTeX entry
    bibtex_lines = [f"@{entry_type}{{{cite_key},"]
    
    # Add required and optional fields
    def add_field(key, value, required=False):
        if value or required:
            # Escape special LaTeX characters
            if value:
                value_str = str(value).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
                # For title, wrap in double braces to preserve capitalization
                if key == "title":
                    bibtex_lines.append(f"  {key} = {{{{{value_str}}}}},")
                elif key in ["volume", "issue", "year", "month", "chapter"]:
                    # Numeric fields don't need braces
                    bibtex_lines.append(f"  {key} = {value_str},")
                else:
                    bibtex_lines.append(f"  {key} = {{{value_str}}},")
            elif required:
                bibtex_lines.append(f"  {key} = {{}},")
    
    # Add fields in standard BibTeX order
    add_field("title", paper.title, required=True)
    add_field("author", paper.authors.replace(";", " and ") if paper.authors else None, required=True)
    add_field("year", paper.year)
    add_field("month", paper.month)
    
    # Entry-specific fields based on BibTeX standard
    if entry_type == "article":
        add_field("journal", paper.journal, required=True)
        add_field("volume", paper.volume)
        add_field("number", paper.issue)  # BibTeX uses "number" for issue
        add_field("pages", paper.pages)
        add_field("publisher", paper.publisher)
    elif entry_type in ["inproceedings", "conference"]:
        add_field("booktitle", paper.booktitle or paper.journal, required=True)
        add_field("pages", paper.pages)
        add_field("publisher", paper.publisher)
        add_field("series", paper.series)
        add_field("volume", paper.volume)
    elif entry_type == "book":
        add_field("publisher", paper.publisher, required=True)
        add_field("edition", paper.edition)
        add_field("volume", paper.volume)
        add_field("series", paper.series)
        add_field("isbn", paper.isbn)
    elif entry_type == "inbook":
        add_field("chapter", paper.chapter)
        add_field("pages", paper.pages)
        add_field("publisher", paper.publisher, required=True)
        add_field("edition", paper.edition)
        add_field("volume", paper.volume)
        add_field("series", paper.series)
        add_field("isbn", paper.isbn)
    elif entry_type == "incollection":
        add_field("booktitle", paper.booktitle, required=True)
        add_field("chapter", paper.chapter)
        add_field("pages", paper.pages)
        add_field("publisher", paper.publisher, required=True)
        add_field("edition", paper.edition)
        add_field("series", paper.series)
    elif entry_type == "phdthesis":
        add_field("school", paper.institution or paper.publisher, required=True)
        add_field("type", "PhD Thesis")
    elif entry_type == "mastersthesis":
        add_field("school", paper.institution or paper.publisher, required=True)
        add_field("type", "Master's Thesis")
    elif entry_type == "techreport":
        add_field("institution", paper.institution or paper.publisher, required=True)
        add_field("number", paper.report_number or paper.issue)
        add_field("type", "Technical Report")
    elif entry_type == "misc":
        # Misc can have almost any fields
        if paper.journal:
            add_field("howpublished", paper.journal)
        if paper.booktitle:
            add_field("howpublished", paper.booktitle)
        add_field("publisher", paper.publisher)
    
    # Common optional fields
    add_field("doi", paper.doi)
    add_field("url", paper.url)
    add_field("abstract", paper.abstract)
    add_field("keywords", paper.keywords)
    add_field("note", paper.note)
    
    # Close entry
    bibtex_lines[-1] = bibtex_lines[-1].rstrip(",")  # Remove trailing comma from last field
    bibtex_lines.append("}")
    
    bibtex_content = "\n".join(bibtex_lines)
    
    return PlainTextResponse(
        content=bibtex_content,
        media_type="application/x-bibtex",
        headers={
            "Content-Disposition": f'attachment; filename="{cite_key}.bib"'
        }
    )


@router.post("/{paper_id}/organize-pdf")
def organize_paper_pdf(
    paper_id: int,
    db: Session = Depends(get_db)
):
    """
    Manually trigger PDF organization/renaming for a paper.
    Uses the same naming format as automatic organization: {author} - {year} - {title}.pdf
    """
    from ..ai.tasks import organize_pdf_file
    
    # Get the paper
    paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    
    # Check if paper has a file
    if not paper.file_path or not os.path.exists(paper.file_path):
        raise HTTPException(status_code=400, detail="Paper PDF file not found")
    
    # Build metadata dictionary from paper fields
    metadata = {
        "title": paper.title,
        "year": paper.year,
        "authors": []
    }
    
    # Parse authors
    if paper.authors:
        # Simple parsing - split by comma or semicolon
        author_list = [a.strip() for a in paper.authors.replace(';', ',').split(',') if a.strip()]
        for author_name in author_list:
            # Try to split into given/family
            parts = author_name.split()
            if len(parts) >= 2:
                metadata["authors"].append({
                    "given": " ".join(parts[:-1]),
                    "family": parts[-1]
                })
            else:
                metadata["authors"].append({
                    "given": "",
                    "family": author_name
                })
    
    # Attempt to organize the PDF
    new_path = organize_pdf_file(paper_id, paper.file_path, metadata)
    
    if not new_path:
        raise HTTPException(
            status_code=400,
            detail="Failed to organize PDF. Check that the paper has sufficient metadata (title required)."
        )
    
    # Update database if path changed
    if new_path != paper.file_path:
        paper.file_path = new_path
        db.commit()
        db.refresh(paper)
    
    return {
        "success": True,
        "message": "PDF organized successfully",
        "new_path": new_path,
        "filename": os.path.basename(new_path)
    }
