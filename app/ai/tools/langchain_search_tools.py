"""
LangChain tool wrappers for metadata search functionality.
"""
from langchain_core.tools import BaseTool
from typing import Dict, Any, Optional
from pydantic import Field
import json
import asyncio

from ..tools.scientific_apis import CrossRefTool, ArxivTool, SemanticScholarTool
from ..tools.exa_search import ExaSearchTool as ExaSearchService


class CrossRefSearchTool(BaseTool):
    """Tool for searching CrossRef API for paper metadata."""
    
    name: str = "crossref_search"
    description: str = """
    Search CrossRef API for academic paper metadata using title, authors, or DOI.
    Best for finding official publication information and citations.
    Input: Search query (title, authors, DOI) as string
    Output: JSON with paper metadata including DOI, title, authors, journal, year
    """
    
    email: Optional[str] = Field(default=None)
    crossref_tool: CrossRefTool = Field(default=None)
    
    def __init__(self, email: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.crossref_tool = CrossRefTool(email=email)
    
    def _run(self, query: str) -> str:
        """Search CrossRef synchronously."""
        try:
            result = asyncio.run(self.crossref_tool.search(query))
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "results": []})
    
    async def _arun(self, query: str) -> str:
        """Search CrossRef asynchronously."""
        try:
            result = await self.crossref_tool.search(query)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "results": []})


class ArxivSearchTool(BaseTool):
    """Tool for searching arXiv for preprint papers."""
    
    name: str = "arxiv_search"
    description: str = """
    Search arXiv for preprint papers by title, authors, or abstract keywords.
    Best for finding recent research papers and preprints.
    Input: Search query as string
    Output: JSON with paper metadata including arXiv ID, title, authors, abstract, categories
    """
    
    arxiv_tool: ArxivTool = Field(default_factory=ArxivTool)
    
    def _run(self, query: str) -> str:
        """Search arXiv synchronously."""
        try:
            result = asyncio.run(self.arxiv_tool.search(query))
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "results": []})
    
    async def _arun(self, query: str) -> str:
        """Search arXiv asynchronously."""
        try:
            result = await self.arxiv_tool.search(query)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "results": []})


class SemanticScholarSearchTool(BaseTool):
    """Tool for searching Semantic Scholar academic database."""
    
    name: str = "semantic_scholar_search"
    description: str = """
    Search Semantic Scholar for academic papers with rich metadata and citation information.
    Provides additional context like influential citations and paper abstracts.
    Input: Search query (title, authors) as string
    Output: JSON with detailed paper metadata including citations, abstracts, venue info
    """
    
    api_key: Optional[str] = Field(default=None)
    semantic_tool: SemanticScholarTool = Field(default=None)
    
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.semantic_tool = SemanticScholarTool(api_key=api_key)
    
    def _run(self, query: str) -> str:
        """Search Semantic Scholar synchronously."""
        try:
            result = asyncio.run(self.semantic_tool.search(query))
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "results": []})
    
    async def _arun(self, query: str) -> str:
        """Search Semantic Scholar asynchronously."""
        try:
            result = await self.semantic_tool.search(query)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "results": []})


class ExaSearchTool(BaseTool):
    """Tool for semantic web search using Exa.ai."""
    
    name: str = "exa_semantic_search"
    description: str = """
    Perform semantic web search for academic papers using Exa.ai.
    Use as fallback when other APIs don't have the paper.
    Searches academic domains and extracts metadata from paper pages.
    Input: Search query (paper title or description) as string  
    Output: JSON with found papers and extracted metadata from web sources
    """
    
    api_key: str = Field(...)
    exa_tool: ExaSearchService = Field(default=None)
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self.exa_tool = ExaSearchService(api_key=api_key)
    
    def _run(self, query: str) -> str:
        """Search Exa.ai synchronously."""
        try:
            result = asyncio.run(self.exa_tool.search_papers(query))
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "results": []})
    
    async def _arun(self, query: str) -> str:
        """Search Exa.ai asynchronously."""
        try:
            result = await self.exa_tool.search_papers(query)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "results": []})


class MultiSearchTool(BaseTool):
    """Tool that combines multiple search sources for comprehensive results."""
    
    name: str = "multi_source_search"
    description: str = """
    Search multiple academic databases simultaneously for comprehensive metadata.
    Combines results from CrossRef, arXiv, Semantic Scholar, and web search.
    Input: Search query as string
    Output: JSON with merged results from all sources, ranked by reliability
    """
    
    crossref_tool: CrossRefSearchTool
    arxiv_tool: ArxivSearchTool  
    semantic_tool: Optional[SemanticScholarSearchTool]
    exa_tool: Optional[ExaSearchTool]
    
    def __init__(self, 
                 crossref_email: Optional[str] = None,
                 semantic_scholar_key: Optional[str] = None,
                 exa_api_key: Optional[str] = None,
                 **kwargs):
        super().__init__(**kwargs)
        
        self.crossref_tool = CrossRefSearchTool(email=crossref_email)
        self.arxiv_tool = ArxivSearchTool()
        
        if semantic_scholar_key:
            self.semantic_tool = SemanticScholarSearchTool(api_key=semantic_scholar_key)
        
        if exa_api_key:
            self.exa_tool = ExaSearchTool(api_key=exa_api_key)
    
    def _run(self, query: str) -> str:
        """Run multi-source search synchronously."""
        try:
            return asyncio.run(self._search_all_sources(query))
        except Exception as e:
            return json.dumps({"error": str(e), "results": []})
    
    async def _arun(self, query: str) -> str:
        """Run multi-source search asynchronously."""
        try:
            return await self._search_all_sources(query)
        except Exception as e:
            return json.dumps({"error": str(e), "results": []})
    
    async def _search_all_sources(self, query: str) -> str:
        """Search all available sources and merge results."""
        results = {
            "query": query,
            "sources": {},
            "merged_results": [],
            "confidence_scores": {}
        }
        
        # Search all sources in parallel
        search_tasks = []
        source_names = []
        
        # Always available sources
        search_tasks.extend([
            self.crossref_tool._arun(query),
            self.arxiv_tool._arun(query)
        ])
        source_names.extend(["crossref", "arxiv"])
        
        # Optional sources
        if hasattr(self, 'semantic_tool') and self.semantic_tool:
            search_tasks.append(self.semantic_tool._arun(query))
            source_names.append("semantic_scholar")
        
        if hasattr(self, 'exa_tool') and self.exa_tool:
            search_tasks.append(self.exa_tool._arun(query))
            source_names.append("exa")
        
        # Execute searches
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Process results
        for source_name, result in zip(source_names, search_results):
            if isinstance(result, Exception):
                results["sources"][source_name] = {"error": str(result)}
            else:
                try:
                    parsed_result = json.loads(result)
                    results["sources"][source_name] = parsed_result
                except json.JSONDecodeError:
                    results["sources"][source_name] = {"error": "Invalid JSON response"}
        
        # Merge and rank results
        merged = self._merge_search_results(results["sources"])
        results["merged_results"] = merged
        
        return json.dumps(results, indent=2)
    
    def _merge_search_results(self, source_results: Dict) -> List[Dict]:
        """Merge and deduplicate results from multiple sources."""
        merged = []
        seen_titles = set()
        
        # Define source priorities (higher = more reliable)
        source_priorities = {
            "crossref": 4,
            "semantic_scholar": 3,
            "arxiv": 2,
            "exa": 1
        }
        
        # Collect all papers with source priority
        all_papers = []
        
        for source, data in source_results.items():
            if "results" in data and isinstance(data["results"], list):
                priority = source_priorities.get(source, 0)
                
                for paper in data["results"]:
                    if "title" in paper:
                        paper["source"] = source
                        paper["source_priority"] = priority
                        all_papers.append(paper)
        
        # Sort by source priority (highest first)
        all_papers.sort(key=lambda x: x.get("source_priority", 0), reverse=True)
        
        # Deduplicate by title similarity
        for paper in all_papers:
            title = paper.get("title", "").lower().strip()
            
            # Skip if we've seen a very similar title
            if any(self._titles_similar(title, seen_title) for seen_title in seen_titles):
                continue
            
            seen_titles.add(title)
            
            # Calculate confidence based on source and completeness
            confidence = self._calculate_paper_confidence(paper)
            paper["confidence"] = confidence
            
            merged.append(paper)
        
        # Sort final results by confidence
        merged.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        
        return merged[:5]  # Return top 5 results
    
    def _titles_similar(self, title1: str, title2: str) -> bool:
        """Check if two titles are similar enough to be considered the same paper."""
        if not title1 or not title2:
            return False
        
        # Simple similarity check
        words1 = set(title1.split())
        words2 = set(title2.split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        # Jaccard similarity
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        return similarity > 0.7  # 70% word overlap
    
    def _calculate_paper_confidence(self, paper: Dict) -> float:
        """Calculate confidence score for a paper based on available metadata."""
        confidence = 0.0
        
        # Source reliability
        source_scores = {
            "crossref": 0.4,
            "semantic_scholar": 0.3,
            "arxiv": 0.3,
            "exa": 0.2
        }
        
        confidence += source_scores.get(paper.get("source", ""), 0.1)
        
        # Metadata completeness
        important_fields = ["title", "authors", "year", "doi"]
        present_fields = sum(1 for field in important_fields if paper.get(field))
        confidence += (present_fields / len(important_fields)) * 0.4
        
        # Additional metadata
        bonus_fields = ["abstract", "journal", "keywords"]
        bonus_score = sum(0.1 for field in bonus_fields if paper.get(field))
        confidence += min(bonus_score, 0.2)  # Max 0.2 bonus
        
        return min(confidence, 1.0)