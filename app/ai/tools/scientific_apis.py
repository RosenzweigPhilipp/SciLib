"""
Scientific API tools for metadata lookup and validation.
"""
import requests
import httpx
from typing import Dict, Optional, List
import logging
from urllib.parse import quote
from ..utils import retry_with_exponential_backoff

logger = logging.getLogger(__name__)


class CrossRefTool:
    """CrossRef API tool for DOI lookup and metadata retrieval."""
    
    def __init__(self, email: Optional[str] = None):
        self.base_url = "https://api.crossref.org/works"
        self.headers = {
            "User-Agent": f"SciLib/1.0 (mailto:{email})" if email else "SciLib/1.0"
        }
    
    @retry_with_exponential_backoff(
        max_retries=3,
        initial_delay=1.0,
        exceptions=(requests.RequestException, requests.Timeout)
    )
    def search_by_title(self, title: str, limit: int = 5) -> List[Dict]:
        """Search for papers by title with automatic retry."""
        query = quote(title)
        url = f"{self.base_url}?query.title={query}&rows={limit}"
        
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get("message", {}).get("items", [])
    
    @retry_with_exponential_backoff(
        max_retries=3,
        initial_delay=1.0,
        exceptions=(requests.RequestException, requests.Timeout)
    )
    def search_by_doi(self, doi: str) -> Optional[Dict]:
        """Get metadata by DOI with automatic retry."""
        clean_doi = doi.strip().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
        url = f"{self.base_url}/{quote(clean_doi, safe='')}"
        
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        return data.get("message")
    
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
            
            # Year and month
            if "published" in crossref_data:
                date_parts = crossref_data["published"].get("date-parts", [[]])[0]
                if date_parts:
                    fields["year"] = date_parts[0]
                    if len(date_parts) > 1:
                        fields["month"] = date_parts[1]
            
            # Journal/Container
            if "container-title" in crossref_data and crossref_data["container-title"]:
                container = crossref_data["container-title"][0]
                fields["journal"] = container
                # For conference papers, this is booktitle
                if crossref_data.get("type") in ["proceedings-article", "paper-conference"]:
                    fields["booktitle"] = container
            
            # DOI
            if "DOI" in crossref_data:
                fields["doi"] = crossref_data["DOI"]
            
            # Volume/Issue/Pages
            if "volume" in crossref_data:
                fields["volume"] = str(crossref_data["volume"])
            if "issue" in crossref_data:
                fields["issue"] = str(crossref_data["issue"])
            if "page" in crossref_data:
                fields["pages"] = crossref_data["page"]
            
            # Abstract
            if "abstract" in crossref_data:
                fields["abstract"] = crossref_data["abstract"]
            
            # Publisher
            if "publisher" in crossref_data:
                fields["publisher"] = crossref_data["publisher"]
            
            # URL
            if "URL" in crossref_data:
                fields["url"] = crossref_data["URL"]
            elif "DOI" in crossref_data:
                fields["url"] = f"https://doi.org/{crossref_data['DOI']}"
            
            # ISBN (for books)
            if "ISBN" in crossref_data and crossref_data["ISBN"]:
                fields["isbn"] = crossref_data["ISBN"][0]
            
            # Edition (for books)
            if "edition-number" in crossref_data:
                fields["edition"] = str(crossref_data["edition-number"])
            
            # Publication type
            if "type" in crossref_data:
                pub_type = crossref_data["type"]
                # Map CrossRef types to BibTeX types
                type_map = {
                    "journal-article": "article",
                    "proceedings-article": "inproceedings",
                    "paper-conference": "inproceedings",
                    "book": "book",
                    "book-chapter": "inbook",
                    "monograph": "book"
                }
                fields["publication_type"] = type_map.get(pub_type, "article")
            
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
                    # Extract month from publication date
                    if len(date_str) >= 7:
                        try:
                            from datetime import datetime
                            date = datetime.fromisoformat(date_str[:10])
                            paper["month"] = date.month
                        except:
                            pass
            
            if summary is not None:
                paper["abstract"] = summary.text.strip()
            
            if arxiv_id is not None:
                arxiv_url = arxiv_id.text
                paper["arxiv_id"] = arxiv_url.split('/')[-1]
                paper["url"] = arxiv_url
            
            # ArXiv papers are preprints
            paper["journal"] = "arXiv preprint"
            paper["publication_type"] = "article"
            
            # Extract arXiv category for note field
            category = entry.find('{http://www.w3.org/2005/Atom}category')
            if category is not None and "term" in category.attrib:
                paper["note"] = f"arXiv:{category.attrib['term']}"
            
            return paper
            
        except Exception as e:
            logger.error(f"Failed to parse arXiv entry: {e}")
            return None


class SemanticScholarTool:
    """Semantic Scholar API tool for academic paper lookup (no API key required)."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {}
        if api_key:
            self.headers["x-api-key"] = api_key
    
    def search_by_title(self, title: str, limit: int = 5) -> List[Dict]:
        """Search Semantic Scholar by title."""
        try:
            search_url = f"{self.base_url}/paper/search"
            params = {
                "query": title,
                "limit": limit,
                "fields": "title,authors,year,abstract,citationCount,referenceCount,venue,journal,externalIds,publicationDate,url,isOpenAccess,openAccessPdf"
            }
            
            response = requests.get(search_url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", [])
            
        except Exception as e:
            error_str = str(e)
            if '429' in error_str:
                print("\033[93m⚠️  Semantic Scholar: Rate limited\033[0m")
            elif '404' in error_str:
                # 404 is normal - paper not found, no need to log
                pass
            else:
                logger.error(f"Semantic Scholar search failed: {e}")
            return []
    
    def search_by_title_match(self, title: str) -> Optional[Dict]:
        """Find best matching paper by exact title match."""
        try:
            match_url = f"{self.base_url}/paper/search/match"
            params = {
                "query": title,
                "fields": "title,authors,year,abstract,venue,journal,externalIds,publicationDate,url,citationCount"
            }
            
            response = requests.get(match_url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            # The match endpoint returns a single best match in 'data' field
            if data and "data" in data and data["data"]:
                return data["data"][0] if isinstance(data["data"], list) else data["data"]
            return None
            
        except Exception as e:
            error_str = str(e)
            if '429' in error_str:
                print("\033[93m⚠️  Semantic Scholar: Rate limited\033[0m")
            elif '404' in error_str:
                # 404 is normal - paper not found, no need to log
                pass
            else:
                logger.error(f"Semantic Scholar title match failed: {e}")
            return None
    
    def get_paper_by_doi(self, doi: str) -> Optional[Dict]:
        """Get paper metadata by DOI."""
        try:
            # Clean DOI
            clean_doi = doi.strip().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
            paper_url = f"{self.base_url}/paper/DOI:{clean_doi}"
            params = {
                "fields": "title,authors,year,abstract,venue,journal,externalIds,publicationDate,url,citationCount,referenceCount"
            }
            
            response = requests.get(paper_url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            error_str = str(e)
            if '429' in error_str:
                print("\033[93m⚠️  Semantic Scholar: Rate limited\033[0m")
            elif '404' in error_str:
                # 404 is normal - paper not found, no need to log
                pass
            else:
                logger.error(f"Semantic Scholar DOI lookup failed for {doi}: {e}")
            return None
    
    def get_paper_by_arxiv(self, arxiv_id: str) -> Optional[Dict]:
        """Get paper metadata by arXiv ID."""
        try:
            # Clean arXiv ID
            clean_id = arxiv_id.strip().replace("arXiv:", "")
            paper_url = f"{self.base_url}/paper/ARXIV:{clean_id}"
            params = {
                "fields": "title,authors,year,abstract,venue,journal,externalIds,publicationDate,url,citationCount"
            }
            
            response = requests.get(paper_url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            error_str = str(e)
            if '429' in error_str:
                print("\033[93m⚠️  Semantic Scholar: Rate limited\033[0m")
            elif '404' in error_str:
                # 404 is normal - paper not found, no need to log
                pass
            else:
                logger.error(f"Semantic Scholar arXiv lookup failed for {arxiv_id}: {e}")
            return None
    
    
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
            
            # Handle venue (could be journal or conference)
            if "venue" in s2_data and s2_data["venue"]:
                venue = s2_data["venue"]
                fields["journal"] = venue
                # Try to detect if it's a conference
                if any(word in venue.lower() for word in ["conference", "proceedings", "workshop", "symposium"]):
                    fields["booktitle"] = venue
                    fields["publication_type"] = "inproceedings"
                else:
                    fields["publication_type"] = "article"
            elif "journal" in s2_data and s2_data["journal"]:
                journal = s2_data["journal"].get("name", "") if isinstance(s2_data["journal"], dict) else s2_data["journal"]
                fields["journal"] = journal
                fields["publication_type"] = "article"
                # Extract volume/pages from journal dict
                if isinstance(s2_data["journal"], dict):
                    if "volume" in s2_data["journal"]:
                        fields["volume"] = str(s2_data["journal"]["volume"])
                    if "pages" in s2_data["journal"]:
                        fields["pages"] = s2_data["journal"]["pages"]
            
            # Extract DOI and other external IDs
            if "externalIds" in s2_data and s2_data["externalIds"]:
                external_ids = s2_data["externalIds"]
                if "DOI" in external_ids:
                    fields["doi"] = external_ids["DOI"]
                if "ArXiv" in external_ids:
                    fields["arxiv_id"] = external_ids["ArXiv"]
                if "ISBN" in external_ids:
                    fields["isbn"] = external_ids["ISBN"]
            
            # URL
            if "url" in s2_data:
                fields["url"] = s2_data["url"]
            elif fields.get("doi"):
                fields["url"] = f"https://doi.org/{fields['doi']}"
            
            # Publication date for month
            if "publicationDate" in s2_data and s2_data["publicationDate"]:
                try:
                    from datetime import datetime
                    date = datetime.fromisoformat(s2_data["publicationDate"].replace("Z", "+00:00"))
                    fields["month"] = date.month
                except:
                    pass
            
            # Citation count (for confidence scoring)
            if "citationCount" in s2_data:
                fields["citationCount"] = s2_data["citationCount"]
            
        except Exception as e:
            logger.error(f"Failed to extract BibTeX fields from S2 data: {e}")
        
        return fields


class OpenAlexTool:
    """OpenAlex API tool for academic paper lookup (free, no API key needed, no rate limits)."""
    
    def __init__(self, email: Optional[str] = None):
        self.base_url = "https://api.openalex.org"
        # OpenAlex encourages including email for polite pool (faster access)
        self.headers = {}
        if email:
            self.headers["User-Agent"] = f"SciLib/1.0 (mailto:{email})"
    
    def search_by_title(self, title: str, limit: int = 5) -> List[Dict]:
        """Search OpenAlex by title."""
        try:
            search_url = f"{self.base_url}/works"
            params = {
                "search": title,
                "per_page": limit,
                "select": "id,doi,title,display_name,publication_year,authorships,abstract_inverted_index,primary_location,type,cited_by_count,biblio"
            }
            
            response = requests.get(search_url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get("results", [])
            
        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")
            return []
    
    def search_by_doi(self, doi: str) -> Optional[Dict]:
        """Get paper metadata by DOI."""
        try:
            # Clean DOI
            clean_doi = doi.strip().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
            paper_url = f"{self.base_url}/works/doi:{clean_doi}"
            
            response = requests.get(paper_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"OpenAlex DOI lookup failed for {doi}: {e}")
            return None
    
    def extract_bibtex_fields(self, openalex_data: Dict) -> Dict:
        """Extract BibTeX fields from OpenAlex response."""
        fields = {}
        
        try:
            # Title - OpenAlex uses 'display_name' or 'title'
            if "display_name" in openalex_data:
                fields["title"] = openalex_data["display_name"]
            elif "title" in openalex_data:
                fields["title"] = openalex_data["title"]
            
            # Authors
            if "authorships" in openalex_data:
                authors = []
                for authorship in openalex_data["authorships"]:
                    author_data = authorship.get("author", {})
                    author_name = author_data.get("display_name", "")
                    if author_name:
                        authors.append(author_name)
                if authors:
                    fields["authors"] = "; ".join(authors)
            
            # Year and publication date
            if "publication_year" in openalex_data and openalex_data["publication_year"]:
                fields["year"] = openalex_data["publication_year"]
            
            if "publication_date" in openalex_data and openalex_data["publication_date"]:
                try:
                    from datetime import datetime
                    date = datetime.fromisoformat(openalex_data["publication_date"])
                    fields["month"] = date.month
                except:
                    pass
            
            # Abstract (OpenAlex stores as inverted index)
            if "abstract_inverted_index" in openalex_data and openalex_data["abstract_inverted_index"]:
                abstract = self._reconstruct_abstract(openalex_data["abstract_inverted_index"])
                if abstract:
                    fields["abstract"] = abstract
            
            # Journal/Venue and Publisher
            if "primary_location" in openalex_data and openalex_data["primary_location"]:
                location = openalex_data["primary_location"]
                source = location.get("source", {})
                if source:
                    if source.get("display_name"):
                        venue_name = source["display_name"]
                        fields["journal"] = venue_name
                        # Detect conference papers
                        if source.get("type") == "conference" or any(word in venue_name.lower() for word in ["conference", "proceedings", "workshop"]):
                            fields["booktitle"] = venue_name
                            fields["publication_type"] = "inproceedings"
                        else:
                            fields["publication_type"] = "article"
                    # Publisher
                    if source.get("host_organization_name"):
                        fields["publisher"] = source["host_organization_name"]
            
            # DOI
            if "doi" in openalex_data and openalex_data["doi"]:
                # OpenAlex DOI comes as URL, extract just the DOI
                doi_url = openalex_data["doi"]
                doi = doi_url.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
                fields["doi"] = doi
                # Construct DOI URL
                if not fields.get("url"):
                    fields["url"] = f"https://doi.org/{doi}"
            
            # Volume, Issue, Pages from biblio
            if "biblio" in openalex_data and openalex_data["biblio"]:
                biblio = openalex_data["biblio"]
                if biblio.get("volume"):
                    fields["volume"] = str(biblio["volume"])
                if biblio.get("issue"):
                    fields["issue"] = str(biblio["issue"])
                if biblio.get("first_page") and biblio.get("last_page"):
                    fields["pages"] = f"{biblio['first_page']}-{biblio['last_page']}"
                elif biblio.get("first_page"):
                    fields["pages"] = str(biblio["first_page"])
            
            # Publication type from OpenAlex type
            if "type" in openalex_data:
                type_map = {
                    "article": "article",
                    "book": "book",
                    "book-chapter": "inbook",
                    "proceedings-article": "inproceedings",
                    "dissertation": "phdthesis"
                }
                if openalex_data["type"] in type_map and not fields.get("publication_type"):
                    fields["publication_type"] = type_map[openalex_data["type"]]
            
            # URL - use OpenAlex ID if no DOI URL
            if not fields.get("url") and "id" in openalex_data:
                fields["url"] = openalex_data["id"]
            
            # Citation count (for confidence scoring)
            if "cited_by_count" in openalex_data:
                fields["citationCount"] = openalex_data["cited_by_count"]
            
        except Exception as e:
            logger.error(f"Failed to extract BibTeX fields from OpenAlex data: {e}")
        
        return fields
    
    def _reconstruct_abstract(self, inverted_index: Dict) -> str:
        """Reconstruct abstract text from OpenAlex inverted index."""
        try:
            # Inverted index maps words to their positions
            word_positions = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            # Sort by position and join
            word_positions.sort()
            abstract = " ".join([word for _, word in word_positions])
            return abstract
            
        except Exception as e:
            logger.error(f"Failed to reconstruct abstract: {e}")
            return ""