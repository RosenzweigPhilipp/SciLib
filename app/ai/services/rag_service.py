"""
RAG Service for SciLib

Implements Retrieval-Augmented Generation for question answering over user's paper library.
Combines semantic search with LLM generation to answer questions based on paper content.
"""

import logging
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from openai import AsyncOpenAI

from app.database.models import Paper
from app.ai.services.vector_search_service import VectorSearchService
from app.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """Service for RAG-based question answering over paper library"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"
        self.max_context_papers = 5
        self.max_tokens = 1000
    
    async def answer_question(
        self,
        db: Session,
        query: str,
        collection_ids: Optional[List[int]] = None,
        tag_ids: Optional[List[int]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        max_papers: int = 5
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG over the user's paper library.
        
        Args:
            db: Database session
            query: User's question
            collection_ids: Filter papers by collections
            tag_ids: Filter papers by tags
            year_from: Filter papers from this year
            year_to: Filter papers up to this year
            max_papers: Maximum papers to use as context
            
        Returns:
            Dictionary with answer, sources, and metadata
        """
        try:
            # Step 1: Retrieve relevant papers using semantic search
            logger.info(f"RAG: Retrieving papers for query: {query[:100]}...")
            search_results = await VectorSearchService.semantic_search(
                db=db,
                query=query,
                limit=max_papers,
                min_score=0.2,  # Lowered from 0.3 to handle meta-linguistic queries like "what do I have"
                collection_ids=collection_ids,
                tag_ids=tag_ids,
                year_from=year_from,
                year_to=year_to
            )
            
            if not search_results:
                return {
                    "answer": "I couldn't find any relevant papers in your library to answer this question.",
                    "sources": [],
                    "context_papers_count": 0,
                    "has_sources": False
                }
            
            # Step 2: Build context from retrieved papers
            context = self._build_context(search_results)
            logger.info(f"RAG: Built context from {len(search_results)} papers")
            
            # Step 3: Generate answer using LLM
            logger.info("RAG: Generating answer with LLM...")
            answer = await self._generate_answer(query, context)
            
            # Step 4: Format response with sources
            sources = [
                {
                    "paper_id": result.paper.id,
                    "title": result.paper.title,
                    "authors": result.paper.authors,
                    "year": result.paper.year,
                    "relevance_score": round(result.score, 4),
                    "doi": result.paper.doi,
                    "journal": result.paper.journal
                }
                for result in search_results
            ]
            
            return {
                "answer": answer,
                "sources": sources,
                "context_papers_count": len(search_results),
                "has_sources": True
            }
            
        except Exception as e:
            logger.error(f"Error in RAG answer generation: {str(e)}", exc_info=True)
            return {
                "answer": f"An error occurred while processing your question: {str(e)}",
                "sources": [],
                "context_papers_count": 0,
                "has_sources": False,
                "error": str(e)
            }
    
    def _build_context(self, search_results: List) -> str:
        """
        Build context string from retrieved papers.
        
        Args:
            search_results: List of SearchResult objects
            
        Returns:
            Formatted context string for LLM
        """
        context_parts = []
        
        for idx, result in enumerate(search_results, 1):
            paper = result.paper
            
            # Build paper context
            paper_context = f"[Paper {idx}]\n"
            paper_context += f"Title: {paper.title}\n"
            
            if paper.authors:
                paper_context += f"Authors: {paper.authors}\n"
            
            if paper.year:
                paper_context += f"Year: {paper.year}\n"
            
            if paper.journal:
                paper_context += f"Journal: {paper.journal}\n"
            
            # Use AI summary if available, otherwise use abstract
            if paper.ai_summary_long:
                paper_context += f"Summary: {paper.ai_summary_long}\n"
            elif paper.ai_summary_short:
                paper_context += f"Summary: {paper.ai_summary_short}\n"
            elif paper.abstract:
                paper_context += f"Abstract: {paper.abstract}\n"
            
            # Add keywords if available
            if paper.keywords:
                paper_context += f"Keywords: {paper.keywords}\n"
            
            context_parts.append(paper_context)
        
        return "\n---\n\n".join(context_parts)
    
    async def _generate_answer(self, query: str, context: str) -> str:
        """
        Generate answer using LLM with retrieved context.
        
        Args:
            query: User's question
            context: Context from retrieved papers
            
        Returns:
            Generated answer
        """
        system_prompt = """You are a helpful research assistant for SciLib, a scientific paper manager.
Your task is to answer questions based on the user's paper library.

Guidelines:
- Answer the question using ONLY information from the provided papers
- Be specific and cite paper numbers in your answer (e.g., "According to Paper 1...")
- If papers disagree, mention the different perspectives
- If the papers don't contain enough information to answer, say so clearly
- Be concise but informative
- Use academic but accessible language
- Don't make up information or cite external sources not in the context"""
        
        user_prompt = f"""Based on the following papers from my library, please answer this question:

Question: {query}

Papers:
{context}

Please provide a clear, well-structured answer with citations to the specific papers."""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=0.3,  # Lower temperature for more factual answers
            )
            
            answer = response.choices[0].message.content.strip()
            return answer
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {str(e)}", exc_info=True)
            raise Exception(f"Failed to generate answer: {str(e)}")
    
    async def generate_enhanced_query(
        self,
        db: Session,
        user_query: str,
        paper_id: Optional[int] = None
    ) -> str:
        """
        Generate an enhanced search query using LLM.
        Useful for improving vague queries or context-aware external discovery.
        
        Args:
            db: Database session
            user_query: Original user query
            paper_id: Optional paper ID for context
            
        Returns:
            Enhanced search query
        """
        try:
            # Build context if paper provided
            context = ""
            if paper_id:
                paper = db.query(Paper).filter(Paper.id == paper_id).first()
                if paper:
                    context = f"\nContext paper: {paper.title}"
                    if paper.abstract:
                        context += f"\nAbstract: {paper.abstract[:500]}..."
            
            system_prompt = """You are a search query optimizer for scientific literature.
Generate an improved search query that will find relevant papers.
- Expand abbreviations
- Add synonyms and related terms
- Keep it concise (max 100 words)
- Focus on key concepts
Return ONLY the enhanced query, no explanations."""
            
            user_prompt = f"Original query: {user_query}{context}\n\nGenerate an enhanced search query:"
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.5
            )
            
            enhanced = response.choices[0].message.content.strip()
            logger.info(f"Enhanced query: {user_query} -> {enhanced}")
            return enhanced
            
        except Exception as e:
            logger.error(f"Error enhancing query: {str(e)}")
            return user_query  # Fallback to original
