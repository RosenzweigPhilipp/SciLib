"""
Exa.ai web search tool for fallback metadata lookup.
"""
from exa_py import Exa
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class ExaSearchTool:
    """Exa.ai semantic search for finding academic paper metadata."""
    
    def __init__(self, api_key: str):
        self.exa = Exa(api_key)
    
    def search_paper_metadata(self, title: str, authors: str = "", limit: int = 3) -> List[Dict]:
        """
        Search for paper metadata using semantic search.
        
        Args:
            title: Paper title
            authors: Paper authors (optional)
            limit: Number of results to return
            
        Returns:
            List of search results with metadata
        """
        try:
            # Construct search query
            query_parts = [f'"{title}"']
            if authors:
                query_parts.append(f"authors: {authors}")
            
            query = " ".join(query_parts)
            
            # Search with Exa
            results = self.exa.search(
                query=query,
                num_results=limit,
                include_domains=[
                    "arxiv.org",
                    "scholar.google.com", 
                    "researchgate.net",
                    "semanticscholar.org",
                    "pubmed.ncbi.nlm.nih.gov",
                    "ieee.org",
                    "acm.org",
                    "springer.com",
                    "elsevier.com",
                    "nature.com",
                    "science.org"
                ],
                type="neural"  # Use semantic/neural search
            )
            
            # Extract metadata from results
            papers = []
            for result in results.results:
                paper_metadata = self._extract_metadata_from_result(result)
                if paper_metadata:
                    papers.append(paper_metadata)
            
            return papers
            
        except Exception as e:
            logger.error(f"Exa search failed: {e}")
            return []
    
    def search_doi_info(self, doi: str) -> Optional[Dict]:
        """Search for additional info about a DOI."""
        try:
            query = f"DOI {doi} paper metadata citation"
            
            results = self.exa.search(
                query=query,
                num_results=3,
                include_domains=[
                    "doi.org",
                    "crossref.org",
                    "scholar.google.com"
                ]
            )
            
            if results.results:
                return self._extract_metadata_from_result(results.results[0])
            
        except Exception as e:
            logger.error(f"Exa DOI search failed: {e}")
        
        return None
    
    def _extract_metadata_from_result(self, result) -> Optional[Dict]:
        """Extract paper metadata from Exa search result."""
        try:
            metadata = {
                "title": "",
                "url": result.url,
                "score": getattr(result, 'score', 0.0),
                "source": self._identify_source(result.url)
            }
            
            # Extract title from result title/snippet
            if hasattr(result, 'title') and result.title:
                metadata["title"] = result.title
            
            # Try to extract additional metadata based on source
            if "arxiv.org" in result.url:
                metadata.update(self._extract_arxiv_metadata(result))
            elif "scholar.google.com" in result.url:
                metadata.update(self._extract_scholar_metadata(result))
            elif "doi.org" in result.url:
                metadata.update(self._extract_doi_metadata(result))
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract metadata from Exa result: {e}")
            return None
    
    def _identify_source(self, url: str) -> str:
        """Identify the source of the search result."""
        if "arxiv.org" in url:
            return "arxiv"
        elif "scholar.google.com" in url:
            return "google_scholar"
        elif "semanticscholar.org" in url:
            return "semantic_scholar"
        elif "pubmed.ncbi.nlm.nih.gov" in url:
            return "pubmed"
        elif "ieee.org" in url:
            return "ieee"
        elif any(domain in url for domain in ["springer.com", "nature.com", "science.org"]):
            return "publisher"
        else:
            return "web"
    
    def _extract_arxiv_metadata(self, result) -> Dict:
        """Extract metadata from arXiv URLs."""
        metadata = {}
        
        try:
            # Extract arXiv ID from URL
            if "/abs/" in result.url:
                arxiv_id = result.url.split("/abs/")[-1].split("v")[0]
                metadata["arxiv_id"] = arxiv_id
                metadata["journal"] = "arXiv preprint"
        
        except Exception as e:
            logger.debug(f"Failed to extract arXiv metadata: {e}")
        
        return metadata
    
    def _extract_scholar_metadata(self, result) -> Dict:
        """Extract metadata from Google Scholar URLs."""
        metadata = {}
        
        # Google Scholar results are harder to parse from URL alone
        # Would need additional processing of the content
        
        return metadata
    
    def _extract_doi_metadata(self, result) -> Dict:
        """Extract metadata from DOI URLs."""
        metadata = {}
        
        try:
            if "doi.org" in result.url:
                doi = result.url.split("doi.org/")[-1]
                metadata["doi"] = doi
        
        except Exception as e:
            logger.debug(f"Failed to extract DOI metadata: {e}")
        
        return metadata