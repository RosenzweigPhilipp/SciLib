"""
Embedding Service for SciLib

Generates vector embeddings for papers using OpenAI's text-embedding-3-small model.
Embeddings are used for semantic search and recommendations.
"""

import logging
from typing import List, Optional
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key)

# Constants
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
MAX_TOKENS = 8191  # Max tokens for text-embedding-3-small


class EmbeddingService:
    """Service for generating and managing paper embeddings"""
    
    @staticmethod
    async def generate_embedding(text: str) -> Optional[List[float]]:
        """
        Generate embedding vector for given text using OpenAI API.
        
        Args:
            text: Text to embed (title, abstract, or combined)
            
        Returns:
            List of floats representing the embedding vector (1536 dimensions)
            or None if generation fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding generation")
            return None
        
        try:
            # Truncate text if too long (rough estimate: 1 token ≈ 4 characters)
            max_chars = MAX_TOKENS * 4
            if len(text) > max_chars:
                logger.info(f"Truncating text from {len(text)} to {max_chars} characters")
                text = text[:max_chars]
            
            # Generate embedding
            response = await client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            
            # Validate dimension
            if len(embedding) != EMBEDDING_DIMENSION:
                logger.error(f"Unexpected embedding dimension: {len(embedding)}, expected {EMBEDDING_DIMENSION}")
                return None
            
            logger.info(f"Successfully generated embedding (dim={len(embedding)})")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    async def generate_paper_embedding(title: str, abstract: Optional[str] = None) -> Optional[List[float]]:
        """
        Generate embedding for a paper based on title and abstract.
        
        Combines title and abstract into a single text for embedding.
        If abstract is missing, uses only the title.
        
        Args:
            title: Paper title
            abstract: Paper abstract (optional)
            
        Returns:
            Embedding vector or None if generation fails
        """
        if not title:
            logger.warning("Cannot generate embedding without title")
            return None
        
        # Combine title and abstract
        text_parts = [title]
        if abstract and abstract.strip():
            text_parts.append(abstract)
        
        combined_text = " ".join(text_parts)
        
        logger.info(f"Generating embedding for paper: '{title[:50]}...' (length={len(combined_text)})")
        return await EmbeddingService.generate_embedding(combined_text)
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Note: In practice, use database vector operations for efficiency.
        This is mainly for testing/debugging.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity score (-1 to 1, higher is more similar)
        """
        import numpy as np
        
        if len(vec1) != len(vec2):
            raise ValueError(f"Vectors must have same dimension: {len(vec1)} vs {len(vec2)}")
        
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        # Cosine similarity = dot product / (norm1 * norm2)
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))


# Convenience functions for backward compatibility
async def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding for arbitrary text"""
    return await EmbeddingService.generate_embedding(text)


async def generate_paper_embedding(title: str, abstract: Optional[str] = None) -> Optional[List[float]]:
    """Generate embedding for paper (title + abstract)"""
    return await EmbeddingService.generate_paper_embedding(title, abstract)

