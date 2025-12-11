from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from ..database import get_db, Tag as TagModel

router = APIRouter(prefix="/tags", tags=["tags"])


class Tag(BaseModel):
    id: int
    name: str
    color: Optional[str] = "#007bff"  # Default blue color
    created_at: datetime
    
    class Config:
        from_attributes = True


class TagCreate(BaseModel):
    name: str
    color: Optional[str] = "#007bff"


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


@router.get("/", response_model=List[Tag])
async def list_tags(db: Session = Depends(get_db)):
    """List all tags"""
    return db.query(TagModel).all()


@router.post("/", response_model=Tag, status_code=status.HTTP_201_CREATED)
async def create_tag(tag: TagCreate, db: Session = Depends(get_db)):
    """Create a new tag"""
    
    # Check if tag already exists
    existing_tag = db.query(TagModel).filter(TagModel.name.ilike(tag.name)).first()
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists"
        )
    
    new_tag = TagModel(
        name=tag.name,
        color=tag.color
    )
    
    db.add(new_tag)
    db.commit()
    db.refresh(new_tag)
    
    return new_tag


@router.get("/{tag_id}", response_model=Tag)
async def get_tag(tag_id: int, db: Session = Depends(get_db)):
    """Get a specific tag by ID"""
    tag = db.query(TagModel).filter(TagModel.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    return tag


@router.put("/{tag_id}", response_model=Tag)
async def update_tag(tag_id: int, tag_update: TagUpdate, db: Session = Depends(get_db)):
    """Update a tag"""
    tag = db.query(TagModel).filter(TagModel.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    # Check for name conflicts if name is being updated
    if tag_update.name and tag_update.name.lower() != tag.name.lower():
        existing_tag = db.query(TagModel).filter(TagModel.name.ilike(tag_update.name)).first()
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag with this name already exists"
            )
    
    update_data = tag_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tag, field, value)
    
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    """Delete a tag"""
    tag = db.query(TagModel).filter(TagModel.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    db.delete(tag)
    db.commit()
    return