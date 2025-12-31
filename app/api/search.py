"""
Search API endpoints for SciLib

Provides semantic, keyword, and hybrid search over papers.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.auth import verify_api_key
from app.ai.services.vector_search_service import search_papers

router = APIRouter(prefix="/api/search", tags=["search"])


# Request/Response Models
class SearchRequest(BaseModel):
    """Request body for search endpoints"""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results")
    mode: str = Field("hybrid", description="Search mode: semantic, keyword, or hybrid")
    
    # Filters
    collection_ids: Optional[List[int]] = Field(None, description="Filter by collection IDs")
    tag_ids: Optional[List[int]] = Field(None, description="Filter by tag IDs")
    year_from: Optional[int] = Field(None, ge=1000, le=9999, description="Filter papers from year")
    year_to: Optional[int] = Field(None, ge=1000, le=9999, description="Filter papers to year")
    
    # Hybrid search weights
    semantic_weight: float = Field(0.7, ge=0.0, le=1.0, description="Weight for semantic score")
    keyword_weight: float = Field(0.3, ge=0.0, le=1.0, description="Weight for keyword score")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Minimum similarity score")


class SearchResultResponse(BaseModel):
    """Single search result"""
    paper_id: int
    title: str
    authors: str
    abstract: Optional[str]
    year: Optional[int]
    journal: Optional[str]
    doi: Optional[str]
    score: float
    match_type: str
    has_summary: bool
    has_embedding: bool


class SearchResponse(BaseModel):
    """Response containing search results"""
    query: str
    mode: str
    total_results: int
    results: List[SearchResultResponse]


# Endpoints
@router.post("/", response_model=SearchResponse, dependencies=[Depends(verify_api_key)])
async def search(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search papers using semantic, keyword, or hybrid search.
    
    **Modes:**
    - `semantic`: Vector similarity search (requires embeddings)
    - `keyword`: Traditional full-text search on title/abstract/authors
    - `hybrid`: Combines both methods with configurable weights
    
    **Filters:**
    - `collection_ids`: Only return papers in these collections
    - `tag_ids`: Only return papers with these tags
    - `year_from`, `year_to`: Filter by publication year range
    
    **Example:**
    ```json
    {
        "query": "machine learning in genomics",
        "mode": "hybrid",
        "limit": 20,
        "semantic_weight": 0.7,
        "keyword_weight": 0.3,
        "year_from": 2020
    }
    ```
    """
    # Validate mode
    if request.mode not in ["semantic", "keyword", "hybrid"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid mode. Must be 'semantic', 'keyword', or 'hybrid'"
        )
    
    # Validate weights sum
    if request.mode == "hybrid":
        weight_sum = request.semantic_weight + request.keyword_weight
        if abs(weight_sum - 1.0) > 0.01:  # Allow small floating point error
            raise HTTPException(
                status_code=400,
                detail=f"Weights must sum to 1.0 (got {weight_sum})"
            )
    
    # Validate year range
    if request.year_from and request.year_to and request.year_from > request.year_to:
        raise HTTPException(
            status_code=400,
            detail="year_from must be less than or equal to year_to"
        )
    
    # Build filters dict
    filters = {}
    if request.collection_ids:
        filters["collection_ids"] = request.collection_ids
    if request.tag_ids:
        filters["tag_ids"] = request.tag_ids
    if request.year_from:
        filters["year_from"] = request.year_from
    if request.year_to:
        filters["year_to"] = request.year_to
    if request.min_score:
        filters["min_score"] = request.min_score
    
    # Add hybrid weights if applicable
    if request.mode == "hybrid":
        filters["semantic_weight"] = request.semantic_weight
        filters["keyword_weight"] = request.keyword_weight
    
    # Perform search
    try:
        results = await search_papers(
            db=db,
            query=request.query,
            mode=request.mode,
            limit=request.limit,
            **filters
        )
        
        return SearchResponse(
            query=request.query,
            mode=request.mode,
            total_results=len(results),
            results=[SearchResultResponse(**r) for r in results]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/semantic", response_model=SearchResponse, dependencies=[Depends(verify_api_key)])
async def semantic_search(
    query: str = Query(..., min_length=1, max_length=1000),
    limit: int = Query(10, ge=1, le=100),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs"),
    tag_ids: Optional[str] = Query(None, description="Comma-separated tag IDs"),
    year_from: Optional[int] = Query(None, ge=1000, le=9999),
    year_to: Optional[int] = Query(None, ge=1000, le=9999),
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    db: Session = Depends(get_db)
):
    """
    Quick semantic search endpoint (GET request).
    
    Use this for simple semantic searches. For more control, use POST /api/search
    """
    # Parse comma-separated IDs
    filters = {}
    if collection_ids:
        filters["collection_ids"] = [int(x.strip()) for x in collection_ids.split(",")]
    if tag_ids:
        filters["tag_ids"] = [int(x.strip()) for x in tag_ids.split(",")]
    if year_from:
        filters["year_from"] = year_from
    if year_to:
        filters["year_to"] = year_to
    if min_score:
        filters["min_score"] = min_score
    
    try:
        results = await search_papers(
            db=db,
            query=query,
            mode="semantic",
            limit=limit,
            **filters
        )
        
        return SearchResponse(
            query=query,
            mode="semantic",
            total_results=len(results),
            results=[SearchResultResponse(**r) for r in results]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Semantic search failed: {str(e)}"
        )


@router.get("/keyword", response_model=SearchResponse, dependencies=[Depends(verify_api_key)])
async def keyword_search(
    query: str = Query(..., min_length=1, max_length=1000),
    limit: int = Query(10, ge=1, le=100),
    collection_ids: Optional[str] = Query(None, description="Comma-separated collection IDs"),
    tag_ids: Optional[str] = Query(None, description="Comma-separated tag IDs"),
    year_from: Optional[int] = Query(None, ge=1000, le=9999),
    year_to: Optional[int] = Query(None, ge=1000, le=9999),
    db: Session = Depends(get_db)
):
    """
    Quick keyword search endpoint (GET request).
    
    Searches title, abstract, authors, and keywords fields.
    """
    # Parse comma-separated IDs
    filters = {}
    if collection_ids:
        filters["collection_ids"] = [int(x.strip()) for x in collection_ids.split(",")]
    if tag_ids:
        filters["tag_ids"] = [int(x.strip()) for x in tag_ids.split(",")]
    if year_from:
        filters["year_from"] = year_from
    if year_to:
        filters["year_to"] = year_to
    
    try:
        results = await search_papers(
            db=db,
            query=query,
            mode="keyword",
            limit=limit,
            **filters
        )
        
        return SearchResponse(
            query=query,
            mode="keyword",
            total_results=len(results),
            results=[SearchResultResponse(**r) for r in results]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Keyword search failed: {str(e)}"
        )
