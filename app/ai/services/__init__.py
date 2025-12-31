"""
AI Services Package

This package contains high-level AI services for SciLib:
- embedding_service: Generate vector embeddings for semantic search
- summary_service: Generate AI summaries of papers
- vector_search_service: Semantic and hybrid search over papers
"""

from .embedding_service import EmbeddingService, generate_embedding, generate_paper_embedding
from .summary_service import SummaryService, generate_paper_summary
from .vector_search_service import VectorSearchService, SearchResult, search_papers

__all__ = [
    "EmbeddingService",
    "generate_embedding", 
    "generate_paper_embedding",
    "SummaryService",
    "generate_paper_summary"
]

