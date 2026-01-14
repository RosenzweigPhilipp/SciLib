"""
Vector Search Service for SciLib

Implements semantic search over papers using vector embeddings.
Supports pure semantic search, keyword search, and hybrid search.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import text, or_, and_
from sqlalchemy.orm import Session

from app.database.models import Paper, Collection
from app.ai.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class SearchResult:
    """Container for search results with metadata"""
    
    def __init__(self, paper: Paper, score: float, match_type: str = "semantic"):
        self.paper = paper
        self.score = score  # 0.0 to 1.0 (higher is better)
        self.match_type = match_type  # "semantic", "keyword", "hybrid"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "paper_id": self.paper.id,
            "title": self.paper.title,
            "authors": self.paper.authors,
            "abstract": self.paper.abstract,
            "year": self.paper.year,
            "journal": self.paper.journal,
            "doi": self.paper.doi,
            "score": round(self.score, 4),
            "match_type": self.match_type,
            "has_summary": self.paper.ai_summary_short is not None,
            "has_embedding": self.paper.embedding_title_abstract is not None
        }


class VectorSearchService:
    """Service for semantic and hybrid search over papers"""
    
    @staticmethod
    async def semantic_search(
        db: Session,
        query: str,
        limit: int = 10,
        min_score: float = 0.0,
        collection_ids: Optional[List[int]] = None,
        tag_ids: Optional[List[int]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Perform semantic search using vector similarity.
        
        Args:
            db: Database session
            query: Search query text
            limit: Maximum number of results
            min_score: Minimum similarity score (0.0 to 1.0)
            collection_ids: Filter by collection IDs
            tag_ids: Filter by tag IDs
            year_from: Filter papers from this year onwards
            year_to: Filter papers up to this year
            
        Returns:
            List of SearchResult objects ordered by relevance
        """
        if not query or not query.strip():
            logger.warning("Empty query provided for semantic search")
            return []
        
        # Generate embedding for query
        query_embedding = await EmbeddingService.generate_embedding(query)
        
        if query_embedding is None:
            logger.error("Failed to generate embedding for query")
            return []
        
        # Build SQL query with filters
        sql = """
            SELECT 
                p.id,
                1 - (p.embedding_title_abstract <=> CAST(:query_embedding AS vector)) AS similarity
            FROM papers p
            WHERE p.embedding_title_abstract IS NOT NULL
        """
        
        params = {"query_embedding": str(query_embedding)}
        
        # Add collection filter
        if collection_ids:
            sql += """
                AND EXISTS (
                    SELECT 1 FROM paper_collections pc 
                    WHERE pc.paper_id = p.id 
                    AND pc.collection_id = ANY(:collection_ids)
                )
            """
            params["collection_ids"] = collection_ids
        
        # Tag filter removed (tags feature disabled)
        
        # Add year filters
        if year_from:
            sql += " AND p.year >= :year_from"
            params["year_from"] = year_from
        
        if year_to:
            sql += " AND p.year <= :year_to"
            params["year_to"] = year_to
        
        # Add minimum score filter
        sql += " AND (1 - (p.embedding_title_abstract <=> CAST(:query_embedding AS vector))) >= :min_score"
        params["min_score"] = min_score
        
        # Order and limit
        sql += """
            ORDER BY p.embedding_title_abstract <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """
        params["limit"] = limit
        
        # Execute query
        try:
            result = db.execute(text(sql), params)
            rows = result.fetchall()
            
            # Fetch full paper objects and create SearchResults
            results = []
            for paper_id, similarity in rows:
                paper = db.query(Paper).filter(Paper.id == paper_id).first()
                if paper:
                    results.append(SearchResult(
                        paper=paper,
                        score=float(similarity),
                        match_type="semantic"
                    ))
            
            logger.info(f"Semantic search for '{query[:50]}...' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}", exc_info=True)
            return []
    
    @staticmethod
    def keyword_search(
        db: Session,
        query: str,
        limit: int = 10,
        collection_ids: Optional[List[int]] = None,
        tag_ids: Optional[List[int]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Perform traditional keyword search on title, abstract, authors.
        
        Uses PostgreSQL full-text search with ranking.
        """
        if not query or not query.strip():
            logger.warning("Empty query provided for keyword search")
            return []
        
        # Build base query
        q = db.query(Paper)
        
        # Full-text search on title, abstract, authors
        search_filter = or_(
            Paper.title.ilike(f"%{query}%"),
            Paper.abstract.ilike(f"%{query}%"),
            Paper.authors.ilike(f"%{query}%"),
            Paper.keywords.ilike(f"%{query}%")
        )
        q = q.filter(search_filter)
        
        # Apply filters
        if collection_ids:
            q = q.join(Paper.collections).filter(Collection.id.in_(collection_ids))
        
        # Tag filter removed (tags feature disabled)
        
        if year_from:
            q = q.filter(Paper.year >= year_from)
        
        if year_to:
            q = q.filter(Paper.year <= year_to)
        
        # Execute and create results
        papers = q.limit(limit).all()
        
        # Simple scoring based on where match was found (title > abstract > authors)
        results = []
        for paper in papers:
            score = 0.0
            if query.lower() in paper.title.lower():
                score = 0.9
            elif paper.abstract and query.lower() in paper.abstract.lower():
                score = 0.7
            elif query.lower() in paper.authors.lower():
                score = 0.5
            else:
                score = 0.3
            
            results.append(SearchResult(
                paper=paper,
                score=score,
                match_type="keyword"
            ))
        
        # Sort by score
        results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Keyword search for '{query[:50]}...' returned {len(results)} results")
        return results
    
    @staticmethod
    async def hybrid_search(
        db: Session,
        query: str,
        limit: int = 10,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        collection_ids: Optional[List[int]] = None,
        tag_ids: Optional[List[int]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining semantic and keyword search.
        
        Args:
            semantic_weight: Weight for semantic score (0.0 to 1.0)
            keyword_weight: Weight for keyword score (0.0 to 1.0)
            
        Returns:
            Combined results with weighted scores
        """
        # Perform both searches
        semantic_results = await VectorSearchService.semantic_search(
            db, query, limit=limit*2,  # Get more to merge
            collection_ids=collection_ids,
            tag_ids=tag_ids,
            year_from=year_from,
            year_to=year_to
        )
        
        keyword_results = VectorSearchService.keyword_search(
            db, query, limit=limit*2,  # Get more to merge
            collection_ids=collection_ids,
            tag_ids=tag_ids,
            year_from=year_from,
            year_to=year_to
        )
        
        # Merge results
        paper_scores: Dict[int, Tuple[float, Paper]] = {}
        
        # Add semantic scores
        for result in semantic_results:
            paper_id = result.paper.id
            score = result.score * semantic_weight
            paper_scores[paper_id] = (score, result.paper)
        
        # Add/combine keyword scores
        for result in keyword_results:
            paper_id = result.paper.id
            keyword_score = result.score * keyword_weight
            
            if paper_id in paper_scores:
                # Combine scores
                existing_score, paper = paper_scores[paper_id]
                paper_scores[paper_id] = (existing_score + keyword_score, paper)
            else:
                paper_scores[paper_id] = (keyword_score, result.paper)
        
        # Create combined results
        combined_results = [
            SearchResult(
                paper=paper,
                score=score,
                match_type="hybrid"
            )
            for paper_id, (score, paper) in paper_scores.items()
        ]
        
        # Sort by combined score
        combined_results.sort(key=lambda x: x.score, reverse=True)
        
        # Limit results
        combined_results = combined_results[:limit]
        
        logger.info(
            f"Hybrid search for '{query[:50]}...' returned {len(combined_results)} results "
            f"(semantic_weight={semantic_weight}, keyword_weight={keyword_weight})"
        )
        
        return combined_results


# Convenience functions
async def search_papers(
    db: Session,
    query: str,
    mode: str = "hybrid",
    limit: int = 10,
    **filters
) -> List[Dict[str, Any]]:
    """
    High-level search function with automatic mode selection.
    
    Args:
        mode: "semantic", "keyword", or "hybrid"
        filters: Additional filters (collection_ids, tag_ids, year_from, year_to)
    
    Returns:
        List of paper dictionaries with scores
    """
    if mode == "semantic":
        results = await VectorSearchService.semantic_search(db, query, limit, **filters)
    elif mode == "keyword":
        results = VectorSearchService.keyword_search(db, query, limit, **filters)
    else:  # hybrid
        results = await VectorSearchService.hybrid_search(db, query, limit, **filters)
    
    return [result.to_dict() for result in results]


async def find_similar_papers(
    db: Session,
    paper_id: int,
    limit: int = 10,
    min_score: float = 0.5,
    exclude_self: bool = True
) -> List[Dict[str, Any]]:
    """
    Find papers similar to a given paper using vector similarity.
    
    This is a fast operation as it uses pre-computed embeddings.
    
    Args:
        db: Database session
        paper_id: ID of the paper to find similar papers for
        limit: Maximum number of results
        min_score: Minimum similarity score (0.0 to 1.0)
        exclude_self: Whether to exclude the source paper from results
        
    Returns:
        List of similar paper dictionaries with similarity scores
    """
    # Get the source paper's embedding
    paper = db.query(Paper).filter(Paper.id == paper_id).first()
    
    if not paper:
        logger.warning(f"Paper {paper_id} not found")
        return []
    
    if paper.embedding_title_abstract is None:
        logger.warning(f"Paper {paper_id} has no embedding")
        return []
    
    # Build SQL query for vector similarity search
    sql = """
        SELECT 
            p.id,
            1 - (p.embedding_title_abstract <=> CAST(:source_embedding AS vector)) AS similarity
        FROM papers p
        WHERE p.embedding_title_abstract IS NOT NULL
    """
    
    # Convert embedding to plain Python floats for PostgreSQL
    embedding_list = [float(x) for x in paper.embedding_title_abstract]
    params = {"source_embedding": str(embedding_list)}
    
    # Exclude self if requested
    if exclude_self:
        sql += " AND p.id != :paper_id"
        params["paper_id"] = paper_id
    
    # Add minimum score filter
    sql += " AND (1 - (p.embedding_title_abstract <=> CAST(:source_embedding AS vector))) >= :min_score"
    params["min_score"] = min_score
    
    # Order by similarity and limit
    sql += """
        ORDER BY p.embedding_title_abstract <=> CAST(:source_embedding AS vector)
        LIMIT :limit
    """
    params["limit"] = limit
    
    try:
        result = db.execute(text(sql), params)
        rows = result.fetchall()
        
        # Fetch full paper objects and create results
        results = []
        for similar_paper_id, similarity in rows:
            similar_paper = db.query(Paper).filter(Paper.id == similar_paper_id).first()
            if similar_paper:
                results.append({
                    "paper_id": similar_paper.id,
                    "title": similar_paper.title,
                    "authors": similar_paper.authors,
                    "abstract": similar_paper.abstract[:300] + "..." if similar_paper.abstract and len(similar_paper.abstract) > 300 else similar_paper.abstract,
                    "year": similar_paper.year,
                    "journal": similar_paper.journal,
                    "doi": similar_paper.doi,
                    "similarity_score": round(float(similarity), 4),
                    "has_summary": similar_paper.ai_summary_short is not None
                })
        
        logger.info(f"Found {len(results)} similar papers for paper {paper_id}")
        return results
        
    except Exception as e:
        db.rollback()  # Rollback to clean transaction state
        logger.error(f"Similarity search failed for paper {paper_id}: {str(e)}", exc_info=True)
        raise  # Re-raise to let caller handle
        return []
