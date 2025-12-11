from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/collections", tags=["collections"])


class Collection(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


# Temporary storage for demo purposes
collections_db = []
next_id = 1


@router.get("/", response_model=List[Collection])
async def list_collections():
    """List all collections"""
    return collections_db


@router.post("/", response_model=Collection, status_code=status.HTTP_201_CREATED)
async def create_collection(collection: CollectionCreate):
    """Create a new collection"""
    global next_id
    
    new_collection = {
        "id": next_id,
        "name": collection.name,
        "description": collection.description,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    
    collections_db.append(new_collection)
    next_id += 1
    
    return new_collection


@router.get("/{collection_id}", response_model=Collection)
async def get_collection(collection_id: int):
    """Get a specific collection by ID"""
    collection = next((c for c in collections_db if c["id"] == collection_id), None)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    return collection


@router.put("/{collection_id}", response_model=Collection)
async def update_collection(collection_id: int, collection_update: CollectionUpdate):
    """Update a collection"""
    collection = next((c for c in collections_db if c["id"] == collection_id), None)
    if not collection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection not found"
        )
    
    update_data = collection_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        collection[field] = value
    
    collection["updated_at"] = datetime.now()
    return collection


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(collection_id: int):
    """Delete a collection"""
    global collections_db
    collections_db = [c for c in collections_db if c["id"] != collection_id]
    return