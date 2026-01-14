"""
Recommendation Service for SciLib

Generates paper recommendations based on multiple similarity strategies:
- Vector similarity (semantic)
- Tag-based similarity
- Collection-based similarity
- Author-based similarity
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_

from app.database.models import Paper, Collection
from app.ai.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RecommendationStrategy:
    """Base class for recommendation strategies"""
    
    def __init__(self, weight: float = 1.0):
        self.weight = weight
    
    def calculate_score(self, target_paper: Paper, candidate: Paper, db: Session) -> float:
        """Calculate similarity score between target and candidate paper"""
        raise NotImplementedError


class VectorSimilarityStrategy(RecommendationStrategy):
    """Recommend based on vector embedding similarity"""
    
    def calculate_score(self, target_paper: Paper, candidate: Paper, db: Session) -> float:
        """Calculate cosine similarity between embeddings"""
        if target_paper.embedding_title_abstract is None or candidate.embedding_title_abstract is None:
            return 0.0
        
        try:
            # Use database to compute cosine similarity
            sql = """
                SELECT 1 - (
                    (SELECT embedding_title_abstract FROM papers WHERE id = :target_id) <=>
                    (SELECT embedding_title_abstract FROM papers WHERE id = :candidate_id)
                ) AS similarity
            """
            result = db.execute(
                text(sql),
                {"target_id": target_paper.id, "candidate_id": candidate.id}
            )
            row = result.fetchone()
            return float(row[0]) if row else 0.0
        except Exception as e:
            logger.error(f"Error calculating vector similarity: {str(e)}")
            return 0.0


# TagSimilarityStrategy removed - tags feature disabled


class CollectionSimilarityStrategy(RecommendationStrategy):
    """Recommend papers from same collections"""
    
    def calculate_score(self, target_paper: Paper, candidate: Paper, db: Session) -> float:
        """Calculate Jaccard similarity of collections"""
        target_collections = set(col.id for col in target_paper.collections)
        candidate_collections = set(col.id for col in candidate.collections)
        
        if not target_collections or not candidate_collections:
            return 0.0
        
        intersection = len(target_collections & candidate_collections)
        union = len(target_collections | candidate_collections)
        
        return intersection / union if union > 0 else 0.0


class AuthorSimilarityStrategy(RecommendationStrategy):
    """Recommend papers by same authors"""
    
    def calculate_score(self, target_paper: Paper, candidate: Paper, db: Session) -> float:
        """Calculate author overlap (normalized)"""
        # Simple approach: check if any author appears in both papers
        target_authors = set(author.strip().lower() for author in target_paper.authors.split(','))
        candidate_authors = set(author.strip().lower() for author in candidate.authors.split(','))
        
        if not target_authors or not candidate_authors:
            return 0.0
        
        intersection = len(target_authors & candidate_authors)
        
        # Full match = 1.0, partial match = lower score
        if intersection > 0:
            return intersection / max(len(target_authors), len(candidate_authors))
        
        return 0.0


class YearProximityStrategy(RecommendationStrategy):
    """Recommend papers published around the same time"""
    
    def __init__(self, weight: float = 1.0, max_year_diff: int = 5):
        super().__init__(weight)
        self.max_year_diff = max_year_diff
    
    def calculate_score(self, target_paper: Paper, candidate: Paper, db: Session) -> float:
        """Score based on publication year proximity"""
        if not target_paper.year or not candidate.year:
            return 0.0
        
        year_diff = abs(target_paper.year - candidate.year)
        
        if year_diff > self.max_year_diff:
            return 0.0
        
        # Linear decay: 1.0 at same year, 0.0 at max_year_diff
        return 1.0 - (year_diff / self.max_year_diff)


class RecommendationResult:
    """Container for recommendation result"""
    
    def __init__(self, paper: Paper, total_score: float, strategy_scores: Dict[str, float]):
        self.paper = paper
        self.total_score = total_score
        self.strategy_scores = strategy_scores
        
        # Determine primary reason
        self.primary_reason = max(strategy_scores.items(), key=lambda x: x[1])[0] if strategy_scores else "unknown"
    
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
            "score": round(self.total_score, 4),
            "primary_reason": self.primary_reason,
            "strategy_scores": {k: round(v, 4) for k, v in self.strategy_scores.items()},
            "has_summary": self.paper.ai_summary_short is not None,
            "has_embedding": self.paper.embedding_title_abstract is not None
        }


class RecommendationService:
    """Service for generating paper recommendations"""
    
    DEFAULT_STRATEGIES = [
        ("vector", VectorSimilarityStrategy(weight=0.5)),
        # Tags strategy removed (tags feature disabled)
        ("collections", CollectionSimilarityStrategy(weight=0.2)),
        ("authors", AuthorSimilarityStrategy(weight=0.15)),
        ("year", YearProximityStrategy(weight=0.05))
    ]
    
    @staticmethod
    def get_recommendations(
        db: Session,
        paper_id: int,
        limit: int = 5,
        min_score: float = 0.1,
        strategies: Optional[List[Tuple[str, RecommendationStrategy]]] = None,
        exclude_ids: Optional[List[int]] = None
    ) -> List[RecommendationResult]:
        """
        Generate recommendations for a paper.
        
        Args:
            db: Database session
            paper_id: Target paper ID
            limit: Maximum number of recommendations
            min_score: Minimum total score threshold
            strategies: List of (name, strategy) tuples (uses defaults if None)
            exclude_ids: Paper IDs to exclude from recommendations
            
        Returns:
            List of RecommendationResult objects ordered by score
        """
        # Get target paper
        target_paper = db.query(Paper).filter(Paper.id == paper_id).first()
        if not target_paper:
            logger.warning(f"Paper {paper_id} not found")
            return []
        
        # Use default strategies if none provided
        if strategies is None:
            strategies = RecommendationService.DEFAULT_STRATEGIES
        
        # Get all candidate papers (exclude target and specified IDs)
        exclude_ids = exclude_ids or []
        exclude_ids.append(paper_id)
        
        candidates = db.query(Paper).filter(
            Paper.id.notin_(exclude_ids)
        ).all()
        
        if not candidates:
            logger.info(f"No candidate papers for recommendations (paper {paper_id})")
            return []
        
        logger.info(f"Generating recommendations for paper {paper_id} from {len(candidates)} candidates")
        
        # Calculate scores for each candidate
        results = []
        for candidate in candidates:
            strategy_scores = {}
            total_score = 0.0
            
            for strategy_name, strategy in strategies:
                try:
                    score = strategy.calculate_score(target_paper, candidate, db)
                    weighted_score = score * strategy.weight
                    strategy_scores[strategy_name] = score
                    total_score += weighted_score
                except Exception as e:
                    logger.error(f"Error in {strategy_name} strategy: {str(e)}")
                    strategy_scores[strategy_name] = 0.0
            
            # Normalize total score by sum of weights
            total_weight = sum(s.weight for _, s in strategies)
            total_score = total_score / total_weight if total_weight > 0 else 0.0
            
            if total_score >= min_score:
                results.append(RecommendationResult(candidate, total_score, strategy_scores))
        
        # Sort by total score
        results.sort(key=lambda x: x.total_score, reverse=True)
        
        # Limit results
        results = results[:limit]
        
        logger.info(f"Generated {len(results)} recommendations for paper {paper_id}")
        
        return results
    
    @staticmethod
    def cache_recommendations(
        db: Session,
        paper_id: int,
        recommendations: List[RecommendationResult],
        cache_duration_days: int = 7
    ) -> bool:
        """
        Cache recommendations in paper's metadata field.
        
        Args:
            db: Database session
            paper_id: Target paper ID
            recommendations: List of recommendations to cache
            cache_duration_days: How long cache is valid
            
        Returns:
            True if cached successfully
        """
        try:
            paper = db.query(Paper).filter(Paper.id == paper_id).first()
            if not paper:
                return False
            
            # Store in extraction_metadata JSON field (repurposing existing field)
            if paper.extraction_metadata is None:
                paper.extraction_metadata = {}
            
            paper.extraction_metadata["recommendations"] = {
                "generated_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=cache_duration_days)).isoformat(),
                "results": [rec.to_dict() for rec in recommendations]
            }
            
            db.commit()
            logger.info(f"Cached {len(recommendations)} recommendations for paper {paper_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error caching recommendations: {str(e)}")
            db.rollback()
            return False
    
    @staticmethod
    def get_cached_recommendations(
        db: Session,
        paper_id: int
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Retrieve cached recommendations if still valid.
        
        Returns:
            List of recommendation dicts or None if cache invalid/expired
        """
        try:
            paper = db.query(Paper).filter(Paper.id == paper_id).first()
            if not paper or not paper.extraction_metadata:
                return None
            
            cached = paper.extraction_metadata.get("recommendations")
            if not cached:
                return None
            
            # Check expiration
            expires_at = datetime.fromisoformat(cached["expires_at"])
            if datetime.utcnow() > expires_at:
                logger.info(f"Cached recommendations for paper {paper_id} expired")
                return None
            
            logger.info(f"Retrieved {len(cached['results'])} cached recommendations for paper {paper_id}")
            return cached["results"]
            
        except Exception as e:
            logger.error(f"Error retrieving cached recommendations: {str(e)}")
            return None


# Convenience function
def get_recommendations(
    db: Session,
    paper_id: int,
    limit: int = 5,
    use_cache: bool = True,
    force_refresh: bool = False
) -> List[Dict[str, Any]]:
    """
    High-level function to get recommendations with caching.
    
    Args:
        db: Database session
        paper_id: Target paper ID
        limit: Maximum recommendations
        use_cache: Whether to use cached results
        force_refresh: Force regenerate even if cached
        
    Returns:
        List of recommendation dictionaries
    """
    # Check cache first
    if use_cache and not force_refresh:
        cached = RecommendationService.get_cached_recommendations(db, paper_id)
        if cached:
            return cached[:limit]
    
    # Generate fresh recommendations
    results = RecommendationService.get_recommendations(db, paper_id, limit=limit)
    
    # Cache results
    if results:
        RecommendationService.cache_recommendations(db, paper_id, results)
    
    return [rec.to_dict() for rec in results]
