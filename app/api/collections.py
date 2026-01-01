from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from ..database import get_db, Collection as CollectionModel

router = APIRouter(prefix="/collections", tags=["collections"])


# Nested schema for papers in collections
class PaperInCollection(BaseModel):
    id: int
    title: str
    authors: str
    year: Optional[int] = None
    journal: Optional[str] = None
    
    class Config:
        from_attributes = True


class Collection(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_smart: Optional[bool] = False
    created_at: datetime
    updated_at: datetime
    papers: List[PaperInCollection] = []
    
    class Config:
        from_attributes = True


class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


@router.get("/", response_model=List[Collection])
async def list_collections(db: Session = Depends(get_db)):
    """List all collections"""
    collections = db.query(CollectionModel).options(
        joinedload(CollectionModel.papers)
    ).all()
    return collections


@router.post("/", response_model=Collection, status_code=status.HTTP_201_CREATED)
async def create_collection(collection: CollectionCreate, db: Session = Depends(get_db)):
    """Create a new collection"""
    
    # Check if collection name already exists
    existing = db.query(CollectionModel).filter(CollectionModel.name == collection.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection with this name already exists"
        )
    
    new_collection = CollectionModel(
        name=collection.name,
        description=collection.description
    )
    
    db.add(new_collection)
    db.commit()
    db.refresh(new_collection)
    
    return new_collection


@router.get("/{collection_id}", response_model=Collection)
async def get_collection(collection_id: int, db: Session = Depends(get_db)):
    """Get a specific collection by ID"""
    collection = db.query(CollectionModel).options(
        joinedload(CollectionModel.papers)
    ).filter(CollectionModel.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    return collection


@router.put("/{collection_id}", response_model=Collection)
async def update_collection(collection_id: int, collection_update: CollectionUpdate, db: Session = Depends(get_db)):
    """Update a collection"""
    collection = db.query(CollectionModel).filter(CollectionModel.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    # Check for name conflicts if name is being updated
    if collection_update.name and collection_update.name != collection.name:
        existing = db.query(CollectionModel).filter(
            CollectionModel.name == collection_update.name
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Collection with this name already exists"
            )
    
    update_data = collection_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(collection, field, value)
    
    db.commit()
    db.refresh(collection)
    return collection


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    """Delete a collection"""
    collection = db.query(CollectionModel).filter(CollectionModel.id == collection_id).first()
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    db.delete(collection)
    db.commit()
    return