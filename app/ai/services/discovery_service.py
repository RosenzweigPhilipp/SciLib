"""
Discovery Service - Search external scientific databases

Aggregates results from multiple sources (Semantic Scholar, arXiv, CrossRef, OpenAlex)
and provides unified discovery functionality.
"""
import logging
from typing import Dict, List, Optional, Set
from sqlalchemy.orm import Session
from datetime import datetime

from ..tools.scientific_apis import (
    SemanticScholarTool,
    ArxivTool,
    CrossRefTool,
    OpenAlexTool
)
from ...database.models import Paper
from ...config import settings

logger = logging.getLogger(__name__)


class DiscoveredPaper:
    """Represents a paper discovered from external sources"""
    
    def __init__(
        self,
        title: str,
        authors: Optional[str] = None,
        year: Optional[int] = None,
        abstract: Optional[str] = None,
        doi: Optional[str] = None,
        journal: Optional[str] = None,
        url: Optional[str] = None,
        source: str = "unknown",
        relevance_score: float = 0.0,
        citation_count: Optional[int] = None,
        in_library: bool = False,
        library_paper_id: Optional[int] = None
    ):
        self.title = title
        self.authors = authors
        self.year = year
        self.abstract = abstract
        self.doi = doi
        self.journal = journal
        self.url = url
        self.source = source
        self.relevance_score = relevance_score
        self.citation_count = citation_count
        self.in_library = in_library
        self.library_paper_id = library_paper_id
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "doi": self.doi,
            "journal": self.journal,
            "url": self.url,
            "source": self.source,
            "relevance_score": self.relevance_score,
            "citation_count": self.citation_count,
            "in_library": self.in_library,
            "library_paper_id": self.library_paper_id
        }


class DiscoveryService:
    """Service for discovering papers from external sources"""
    
    def __init__(self, db: Session):
        self.db = db
        self.semantic_scholar = SemanticScholarTool()
        self.arxiv = ArxivTool()
        self.crossref = CrossRefTool(email=settings.crossref_email)
        self.openalex = OpenAlexTool()
    
    def search(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        limit: int = 20,
        min_year: Optional[int] = None,
        max_year: Optional[int] = None
    ) -> List[DiscoveredPaper]:
        """
        Search external sources for papers
        
        Args:
            query: Search query (title, keywords, etc.)
            sources: List of sources to search (default: all)
            limit: Maximum results per source
            min_year: Filter papers after this year
            max_year: Filter papers before this year
        
        Returns:
            List of DiscoveredPaper objects, ranked by relevance
        """
        if sources is None:
            sources = ["semantic_scholar", "arxiv", "crossref", "openalex"]
        
        results = []
        
        # Search each source
        if "semantic_scholar" in sources:
            results.extend(self._search_semantic_scholar(query, limit))
        
        if "arxiv" in sources:
            results.extend(self._search_arxiv(query, limit))
        
        if "crossref" in sources:
            results.extend(self._search_crossref(query, limit))
        
        if "openalex" in sources:
            results.extend(self._search_openalex(query, limit))
        
        # Filter by year if specified
        if min_year or max_year:
            results = [
                r for r in results
                if (min_year is None or (r.year and r.year >= min_year)) and
                   (max_year is None or (r.year and r.year <= max_year))
            ]
        
        # Deduplicate by DOI and title
        results = self._deduplicate_results(results)
        
        # Check which papers are already in library
        results = self._check_library_status(results)
        
        # Sort by relevance and citation count
        results = self._rank_results(results)
        
        # Limit total results
        return results[:limit * 2]  # Return 2x limit since we combine sources
    
    def _search_semantic_scholar(self, query: str, limit: int) -> List[DiscoveredPaper]:
        """Search Semantic Scholar"""
        try:
            logger.info(f"Searching Semantic Scholar: {query}")
            results = self.semantic_scholar.search_by_title(query, limit=limit)
            
            papers = []
            for idx, result in enumerate(results):
                # Extract DOI
                doi = None
                if "externalIds" in result and result["externalIds"]:
                    doi = result["externalIds"].get("DOI")
                
                # Extract authors
                authors = None
                if "authors" in result and result["authors"]:
                    author_names = [a.get("name", "") for a in result["authors"]]
                    authors = "; ".join(author_names)
                
                # Extract journal/venue
                journal = result.get("venue") or result.get("journal", {}).get("name")
                
                # Calculate relevance score (position-based + citation count)
                position_score = 1.0 - (idx / max(limit, 1))
                citation_score = min(result.get("citationCount", 0) / 1000.0, 1.0)
                relevance = 0.7 * position_score + 0.3 * citation_score
                
                # Get URL
                url = result.get("url") or (result.get("openAccessPdf", {}) or {}).get("url")
                
                paper = DiscoveredPaper(
                    title=result.get("title", ""),
                    authors=authors,
                    year=result.get("year"),
                    abstract=result.get("abstract"),
                    doi=doi,
                    journal=journal,
                    url=url,
                    source="Semantic Scholar",
                    relevance_score=relevance,
                    citation_count=result.get("citationCount")
                )
                papers.append(paper)
            
            logger.info(f"Found {len(papers)} papers from Semantic Scholar")
            return papers
            
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []
    
    def _search_arxiv(self, query: str, limit: int) -> List[DiscoveredPaper]:
        """Search arXiv"""
        try:
            logger.info(f"Searching arXiv: {query}")
            results = self.arxiv.search_by_title(query, limit=limit)
            
            papers = []
            for idx, result in enumerate(results):
                # Position-based relevance
                relevance = 1.0 - (idx / max(limit, 1))
                
                paper = DiscoveredPaper(
                    title=result.get("title", ""),
                    authors=result.get("authors"),
                    year=result.get("year"),
                    abstract=result.get("abstract"),
                    doi=None,  # arXiv doesn't have DOIs in this format
                    journal=result.get("journal", "arXiv preprint"),
                    url=result.get("url"),
                    source="arXiv",
                    relevance_score=relevance * 0.8,  # Slightly lower than Semantic Scholar
                    citation_count=None
                )
                papers.append(paper)
            
            logger.info(f"Found {len(papers)} papers from arXiv")
            return papers
            
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
            return []
    
    def _search_crossref(self, query: str, limit: int) -> List[DiscoveredPaper]:
        """Search CrossRef"""
        try:
            logger.info(f"Searching CrossRef: {query}")
            results = self.crossref.search_by_title(query, limit=limit)
            
            papers = []
            for idx, result in enumerate(results):
                # Extract title
                title = result.get("title", [""])[0] if "title" in result else ""
                
                # Extract authors
                authors = None
                if "author" in result:
                    author_names = []
                    for author in result["author"]:
                        given = author.get("given", "")
                        family = author.get("family", "")
                        if family:
                            author_names.append(f"{given} {family}".strip())
                    authors = "; ".join(author_names)
                
                # Extract year
                year = None
                if "published" in result:
                    date_parts = result["published"].get("date-parts", [[]])[0]
                    if date_parts:
                        year = date_parts[0]
                
                # Extract journal
                journal = result.get("container-title", [""])[0] if "container-title" in result else None
                
                # Position-based relevance
                relevance = 1.0 - (idx / max(limit, 1))
                
                paper = DiscoveredPaper(
                    title=title,
                    authors=authors,
                    year=year,
                    abstract=result.get("abstract"),
                    doi=result.get("DOI"),
                    journal=journal,
                    url=f"https://doi.org/{result['DOI']}" if "DOI" in result else None,
                    source="CrossRef",
                    relevance_score=relevance * 0.85,
                    citation_count=result.get("is-referenced-by-count")
                )
                papers.append(paper)
            
            logger.info(f"Found {len(papers)} papers from CrossRef")
            return papers
            
        except Exception as e:
            logger.error(f"CrossRef search failed: {e}")
            return []
    
    def _search_openalex(self, query: str, limit: int) -> List[DiscoveredPaper]:
        """Search OpenAlex"""
        try:
            logger.info(f"Searching OpenAlex: {query}")
            results = self.openalex.search_by_title(query, limit=limit)
            
            papers = []
            for idx, result in enumerate(results):
                # Extract authors
                authors = None
                if "authorships" in result and result["authorships"]:
                    author_names = [
                        a.get("author", {}).get("display_name", "")
                        for a in result["authorships"]
                    ]
                    authors = "; ".join([n for n in author_names if n])
                
                # Position-based relevance
                relevance = 1.0 - (idx / max(limit, 1))
                
                paper = DiscoveredPaper(
                    title=result.get("title", ""),
                    authors=authors,
                    year=result.get("publication_year"),
                    abstract=None,  # OpenAlex doesn't provide abstracts in search
                    doi=result.get("doi", "").replace("https://doi.org/", ""),
                    journal=result.get("host_venue", {}).get("display_name"),
                    url=result.get("doi"),
                    source="OpenAlex",
                    relevance_score=relevance * 0.75,
                    citation_count=result.get("cited_by_count")
                )
                papers.append(paper)
            
            logger.info(f"Found {len(papers)} papers from OpenAlex")
            return papers
            
        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")
            return []
    
    def _deduplicate_results(self, results: List[DiscoveredPaper]) -> List[DiscoveredPaper]:
        """Remove duplicate papers based on DOI and title similarity"""
        seen_dois: Set[str] = set()
        seen_titles: Set[str] = set()
        unique_results = []
        
        for paper in results:
            # Check DOI first (most reliable)
            if paper.doi:
                doi_normalized = paper.doi.lower().strip()
                if doi_normalized in seen_dois:
                    continue
                seen_dois.add(doi_normalized)
            
            # Check title (normalize for comparison)
            if paper.title:
                title_normalized = paper.title.lower().strip()
                # Simple duplicate detection (exact match)
                if title_normalized in seen_titles:
                    continue
                seen_titles.add(title_normalized)
            
            unique_results.append(paper)
        
        logger.info(f"Deduplicated {len(results)} -> {len(unique_results)} papers")
        return unique_results
    
    def _check_library_status(self, results: List[DiscoveredPaper]) -> List[DiscoveredPaper]:
        """Check which papers are already in the library"""
        for paper in results:
            # Check by DOI first
            if paper.doi:
                existing = self.db.query(Paper).filter(
                    Paper.doi == paper.doi
                ).first()
                if existing:
                    paper.in_library = True
                    paper.library_paper_id = existing.id
                    continue
            
            # Check by title (exact match)
            if paper.title:
                existing = self.db.query(Paper).filter(
                    Paper.title == paper.title
                ).first()
                if existing:
                    paper.in_library = True
                    paper.library_paper_id = existing.id
        
        return results
    
    def _rank_results(self, results: List[DiscoveredPaper]) -> List[DiscoveredPaper]:
        """Rank results by relevance and citation count"""
        # Sort by relevance score (descending), then citation count
        def sort_key(paper: DiscoveredPaper):
            citation_score = (paper.citation_count or 0) / 1000.0  # Normalize
            return (
                paper.relevance_score * 0.7 + min(citation_score, 1.0) * 0.3,
                paper.citation_count or 0
            )
        
        results.sort(key=sort_key, reverse=True)
        return results
    
    def add_to_library(
        self,
        discovered_paper: Dict,
        collection_ids: Optional[List[int]] = None
    ) -> Paper:
        """
        Add a discovered paper to the library
        
        Args:
            discovered_paper: Paper data from discovery search
            collection_ids: Optional list of collection IDs to add paper to
        
        Returns:
            Created Paper object
        """
        # Create paper in database
        paper = Paper(
            title=discovered_paper.get("title"),
            authors=discovered_paper.get("authors"),
            abstract=discovered_paper.get("abstract"),
            year=discovered_paper.get("year"),
            doi=discovered_paper.get("doi"),
            journal=discovered_paper.get("journal"),
            file_path=None,  # No file for discovered papers
            extraction_status="completed",  # Mark as completed since we have metadata
            extraction_confidence=0.9,  # High confidence from external source
            extraction_sources={"external": discovered_paper.get("source")},
            extraction_metadata={
                "source": discovered_paper.get("source"),
                "url": discovered_paper.get("url"),
                "citation_count": discovered_paper.get("citation_count"),
                "discovered_at": datetime.utcnow().isoformat()
            }
        )
        
        self.db.add(paper)
        self.db.commit()
        self.db.refresh(paper)
        
        # Add to collections if specified
        if collection_ids:
            from ...database.models import Collection
            for collection_id in collection_ids:
                collection = self.db.query(Collection).filter(
                    Collection.id == collection_id
                ).first()
                if collection:
                    paper.collections.append(collection)
            self.db.commit()
        
        logger.info(f"Added discovered paper to library: {paper.title} (ID: {paper.id})")
        return paper


def search_external_papers(
    db: Session,
    query: str,
    sources: Optional[List[str]] = None,
    limit: int = 20,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None
) -> List[Dict]:
    """
    Convenience function to search external sources
    
    Args:
        db: Database session
        query: Search query
        sources: List of sources (default: all)
        limit: Max results per source
        min_year: Filter by minimum year
        max_year: Filter by maximum year
    
    Returns:
        List of paper dictionaries
    """
    service = DiscoveryService(db)
    results = service.search(query, sources, limit, min_year, max_year)
    return [r.to_dict() for r in results]
