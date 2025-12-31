"""
Citation Analysis API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy import func

from ..database.connection import get_db
from ..auth import verify_api_key
from ..ai.services.citation_service import CitationAnalysisService

router = APIRouter(prefix="/api/citations", tags=["citations"])


class AddCitationRequest(BaseModel):
    """Request to add a citation"""
    citing_paper_id: int = Field(..., description="Paper that cites another paper")
    cited_paper_id: int = Field(..., description="Paper being cited")
    context: Optional[str] = Field(None, description="Optional citation context")


class CitationResponse(BaseModel):
    """Citation response"""
    id: int
    citing_paper_id: int
    cited_paper_id: int
    context: Optional[str]


class PaperCitationsResponse(BaseModel):
    """Citations for a specific paper"""
    paper_id: int
    citation_count: int
    reference_count: int
    citing: List[dict]
    cited: List[dict]


class InfluentialPaperResponse(BaseModel):
    """Influential paper response"""
    id: int
    title: str
    authors: str
    year: Optional[int]
    citation_count: int
    external_citation_count: int
    h_index: int
    influence_score: float


class CitationNetworkResponse(BaseModel):
    """Citation network for visualization"""
    nodes: List[dict]
    edges: List[dict]
    stats: dict


@router.post("/add", response_model=CitationResponse)
def add_citation(
    request: AddCitationRequest,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Add a citation relationship between two papers
    
    - **citing_paper_id**: Paper that cites another paper
    - **cited_paper_id**: Paper being cited
    - **context**: Optional context text around citation
    """
    try:
        service = CitationAnalysisService(db)
        citation = service.add_citation(
            citing_paper_id=request.citing_paper_id,
            cited_paper_id=request.cited_paper_id,
            context=request.context
        )
        
        return CitationResponse(
            id=citation.id,
            citing_paper_id=citation.citing_paper_id,
            cited_paper_id=citation.cited_paper_id,
            context=citation.context
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add citation: {str(e)}")


@router.delete("/{citing_paper_id}/{cited_paper_id}")
def remove_citation(
    citing_paper_id: int,
    cited_paper_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """Remove a citation relationship"""
    service = CitationAnalysisService(db)
    removed = service.remove_citation(citing_paper_id, cited_paper_id)
    
    if not removed:
        raise HTTPException(status_code=404, detail="Citation not found")
    
    return {"message": "Citation removed successfully"}


@router.get("/paper/{paper_id}", response_model=PaperCitationsResponse)
def get_paper_citations(
    paper_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get all citations for a paper
    
    Returns both papers that cite this paper and papers cited by this paper.
    """
    try:
        service = CitationAnalysisService(db)
        citations = service.get_citations_for_paper(paper_id)
        
        return PaperCitationsResponse(
            paper_id=paper_id,
            **citations
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get citations: {str(e)}")


@router.post("/paper/{paper_id}/fetch-external")
def fetch_external_citations(
    paper_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Fetch external citation data from Semantic Scholar
    
    Updates the paper's external_citation_count field.
    """
    try:
        service = CitationAnalysisService(db)
        data = service.fetch_external_citations(paper_id)
        
        return {
            "paper_id": paper_id,
            "external_citations": data["external_citations"],
            "source": data["source"],
            "message": "External citations updated successfully"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch external citations: {str(e)}")


@router.post("/paper/{paper_id}/calculate-influence")
def calculate_influence(
    paper_id: int,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Calculate influence score for a paper
    
    Analyzes citation network and updates:
    - influence_score
    - h_index
    - citations_updated_at
    """
    try:
        service = CitationAnalysisService(db)
        influence = service.calculate_influence_score(paper_id)
        
        return {
            "paper_id": paper_id,
            "influence_score": influence,
            "message": "Influence score calculated successfully"
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate influence: {str(e)}")


@router.post("/recalculate-all")
def recalculate_all_metrics(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Recalculate citation metrics for all papers
    
    This is a heavy operation that updates influence scores and h-index
    for all papers in the library.
    """
    service = CitationAnalysisService(db)
    result = service.recalculate_all_metrics()
    
    return {
        "total_papers": result["total"],
        "updated": result["updated"],
        "message": f"Recalculated metrics for {result['updated']} papers"
    }


@router.get("/influential", response_model=List[InfluentialPaperResponse])
def get_influential_papers(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of papers"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get most influential papers by influence score
    
    Returns papers ranked by calculated influence metric which considers:
    - Direct citations
    - Citation velocity (citations per year)
    - H-index
    - Network centrality
    """
    service = CitationAnalysisService(db)
    papers = service.get_most_influential_papers(limit)
    
    return [InfluentialPaperResponse(**p) for p in papers]


@router.get("/most-cited", response_model=List[dict])
def get_most_cited_papers(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of papers"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get most cited papers in library
    
    Returns papers ranked by citation count within the library.
    """
    service = CitationAnalysisService(db)
    papers = service.get_most_cited_papers(limit)
    
    return papers


@router.get("/network", response_model=CitationNetworkResponse)
def get_citation_network(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get complete citation network for visualization
    
    Returns:
    - **nodes**: Papers with citation metadata
    - **edges**: Citation relationships (source -> target)
    - **stats**: Network statistics
    """
    service = CitationAnalysisService(db)
    network = service.get_citation_network()
    
    return CitationNetworkResponse(**network)


@router.get("/clusters")
def get_citation_clusters(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Detect clusters/communities in citation network
    
    Uses connected components algorithm to find groups of related papers.
    """
    service = CitationAnalysisService(db)
    clusters = service.detect_citation_clusters()
    
    return {
        "total_clusters": len(clusters),
        "clusters": clusters
    }


@router.get("/stats")
def get_citation_stats(
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """
    Get overall citation statistics for the library
    """
    from ..database.models import Paper, Citation
    
    total_papers = db.query(Paper).count()
    total_citations = db.query(Citation).count()
    
    # Papers with citations
    papers_with_citations = db.query(Paper).filter(Paper.citation_count > 0).count()
    
    # Average citations
    avg_citations = db.query(func.avg(Paper.citation_count)).scalar() or 0
    
    # Most cited paper
    most_cited = db.query(Paper).order_by(Paper.citation_count.desc()).first()
    
    # Most influential paper
    most_influential = db.query(Paper).order_by(Paper.influence_score.desc()).first()
    
    return {
        "total_papers": total_papers,
        "total_citations": total_citations,
        "papers_with_citations": papers_with_citations,
        "avg_citations_per_paper": round(avg_citations, 2),
        "most_cited_paper": {
            "id": most_cited.id,
            "title": most_cited.title,
            "citation_count": most_cited.citation_count
        } if most_cited else None,
        "most_influential_paper": {
            "id": most_influential.id,
            "title": most_influential.title,
            "influence_score": most_influential.influence_score
        } if most_influential else None
    }
