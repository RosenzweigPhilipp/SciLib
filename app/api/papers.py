from fastapi import APIRouter, HTTPException, UploadFile, File, Query, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

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


# Temporary storage for demo purposes
papers_db = []
next_id = 1


@router.post("/upload", response_model=Paper, status_code=status.HTTP_201_CREATED)
async def upload_paper(file: UploadFile = File(...)):
    """Upload a new paper PDF"""
    global next_id
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # For now, just create a mock paper entry
    # TODO: Implement actual file saving and metadata extraction
    paper = {
        "id": next_id,
        "title": f"Uploaded Paper: {file.filename}",
        "authors": "Unknown Authors",
        "abstract": None,
        "keywords": None,
        "year": None,
        "journal": None,
        "doi": None,
        "file_path": f"uploads/{file.filename}",
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    papers_db.append(paper)
    next_id += 1
    
    return paper


@router.get("/", response_model=List[Paper])
async def list_papers(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None)
):
    """List papers with pagination and optional search"""
    filtered_papers = papers_db
    
    if search:
        filtered_papers = [
            paper for paper in papers_db 
            if search.lower() in paper["title"].lower() or 
               search.lower() in paper["authors"].lower()
        ]
    
    return filtered_papers[skip:skip + limit]


@router.get("/{paper_id}", response_model=Paper)
async def get_paper(paper_id: int):
    """Get a specific paper by ID"""
    paper = next((p for p in papers_db if p["id"] == paper_id), None)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    return paper


@router.put("/{paper_id}", response_model=Paper)
async def update_paper(paper_id: int, paper_update: PaperUpdate):
    """Update paper metadata"""
    paper = next((p for p in papers_db if p["id"] == paper_id), None)
    if not paper:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paper not found"
        )
    
    update_data = paper_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        paper[field] = value
    
    paper["updated_at"] = datetime.now()
    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(paper_id: int):
    """Delete a paper"""
    global papers_db
    papers_db = [p for p in papers_db if p["id"] != paper_id]
    return