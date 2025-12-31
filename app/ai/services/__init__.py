"""
AI Services Package

This package contains high-level AI services for SciLib:
- embedding_service: Generate vector embeddings for semantic search
"""

from .embedding_service import EmbeddingService, generate_embedding, generate_paper_embedding

__all__ = [
    "EmbeddingService",
    "generate_embedding", 
    "generate_paper_embedding"
]

