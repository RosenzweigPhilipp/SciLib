"""
Discovery API endpoints for external paper search
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field

from ..database.connection import get_db
from ..auth import verify_api_key
from ..ai.services.discovery_service import DiscoveryService, search_external_papers

router = APIRouter(prefix="/api/discover", tags=["discovery"])


class DiscoverySearchRequest(BaseModel):
    """Request model for discovery search"""
    query: str = Field(..., description="Search query (title, keywords, etc.)")
    sources: Optional[List[str]] = Field(
        default=None,
        description="Sources to search (semantic_scholar, arxiv, crossref, openalex)"
    )
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results per source")
    min_year: Optional[int] = Field(default=None, description="Filter papers after this year")
    max_year: Optional[int] = Field(default=None, description="Filter papers before this year")


class DiscoveredPaperResponse(BaseModel):
    """Response model for a discovered paper"""
    title: str
    authors: Optional[str]
    year: Optional[int]
    abstract: Optional[str]
    doi: Optional[str]
    journal: Optional[str]
    url: Optional[str]
    source: str
    relevance_score: float
    citation_count: Optional[int]
    in_library: bool
    library_paper_id: Optional[int]


class DiscoverySearchResponse(BaseModel):
    """Response model for discovery search"""
    query: str
    total_results: int
    papers: List[DiscoveredPaperResponse]


class AddPaperRequest(BaseModel):
    """Request model for adding discovered paper to library"""
    title: str
    authors: Optional[str] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    journal: Optional[str] = None
    url: Optional[str] = None
    source: str
    citation_count: Optional[int] = None
    collection_ids: Optional[List[int]] = Field(default=None, description="Collections to add paper to")


class AddPaperResponse(BaseModel):
    """Response model for added paper"""
    id: int
    title: str
    authors: Optional[str]
    year: Optional[int]
    doi: Optional[str]
    message: str


@router.post("/search", response_model=DiscoverySearchResponse)
def search_papers(
    request: DiscoverySearchRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Search external scientific databases for papers
    
    Searches multiple sources (Semantic Scholar, arXiv, CrossRef, OpenAlex) and returns
    unified, deduplicated results ranked by relevance.
    
    - **query**: Search query (title, keywords, author, etc.)
    - **sources**: Optional list of sources to search (defaults to all)
    - **limit**: Maximum results per source
    - **min_year**: Filter papers published after this year
    - **max_year**: Filter papers published before this year
    """
    try:
        # Validate sources
        valid_sources = {"semantic_scholar", "arxiv", "crossref", "openalex"}
        if request.sources:
            invalid = set(request.sources) - valid_sources
            if invalid:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid sources: {invalid}. Valid sources: {valid_sources}"
                )
        
        # Search external sources
        results = search_external_papers(
            db=db,
            query=request.query,
            sources=request.sources,
            limit=request.limit,
            min_year=request.min_year,
            max_year=request.max_year
        )
        
        return DiscoverySearchResponse(
            query=request.query,
            total_results=len(results),
            papers=[DiscoveredPaperResponse(**paper) for paper in results]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery search failed: {str(e)}")


@router.get("/search", response_model=DiscoverySearchResponse)
def search_papers_get(
    query: str = Query(..., description="Search query"),
    sources: Optional[str] = Query(None, description="Comma-separated list of sources"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    min_year: Optional[int] = Query(None, description="Minimum publication year"),
    max_year: Optional[int] = Query(None, description="Maximum publication year"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Search external scientific databases (GET version)
    
    Query parameters:
    - **query**: Search query
    - **sources**: Comma-separated sources (semantic_scholar,arxiv,crossref,openalex)
    - **limit**: Maximum results (default: 20)
    - **min_year**: Filter by minimum year
    - **max_year**: Filter by maximum year
    """
    try:
        # Parse sources from comma-separated string
        source_list = None
        if sources:
            source_list = [s.strip() for s in sources.split(",")]
        
        # Use the same logic as POST
        request = DiscoverySearchRequest(
            query=query,
            sources=source_list,
            limit=limit,
            min_year=min_year,
            max_year=max_year
        )
        
        return search_papers(request, db, api_key)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery search failed: {str(e)}")


@router.post("/add", response_model=AddPaperResponse)
def add_discovered_paper(
    request: AddPaperRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Add a discovered paper to the library
    
    - **title**: Paper title (required)
    - **authors**: Author names
    - **year**: Publication year
    - **abstract**: Paper abstract
    - **doi**: Digital Object Identifier
    - **journal**: Journal/venue name
    - **url**: Paper URL
    - **source**: Discovery source
    - **citation_count**: Number of citations
    - **collection_ids**: Optional list of collection IDs to add paper to
    """
    try:
        # Check if paper already exists
        from ..database.models import Paper
        
        if request.doi:
            existing = db.query(Paper).filter(Paper.doi == request.doi).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Paper with DOI {request.doi} already exists in library (ID: {existing.id})"
                )
        
        if request.title:
            existing = db.query(Paper).filter(Paper.title == request.title).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Paper with title '{request.title}' already exists in library (ID: {existing.id})"
                )
        
        # Add paper to library
        service = DiscoveryService(db)
        paper = service.add_to_library(
            discovered_paper=request.dict(),
            collection_ids=request.collection_ids
        )
        
        return AddPaperResponse(
            id=paper.id,
            title=paper.title,
            authors=paper.authors,
            year=paper.year,
            doi=paper.doi,
            message=f"Paper added to library successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add paper: {str(e)}")


@router.get("/sources")
def get_available_sources(api_key: str = Depends(verify_api_key)):
    """
    Get list of available discovery sources
    
    Returns information about each source including rate limits and capabilities.
    """
    return {
        "sources": [
            {
                "id": "semantic_scholar",
                "name": "Semantic Scholar",
                "description": "Academic search engine with citation data",
                "rate_limit": "100 requests per 5 minutes (higher with API key)",
                "features": ["citations", "abstracts", "open_access"]
            },
            {
                "id": "arxiv",
                "name": "arXiv",
                "description": "Preprint repository for physics, math, CS, etc.",
                "rate_limit": "1 request per 3 seconds",
                "features": ["preprints", "abstracts", "free_access"]
            },
            {
                "id": "crossref",
                "name": "CrossRef",
                "description": "DOI registration agency with publication metadata",
                "rate_limit": "50 requests per second (with polite email)",
                "features": ["doi", "citations", "publisher_data"]
            },
            {
                "id": "openalex",
                "name": "OpenAlex",
                "description": "Open catalog of scholarly papers",
                "rate_limit": "No rate limit",
                "features": ["citations", "open_data", "institution_data"]
            }
        ]
    }
