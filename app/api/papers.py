from fastapi import APIRouter, HTTPException, UploadFile, File, Query, status, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import os
import shutil
from ..database import get_db, Paper as PaperModel
from ..config import settings

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


@router.post("/upload", response_model=Paper, status_code=status.HTTP_201_CREATED)
async def upload_paper(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a new paper PDF"""
    
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
    # For now, just use filename as title - TODO: implement PDF metadata extraction
    paper = PaperModel(
        title=file.filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ').title(),
        authors="Unknown Authors",
        file_path=file_path
    )
    
    db.add(paper)
    db.commit()
    db.refresh(paper)
    
    return paper


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