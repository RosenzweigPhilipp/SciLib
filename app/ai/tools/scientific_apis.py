"""
Scientific API tools for metadata lookup and validation.
"""
import requests
import httpx
from typing import Dict, Optional, List
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


class CrossRefTool:
    """CrossRef API tool for DOI lookup and metadata retrieval."""
    
    def __init__(self, email: Optional[str] = None):
        self.base_url = "https://api.crossref.org/works"
        self.headers = {
            "User-Agent": f"SciLib/1.0 (mailto:{email})" if email else "SciLib/1.0"
        }
    
    def search_by_title(self, title: str, limit: int = 5) -> List[Dict]:
        """Search for papers by title."""
        try:
            query = quote(title)
            url = f"{self.base_url}?query.title={query}&rows={limit}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get("message", {}).get("items", [])
            
        except Exception as e:
            logger.error(f"CrossRef title search failed: {e}")
            return []
    
    def search_by_doi(self, doi: str) -> Optional[Dict]:
        """Get metadata by DOI."""
        try:
            clean_doi = doi.strip().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
            url = f"{self.base_url}/{quote(clean_doi, safe='')}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get("message")
            
        except Exception as e:
            logger.error(f"CrossRef DOI lookup failed for {doi}: {e}")
            return None
    
    def extract_bibtex_fields(self, crossref_data: Dict) -> Dict:
        """Extract BibTeX fields from CrossRef response."""
        fields = {}
        
        try:
            # Title
            if "title" in crossref_data and crossref_data["title"]:
                fields["title"] = crossref_data["title"][0]
            
            # Authors
            if "author" in crossref_data:
                authors = []
                for author in crossref_data["author"]:
                    given = author.get("given", "")
                    family = author.get("family", "")
                    if family:
                        authors.append(f"{given} {family}".strip())
                fields["authors"] = "; ".join(authors)
            
            # Year
            if "published" in crossref_data:
                date_parts = crossref_data["published"].get("date-parts", [[]])[0]
                if date_parts:
                    fields["year"] = date_parts[0]
            
            # Journal
            if "container-title" in crossref_data and crossref_data["container-title"]:
                fields["journal"] = crossref_data["container-title"][0]
            
            # DOI
            if "DOI" in crossref_data:
                fields["doi"] = crossref_data["DOI"]
            
            # Volume/Issue/Pages
            if "volume" in crossref_data:
                fields["volume"] = crossref_data["volume"]
            if "issue" in crossref_data:
                fields["number"] = crossref_data["issue"]
            if "page" in crossref_data:
                fields["pages"] = crossref_data["page"]
            
            # Abstract
            if "abstract" in crossref_data:
                fields["abstract"] = crossref_data["abstract"]
            
            # Publisher
            if "publisher" in crossref_data:
                fields["publisher"] = crossref_data["publisher"]
            
        except Exception as e:
            logger.error(f"Failed to extract BibTeX fields: {e}")
        
        return fields


class ArxivTool:
    """ArXiv API tool for preprint lookup."""
    
    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
    
    def search_by_title(self, title: str, limit: int = 5) -> List[Dict]:
        """Search arXiv by title."""
        try:
            import xml.etree.ElementTree as ET
            
            query = quote(f'ti:"{title}"')
            url = f"{self.base_url}?search_query={query}&max_results={limit}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            
            papers = []
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                paper = self._parse_arxiv_entry(entry)
                if paper:
                    papers.append(paper)
            
            return papers
            
        except Exception as e:
            logger.error(f"ArXiv search failed: {e}")
            return []
    
    def _parse_arxiv_entry(self, entry) -> Optional[Dict]:
        """Parse arXiv XML entry."""
        try:
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            # Extract fields
            title = entry.find('atom:title', ns)
            authors = entry.findall('atom:author/atom:name', ns)
            published = entry.find('atom:published', ns)
            summary = entry.find('atom:summary', ns)
            arxiv_id = entry.find('atom:id', ns)
            
            paper = {}
            
            if title is not None:
                paper["title"] = title.text.strip()
            
            if authors:
                paper["authors"] = "; ".join([author.text.strip() for author in authors])
            
            if published is not None:
                # Extract year from date
                date_str = published.text
                if date_str:
                    paper["year"] = int(date_str[:4])
            
            if summary is not None:
                paper["abstract"] = summary.text.strip()
            
            if arxiv_id is not None:
                arxiv_url = arxiv_id.text
                paper["arxiv_id"] = arxiv_url.split('/')[-1]
                paper["url"] = arxiv_url
            
            # ArXiv papers are preprints
            paper["journal"] = "arXiv preprint"
            
            return paper
            
        except Exception as e:
            logger.error(f"Failed to parse arXiv entry: {e}")
            return None


class SemanticScholarTool:
    """Semantic Scholar API tool for academic paper lookup."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper"
        self.headers = {}
        if api_key:
            self.headers["x-api-key"] = api_key
    
    def search_by_title(self, title: str, limit: int = 5) -> List[Dict]:
        """Search Semantic Scholar by title."""
        try:
            search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": title,
                "limit": limit,
                "fields": "title,authors,year,abstract,citationCount,referenceCount,journal,externalIds"
            }
            
            response = requests.get(search_url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []
    
    def extract_bibtex_fields(self, s2_data: Dict) -> Dict:
        """Extract BibTeX fields from Semantic Scholar response."""
        fields = {}
        
        try:
            if "title" in s2_data:
                fields["title"] = s2_data["title"]
            
            if "authors" in s2_data:
                authors = [author.get("name", "") for author in s2_data["authors"] if author.get("name")]
                fields["authors"] = "; ".join(authors)
            
            if "year" in s2_data:
                fields["year"] = s2_data["year"]
            
            if "abstract" in s2_data:
                fields["abstract"] = s2_data["abstract"]
            
            if "journal" in s2_data and s2_data["journal"]:
                fields["journal"] = s2_data["journal"].get("name", "")
            
            # Extract DOI from external IDs
            if "externalIds" in s2_data and s2_data["externalIds"]:
                external_ids = s2_data["externalIds"]
                if "DOI" in external_ids:
                    fields["doi"] = external_ids["DOI"]
                if "ArXiv" in external_ids:
                    fields["arxiv_id"] = external_ids["ArXiv"]
            
        except Exception as e:
            logger.error(f"Failed to extract BibTeX fields from S2 data: {e}")
        
        return fields