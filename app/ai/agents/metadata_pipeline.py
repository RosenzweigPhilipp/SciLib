"""
Direct LLM-based metadata extraction pipeline for scientific papers.
Simplified approach without complex agent frameworks.
"""
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, List, Optional, Any
import json
import logging
import asyncio

# Import our extraction tools
from ..extractors.pdf_extractor import PDFExtractor
from ..tools.scientific_apis import CrossRefTool, ArxivTool, SemanticScholarTool
from ..tools.exa_search import ExaSearchTool

logger = logging.getLogger(__name__)


class MetadataExtractionPipeline:
    """
    Simplified metadata extraction pipeline using direct LLM calls.
    
    Pipeline:
    1. PDF Content Extraction -> Extract text/metadata from PDF
    2. LLM Analysis -> Analyze content and extract structured metadata  
    3. API Search & Validation -> Search databases and validate results
    4. Final Processing -> Merge, validate, and generate BibTeX
    """
    
    def __init__(self, 
                 openai_api_key: str,
                 exa_api_key: Optional[str] = None,
                 crossref_email: Optional[str] = None,
                 semantic_scholar_key: Optional[str] = None):
        
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model="gpt-4o-mini",
            temperature=0.1  # Low temperature for consistent extraction
        )
        
        # Initialize extraction tools
        self.pdf_extractor = PDFExtractor()
        self.crossref_tool = CrossRefTool(email=crossref_email)
        self.arxiv_tool = ArxivTool()
        
        # Optional tools
        self.semantic_scholar_tool = None
        if semantic_scholar_key:
            self.semantic_scholar_tool = SemanticScholarTool(api_key=semantic_scholar_key)
        
        self.exa_tool = None
        if exa_api_key:
            self.exa_tool = ExaSearchTool(api_key=exa_api_key)
    
    async def extract_metadata(self, pdf_path: str, paper_id: int) -> Dict:
        """
        Run the complete extraction pipeline.
        
        Args:
            pdf_path: Path to PDF file
            paper_id: Database paper ID
            
        Returns:
            Dict with extracted metadata and confidence scores
        """
        pipeline_result = {
            "paper_id": paper_id,
            "pdf_path": pdf_path,
            "extraction_status": "processing",
            "confidence": 0.0,
            "metadata": {},
            "sources": [],
            "errors": []
        }
        
        try:
            # Step 1: PDF Content Extraction
            logger.info(f"Starting PDF extraction for paper {paper_id}")
            pdf_result = await self.pdf_extractor.extract_content(pdf_path)
            pipeline_result["sources"].append("pdf_extraction")
            
            if not pdf_result.get("text"):
                pipeline_result["errors"].append("Failed to extract text from PDF")
                pipeline_result["extraction_status"] = "failed"
                return pipeline_result
            
            # Step 2: LLM Analysis of PDF Content
            logger.info(f"Starting LLM analysis for paper {paper_id}")
            llm_metadata = await self._analyze_pdf_content(pdf_result)
            
            # Step 3: Search Scientific Databases
            logger.info(f"Starting database search for paper {paper_id}")
            search_results = await self._search_scientific_databases(llm_metadata)
            pipeline_result["sources"].extend(search_results.get("sources", []))
            
            # Step 4: Merge and Validate Results
            logger.info(f"Starting validation for paper {paper_id}")
            final_metadata = await self._merge_and_validate(llm_metadata, search_results)
            
            # Calculate final confidence
            confidence = self._calculate_confidence(final_metadata, search_results)
            
            pipeline_result.update({
                "extraction_status": "completed",
                "confidence": confidence,
                "metadata": final_metadata,
                "sources": list(set(pipeline_result["sources"]))
            })
            
            logger.info(f"Pipeline completed for paper {paper_id} with confidence {confidence}")
            
        except Exception as e:
            logger.error(f"Pipeline failed for paper {paper_id}: {e}")
            pipeline_result.update({
                "extraction_status": "failed",
                "errors": [str(e)]
            })
        
        return pipeline_result
    
    async def _analyze_pdf_content(self, pdf_result: Dict) -> Dict:
        """Use LLM to analyze PDF content and extract structured metadata."""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert at extracting bibliographic metadata from academic papers. 
Analyze the provided PDF text and extract the following information in JSON format:

{
  "title": "exact paper title",
  "authors": "full author list", 
  "abstract": "paper abstract if available",
  "year": "publication year",
  "journal": "journal or conference name",
  "doi": "DOI if present",
  "keywords": "keywords if available",
  "confidence": 0.8
}

Be precise and only include information you are confident about. 
Set confidence between 0.0 and 1.0 based on text quality and extraction certainty.
If information is not clearly available, use null for that field."""),
            ("human", "Extract metadata from this PDF text:\n\n{pdf_text}")
        ])
        
        try:
            response = await self.llm.ainvoke(prompt.format_messages(
                pdf_text=pdf_result.get("text", "")[:8000]  # Limit to ~8k chars
            ))
            
            # Parse JSON response
            metadata = json.loads(response.content)
            
            # Adjust confidence based on PDF extraction quality
            pdf_confidence = pdf_result.get("confidence", 0.5)
            llm_confidence = metadata.get("confidence", 0.5)
            combined_confidence = (pdf_confidence + llm_confidence) / 2
            metadata["confidence"] = combined_confidence
            
            return metadata
            
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return {
                "title": None,
                "authors": None, 
                "abstract": None,
                "year": None,
                "journal": None,
                "doi": None,
                "keywords": None,
                "confidence": 0.2,
                "error": str(e)
            }
    
    async def _search_scientific_databases(self, llm_metadata: Dict) -> Dict:
        """Search scientific databases for additional/validation metadata."""
        
        search_results = {
            "sources": [],
            "crossref": None,
            "arxiv": None,
            "semantic_scholar": None,
            "exa": None
        }
        
        # Build search query from LLM metadata
        title = llm_metadata.get("title")
        authors = llm_metadata.get("authors")
        
        if not title and not authors:
            return search_results
        
        # Search tasks
        search_tasks = []
        
        # CrossRef search
        if title:
            search_tasks.append(self._search_crossref(title))
        
        # arXiv search  
        if title:
            search_tasks.append(self._search_arxiv(title))
        
        # Semantic Scholar search
        if self.semantic_scholar_tool and title:
            search_tasks.append(self._search_semantic_scholar(title))
        
        # Execute searches in parallel
        try:
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Process results
            idx = 0
            if title:
                if not isinstance(results[idx], Exception) and results[idx]:
                    search_results["crossref"] = results[idx]
                    search_results["sources"].append("crossref")
                idx += 1
                
                if not isinstance(results[idx], Exception) and results[idx]:
                    search_results["arxiv"] = results[idx]
                    search_results["sources"].append("arxiv")
                idx += 1
                
                if self.semantic_scholar_tool:
                    if not isinstance(results[idx], Exception) and results[idx]:
                        search_results["semantic_scholar"] = results[idx]
                        search_results["sources"].append("semantic_scholar")
                    idx += 1
            
        except Exception as e:
            logger.error(f"Database search failed: {e}")
        
        # Fallback to web search if needed
        if not any(search_results[key] for key in ["crossref", "arxiv", "semantic_scholar"]):
            if self.exa_tool and title:
                try:
                    exa_result = await self._search_exa(title)
                    if exa_result:
                        search_results["exa"] = exa_result
                        search_results["sources"].append("exa")
                except Exception as e:
                    logger.error(f"Exa search failed: {e}")
        
        return search_results
    
    async def _search_crossref(self, title: str) -> Optional[Dict]:
        """Search CrossRef API."""
        try:
            result = await self.crossref_tool.search(title)
            if result and result.get("results"):
                return result["results"][0]  # Return best match
        except Exception as e:
            logger.error(f"CrossRef search failed: {e}")
        return None
    
    async def _search_arxiv(self, title: str) -> Optional[Dict]:
        """Search arXiv API."""
        try:
            result = await self.arxiv_tool.search(title)
            if result and result.get("results"):
                return result["results"][0]  # Return best match
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
        return None
    
    async def _search_semantic_scholar(self, title: str) -> Optional[Dict]:
        """Search Semantic Scholar API."""
        try:
            result = await self.semantic_scholar_tool.search(title)
            if result and result.get("results"):
                return result["results"][0]  # Return best match
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
        return None
    
    async def _search_exa(self, title: str) -> Optional[Dict]:
        """Search Exa.ai for fallback."""
        try:
            result = await self.exa_tool.search_papers(title)
            if result and result.get("results"):
                return result["results"][0]  # Return best match
        except Exception as e:
            logger.error(f"Exa search failed: {e}")
        return None
    
    async def _merge_and_validate(self, llm_metadata: Dict, search_results: Dict) -> Dict:
        """Merge LLM analysis with search results."""
        
        # Start with LLM metadata
        merged = {
            "title": llm_metadata.get("title"),
            "authors": llm_metadata.get("authors"),
            "abstract": llm_metadata.get("abstract"),
            "year": llm_metadata.get("year"),
            "journal": llm_metadata.get("journal"),
            "doi": llm_metadata.get("doi"),
            "keywords": llm_metadata.get("keywords"),
            "url": None,
            "bibtex_type": "article"
        }
        
        # Merge in search results with priority: CrossRef > Semantic Scholar > arXiv > Exa
        sources_priority = ["crossref", "semantic_scholar", "arxiv", "exa"]
        
        for source in sources_priority:
            source_data = search_results.get(source)
            if not source_data:
                continue
                
            # Merge fields, preferring non-null values
            for field in merged.keys():
                if field == "bibtex_type":
                    continue
                    
                source_value = self._extract_field_from_source(source_data, field)
                if source_value and not merged.get(field):
                    merged[field] = source_value
                elif source_value and source in ["crossref", "semantic_scholar"]:
                    # Override with high-quality sources
                    merged[field] = source_value
        
        # Clean and validate fields
        merged = self._clean_metadata(merged)
        
        # Determine BibTeX type
        merged["bibtex_type"] = self._determine_bibtex_type(merged)
        
        return merged
    
    def _extract_field_from_source(self, source_data: Dict, field: str) -> Optional[str]:
        """Extract field value from source data."""
        
        # Direct mapping
        if field in source_data:
            return str(source_data[field]).strip() if source_data[field] else None
        
        # Alternative mappings
        field_mappings = {
            "title": ["title", "paper_title"],
            "authors": ["authors", "author", "creators"],
            "abstract": ["abstract", "summary"],
            "year": ["year", "publication_year", "pub_year"],
            "journal": ["journal", "venue", "container-title"],
            "doi": ["doi", "DOI"],
            "keywords": ["keywords", "tags"],
            "url": ["url", "link", "external_url"]
        }
        
        for alt_field in field_mappings.get(field, []):
            if alt_field in source_data and source_data[alt_field]:
                return str(source_data[alt_field]).strip()
        
        return None
    
    def _clean_metadata(self, metadata: Dict) -> Dict:
        """Clean and normalize metadata fields."""
        
        # Clean title
        if metadata.get("title"):
            title = metadata["title"].strip()
            # Remove trailing periods, normalize whitespace
            title = title.rstrip(".")
            metadata["title"] = " ".join(title.split())
        
        # Clean authors  
        if metadata.get("authors"):
            authors = metadata["authors"]
            if isinstance(authors, list):
                metadata["authors"] = "; ".join(str(a).strip() for a in authors if a)
            else:
                metadata["authors"] = str(authors).strip()
        
        # Clean year
        if metadata.get("year"):
            import re
            year_match = re.search(r'\b(19|20)\d{2}\b', str(metadata["year"]))
            if year_match:
                metadata["year"] = year_match.group()
        
        # Clean DOI
        if metadata.get("doi"):
            doi = str(metadata["doi"]).strip()
            # Remove doi: prefix
            doi = re.sub(r'^(doi:?\s*)', '', doi, flags=re.IGNORECASE)
            metadata["doi"] = doi
        
        return metadata
    
    def _determine_bibtex_type(self, metadata: Dict) -> str:
        """Determine BibTeX entry type."""
        
        journal = metadata.get("journal", "").lower()
        
        # Conference patterns
        if any(pattern in journal for pattern in [
            "conference", "proceedings", "workshop", "symposium", "ieee", "acm"
        ]):
            return "inproceedings"
        
        # arXiv preprints
        if "arxiv" in journal or (metadata.get("url", "").find("arxiv") != -1):
            return "misc"
        
        return "article"
    
    def _calculate_confidence(self, metadata: Dict, search_results: Dict) -> float:
        """Calculate overall confidence score."""
        
        confidence = 0.0
        
        # Base confidence from metadata completeness
        important_fields = ["title", "authors", "year"]
        present_important = sum(1 for field in important_fields if metadata.get(field))
        confidence += (present_important / len(important_fields)) * 0.4
        
        # Bonus for additional fields
        bonus_fields = ["doi", "journal", "abstract"]
        present_bonus = sum(1 for field in bonus_fields if metadata.get(field))
        confidence += (present_bonus / len(bonus_fields)) * 0.2
        
        # Source reliability bonus
        if search_results.get("crossref"):
            confidence += 0.2
        elif search_results.get("semantic_scholar"):
            confidence += 0.15
        elif search_results.get("arxiv"):
            confidence += 0.1
        elif search_results.get("exa"):
            confidence += 0.05
        
        # Cross-validation bonus
        sources_count = len([s for s in search_results.get("sources", []) if s])
        if sources_count > 1:
            confidence += min(sources_count * 0.05, 0.2)
        
        return min(confidence, 1.0)