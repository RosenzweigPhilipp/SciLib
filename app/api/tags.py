from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/tags", tags=["tags"])


class Tag(BaseModel):
    id: int
    name: str
    color: Optional[str] = "#007bff"  # Default blue color
    created_at: datetime


class TagCreate(BaseModel):
    name: str
    color: Optional[str] = "#007bff"


class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


# Temporary storage for demo purposes
tags_db = []
next_id = 1


@router.get("/", response_model=List[Tag])
async def list_tags():
    """List all tags"""
    return tags_db


@router.post("/", response_model=Tag, status_code=status.HTTP_201_CREATED)
async def create_tag(tag: TagCreate):
    """Create a new tag"""
    global next_id
    
    # Check if tag already exists
    existing_tag = next((t for t in tags_db if t["name"].lower() == tag.name.lower()), None)
    if existing_tag:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tag with this name already exists"
        )
    
    new_tag = {
        "id": next_id,
        "name": tag.name,
        "color": tag.color,
        "created_at": datetime.now()
    }
    
    tags_db.append(new_tag)
    next_id += 1
    
    return new_tag


@router.get("/{tag_id}", response_model=Tag)
async def get_tag(tag_id: int):
    """Get a specific tag by ID"""
    tag = next((t for t in tags_db if t["id"] == tag_id), None)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    return tag


@router.put("/{tag_id}", response_model=Tag)
async def update_tag(tag_id: int, tag_update: TagUpdate):
    """Update a tag"""
    tag = next((t for t in tags_db if t["id"] == tag_id), None)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found"
        )
    
    update_data = tag_update.dict(exclude_unset=True)
    
    # Check for name conflicts if name is being updated
    if "name" in update_data:
        existing_tag = next(
            (t for t in tags_db 
             if t["name"].lower() == update_data["name"].lower() and t["id"] != tag_id), 
            None
        )
        if existing_tag:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tag with this name already exists"
            )
    
    for field, value in update_data.items():
        tag[field] = value
    
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: int):
    """Delete a tag"""
    global tags_db
    tags_db = [t for t in tags_db if t["id"] != tag_id]
    return