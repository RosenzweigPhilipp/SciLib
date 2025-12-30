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
    
    # AI Extraction fields
    extraction_status: Optional[str] = None
    extraction_confidence: Optional[float] = None
    extraction_sources: Optional[Any] = None  # Can be JSON string or parsed object
    extraction_metadata: Optional[Any] = None  # Can be JSON string or parsed object
    extracted_at: Optional[datetime] = None
    
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


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    authors: Optional[str] = None
    abstract: Optional[str] = None
    keywords: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    doi: Optional[str] = None


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
                paper_id=paper.id,
                user_id=1  # Default user ID for now
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


@router.get("/", response_model=List[Paper])
async def list_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List papers with pagination and optional search"""
    query = db.query(PaperModel)
    
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
    paper = db.query(PaperModel).filter(PaperModel.id == paper_id).first()
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
        papers = db.query(PaperModel).all()
        # Delete files from disk
        for p in papers:
            try:
                if p.file_path and os.path.exists(p.file_path):
                    os.remove(p.file_path)
            except Exception:
                # ignore file removal errors
                pass

        # Delete all rows
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
                args=[paper.file_path, paper.id, 1],
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