"""
Citation Analysis Service

Analyzes citation relationships, calculates influence metrics,
and provides citation network insights.
"""
import logging
from typing import Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from datetime import datetime
from collections import defaultdict

from ...database.models import Paper, Citation
from ..tools.scientific_apis import SemanticScholarTool
from ...config import settings

logger = logging.getLogger(__name__)


class CitationAnalysisService:
    """Service for analyzing citations and calculating influence metrics"""
    
    def __init__(self, db: Session):
        self.db = db
        self.semantic_scholar = SemanticScholarTool()
    
    def add_citation(
        self,
        citing_paper_id: int,
        cited_paper_id: int,
        context: Optional[str] = None
    ) -> Citation:
        """
        Add a citation relationship between two papers
        
        Args:
            citing_paper_id: Paper that cites another paper
            cited_paper_id: Paper being cited
            context: Optional context text around citation
        
        Returns:
            Created Citation object
        """
        # Check if citation already exists
        existing = self.db.query(Citation).filter(
            Citation.citing_paper_id == citing_paper_id,
            Citation.cited_paper_id == cited_paper_id
        ).first()
        
        if existing:
            logger.info(f"Citation already exists: {citing_paper_id} -> {cited_paper_id}")
            return existing
        
        # Prevent self-citation
        if citing_paper_id == cited_paper_id:
            raise ValueError("Cannot create self-citation")
        
        # Create citation
        citation = Citation(
            citing_paper_id=citing_paper_id,
            cited_paper_id=cited_paper_id,
            context=context
        )
        
        self.db.add(citation)
        self.db.commit()
        self.db.refresh(citation)
        
        logger.info(f"Added citation: Paper {citing_paper_id} cites Paper {cited_paper_id}")
        
        # Trigger will update counts automatically
        return citation
    
    def remove_citation(self, citing_paper_id: int, cited_paper_id: int) -> bool:
        """Remove a citation relationship"""
        citation = self.db.query(Citation).filter(
            Citation.citing_paper_id == citing_paper_id,
            Citation.cited_paper_id == cited_paper_id
        ).first()
        
        if citation:
            self.db.delete(citation)
            self.db.commit()
            logger.info(f"Removed citation: {citing_paper_id} -> {cited_paper_id}")
            return True
        
        return False
    
    def get_citations_for_paper(self, paper_id: int) -> Dict[str, List[Dict]]:
        """
        Get all citations for a paper (both citing and cited)
        
        Returns:
            Dictionary with 'citing' and 'cited' lists
        """
        paper = self.db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")
        
        # Papers that cite this paper
        citing = []
        for citation in paper.citations_received:
            citing.append({
                "id": citation.citing_paper.id,
                "title": citation.citing_paper.title,
                "authors": citation.citing_paper.authors,
                "year": citation.citing_paper.year,
                "context": citation.context,
                "citation_id": citation.id
            })
        
        # Papers cited by this paper
        cited = []
        for citation in paper.citations_made:
            cited.append({
                "id": citation.cited_paper.id,
                "title": citation.cited_paper.title,
                "authors": citation.cited_paper.authors,
                "year": citation.cited_paper.year,
                "context": citation.context,
                "citation_id": citation.id
            })
        
        return {
            "citing": citing,  # Papers that cite this paper
            "cited": cited,    # Papers this paper cites
            "citation_count": len(citing),
            "reference_count": len(cited)
        }
    
    def fetch_external_citations(self, paper_id: int) -> Dict:
        """
        Fetch citation data from external sources (Semantic Scholar)
        
        Updates external_citation_count for the paper
        """
        paper = self.db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")
        
        citation_data = {
            "external_citations": 0,
            "references": [],
            "source": None
        }
        
        # Try DOI first
        if paper.doi:
            try:
                result = self.semantic_scholar.get_paper_by_doi(paper.doi)
                if result:
                    citation_data["external_citations"] = result.get("citationCount", 0)
                    citation_data["source"] = "Semantic Scholar (DOI)"
                    
                    # Update paper
                    paper.external_citation_count = citation_data["external_citations"]
                    paper.citations_updated_at = datetime.utcnow()
                    self.db.commit()
                    
                    logger.info(
                        f"Updated external citations for paper {paper_id}: "
                        f"{citation_data['external_citations']} citations"
                    )
                    return citation_data
            except Exception as e:
                logger.error(f"Failed to fetch citations by DOI: {e}")
        
        # Try title match
        try:
            result = self.semantic_scholar.search_by_title_match(paper.title)
            if result:
                citation_data["external_citations"] = result.get("citationCount", 0)
                citation_data["source"] = "Semantic Scholar (Title)"
                
                # Update paper
                paper.external_citation_count = citation_data["external_citations"]
                paper.citations_updated_at = datetime.utcnow()
                self.db.commit()
                
                logger.info(
                    f"Updated external citations for paper {paper_id}: "
                    f"{citation_data['external_citations']} citations"
                )
        except Exception as e:
            logger.error(f"Failed to fetch citations by title: {e}")
        
        return citation_data
    
    def calculate_influence_score(self, paper_id: int) -> float:
        """
        Calculate influence score for a paper based on citation network
        
        Formula combines:
        - Direct citations (40%)
        - Citation velocity (20%)
        - H-index contribution (20%)
        - Network centrality (20%)
        """
        paper = self.db.query(Paper).filter(Paper.id == paper_id).first()
        if not paper:
            raise ValueError(f"Paper {paper_id} not found")
        
        # Get total papers in library for normalization
        total_papers = self.db.query(func.count(Paper.id)).scalar()
        
        if total_papers <= 1:
            return 0.0
        
        # 1. Direct citation score (normalized)
        max_citations = self.db.query(func.max(Paper.citation_count)).scalar() or 1
        max_citations = float(max_citations)
        citation_score = (paper.citation_count / max_citations) if max_citations > 0 else 0.0
        
        # 2. Citation velocity (citations per year since publication)
        current_year = datetime.utcnow().year
        if paper.year and current_year > paper.year:
            years_since_pub = current_year - paper.year
            velocity = paper.citation_count / max(years_since_pub, 1)
            max_velocity = self.db.query(
                func.max(Paper.citation_count / func.greatest(current_year - Paper.year, 1))
            ).scalar() or 1
            max_velocity = float(max_velocity)
            velocity_score = velocity / max_velocity if max_velocity > 0 else 0.0
        else:
            velocity_score = 0.0
        
        # 3. H-index contribution
        h_index = self._calculate_h_index(paper_id)
        max_h_index = self.db.query(func.max(Paper.h_index)).scalar() or 1
        max_h_index = float(max_h_index)
        h_index_score = h_index / max_h_index if max_h_index > 0 else 0.0
        
        # 4. Network centrality (papers that cite influential papers)
        centrality_score = self._calculate_centrality(paper_id)
        
        # Weighted combination
        influence = (
            0.4 * citation_score +
            0.2 * velocity_score +
            0.2 * h_index_score +
            0.2 * centrality_score
        )
        
        # Update paper
        paper.influence_score = influence
        paper.h_index = h_index
        paper.citations_updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Calculated influence score for paper {paper_id}: {influence:.4f}")
        return influence
    
    def _calculate_h_index(self, paper_id: int) -> int:
        """Calculate h-index for a paper based on its citations"""
        # Get citation counts for all papers this paper cites
        citations = self.db.query(
            Paper.citation_count
        ).join(
            Citation, Citation.cited_paper_id == Paper.id
        ).filter(
            Citation.citing_paper_id == paper_id
        ).order_by(
            Paper.citation_count.desc()
        ).all()
        
        if not citations:
            return 0
        
        # H-index: largest number h such that h papers have at least h citations
        citation_counts = [c[0] for c in citations]
        h = 0
        for i, count in enumerate(citation_counts, 1):
            if count >= i:
                h = i
            else:
                break
        
        return h
    
    def _calculate_centrality(self, paper_id: int) -> float:
        """Calculate network centrality score"""
        # Papers that cite this paper
        citing_papers = self.db.query(Paper.id, Paper.citation_count).join(
            Citation, Citation.citing_paper_id == Paper.id
        ).filter(
            Citation.cited_paper_id == paper_id
        ).all()
        
        if not citing_papers:
            return 0.0
        
        # Weighted by citation count of citing papers
        total_influence = sum(count for _, count in citing_papers)
        max_possible = len(citing_papers) * (
            self.db.query(func.max(Paper.citation_count)).scalar() or 1
        )
        
        return total_influence / max_possible if max_possible > 0 else 0.0
    
    def recalculate_all_metrics(self) -> Dict[str, int]:
        """Recalculate all citation metrics for all papers"""
        papers = self.db.query(Paper).all()
        
        updated_count = 0
        for paper in papers:
            try:
                self.calculate_influence_score(paper.id)
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to calculate metrics for paper {paper.id}: {e}")
        
        logger.info(f"Recalculated metrics for {updated_count}/{len(papers)} papers")
        return {
            "total": len(papers),
            "updated": updated_count
        }
    
    def get_most_influential_papers(self, limit: int = 10) -> List[Dict]:
        """Get most influential papers by influence score"""
        papers = self.db.query(Paper).filter(
            Paper.influence_score > 0
        ).order_by(
            Paper.influence_score.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "citation_count": p.citation_count,
                "external_citation_count": p.external_citation_count,
                "h_index": p.h_index,
                "influence_score": p.influence_score
            }
            for p in papers
        ]
    
    def get_most_cited_papers(self, limit: int = 10) -> List[Dict]:
        """Get most cited papers in library"""
        papers = self.db.query(Paper).order_by(
            Paper.citation_count.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "title": p.title,
                "authors": p.authors,
                "year": p.year,
                "citation_count": p.citation_count,
                "external_citation_count": p.external_citation_count,
                "reference_count": p.reference_count
            }
            for p in papers
        ]
    
    def get_citation_network(self) -> Dict:
        """
        Get complete citation network for visualization
        
        Returns:
            nodes: List of papers
            edges: List of citations (citing -> cited)
        """
        # Get all papers with citations
        papers = self.db.query(Paper).filter(
            (Paper.citation_count > 0) | (Paper.reference_count > 0)
        ).all()
        
        # Get all citations
        citations = self.db.query(Citation).all()
        
        nodes = [
            {
                "id": p.id,
                "title": p.title,
                "year": p.year,
                "citation_count": p.citation_count,
                "influence_score": p.influence_score
            }
            for p in papers
        ]
        
        edges = [
            {
                "source": c.citing_paper_id,
                "target": c.cited_paper_id,
                "id": c.id
            }
            for c in citations
        ]
        
        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_papers": len(nodes),
                "total_citations": len(edges),
                "avg_citations_per_paper": len(edges) / len(nodes) if nodes else 0
            }
        }
    
    def detect_citation_clusters(self) -> List[Dict]:
        """
        Detect clusters/communities in citation network
        
        Uses simple connected components algorithm
        """
        # Get all papers with citations
        papers = self.db.query(Paper).filter(
            (Paper.citation_count > 0) | (Paper.reference_count > 0)
        ).all()
        
        if not papers:
            return []
        
        # Build adjacency list
        graph = defaultdict(set)
        for citation in self.db.query(Citation).all():
            graph[citation.citing_paper_id].add(citation.cited_paper_id)
            graph[citation.cited_paper_id].add(citation.citing_paper_id)
        
        # Find connected components using DFS
        visited = set()
        clusters = []
        
        def dfs(node, cluster):
            visited.add(node)
            cluster.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, cluster)
        
        for paper in papers:
            if paper.id not in visited:
                cluster = set()
                dfs(paper.id, cluster)
                if len(cluster) > 1:  # Only include clusters with 2+ papers
                    clusters.append(cluster)
        
        # Convert to detailed format
        result = []
        for i, cluster in enumerate(clusters, 1):
            cluster_papers = self.db.query(Paper).filter(
                Paper.id.in_(cluster)
            ).all()
            
            result.append({
                "cluster_id": i,
                "size": len(cluster),
                "papers": [
                    {
                        "id": p.id,
                        "title": p.title,
                        "authors": p.authors,
                        "year": p.year
                    }
                    for p in cluster_papers
                ]
            })
        
        return result


def add_citation_link(
    db: Session,
    citing_paper_id: int,
    cited_paper_id: int,
    context: Optional[str] = None
) -> Citation:
    """Convenience function to add a citation"""
    service = CitationAnalysisService(db)
    return service.add_citation(citing_paper_id, cited_paper_id, context)
