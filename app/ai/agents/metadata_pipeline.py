"""
Direct LLM-based metadata extraction pipeline for scientific papers.
Simplified approach without complex agent frameworks.
"""
from openai import AsyncOpenAI
from typing import Dict, List, Optional, Any
import json
import logging
import asyncio
import re
import os
from difflib import SequenceMatcher

# Import our extraction tools
from ..extractors.pdf_extractor import PDFExtractor
from ..tools.scientific_apis import CrossRefTool, ArxivTool, SemanticScholarTool, OpenAlexTool
from ..tools.exa_search import ExaSearchTool

logger = logging.getLogger(__name__)

# Check if debug mode is enabled
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def debug_log(message: str, color: str = Colors.OKBLUE):
    """Log debug message if DEBUG is enabled. Uses logging instead of print."""
    if DEBUG:
        # In debug mode, print colored output to console for readability
        print(f"{color}{message}{Colors.ENDC}")
    # Always log properly (will go to log files in production)
    logger.debug(message)

def debug_result(tool_name: str, result: Any, confidence: float = None):
    """Log formatted tool result."""
    status = "SUCCESS" if result else "NO_RESULTS"
    conf_text = f" (confidence: {confidence:.2f})" if confidence else ""
    log_message = f"{status} - {tool_name}{conf_text}"
    
    if DEBUG:
        # Console output with colors in debug mode
        status_color = Colors.OKGREEN if result else Colors.WARNING
        status_symbol = "✓ SUCCESS" if result else "✗ NO RESULTS"
        print(f"{status_color}{status_symbol}{Colors.ENDC} - {Colors.BOLD}{tool_name}{Colors.ENDC}{conf_text}")
        if result and isinstance(result, dict):
            # Show key fields
            for key in ['title', 'authors', 'doi', 'year', 'journal']:
                if key in result and result[key]:
                    value = str(result[key])[:80]
                    print(f"  {Colors.OKCYAN}{key}{Colors.ENDC}: {value}")
    
    # Always log properly
    logger.debug(log_message)
    if result and isinstance(result, dict):
        for key in ['title', 'authors', 'doi', 'year', 'journal']:
            if key in result and result[key]:
                logger.debug(f"  {key}: {str(result[key])[:80]}")


class MetadataExtractionPipeline:
    """
    Enhanced metadata extraction pipeline with DOI-first strategy and optional LLM.
    
    Pipeline:
    1. PDF Content Extraction -> Extract text/metadata from PDF
    2. Basic Metadata Extraction -> Extract title/authors/DOI directly (fast, free)
    3. DOI-First Lookup -> If DOI found, query APIs directly
    4. API Search -> Use title/authors to search scientific databases
    5. LLM Analysis (Optional) -> Only if APIs return poor results
    6. Validation & Merging -> Cross-check sources and merge with confidence scoring
    """
    
    def __init__(self, 
                 openai_api_key: str,
                 exa_api_key: Optional[str] = None,
                 crossref_email: Optional[str] = None,
                 semantic_scholar_key: Optional[str] = None,
                 use_llm: bool = False):  # LLM disabled by default
        
        self.use_llm = use_llm
        
        if use_llm:
            self.llm = AsyncOpenAI(api_key=openai_api_key)
            self.model = "gpt-4o-mini"
        else:
            self.llm = None
            self.model = None
        
        # Initialize extraction tools
        self.pdf_extractor = PDFExtractor()
        self.crossref_tool = CrossRefTool(email=crossref_email)
        self.arxiv_tool = ArxivTool()
        
        # Semantic Scholar (no API key required, but can be provided for higher rate limits)
        self.semantic_scholar_tool = SemanticScholarTool(api_key=semantic_scholar_key)
        
        # OpenAlex (free, no rate limits, no API key needed)
        self.openalex_tool = OpenAlexTool(email=crossref_email)
        
        self.exa_tool = None
        if exa_api_key:
            self.exa_tool = ExaSearchTool(api_key=exa_api_key)
    
    async def extract_metadata(self, pdf_path: str, paper_id: int, force_llm: bool = False) -> Dict:
        """
        Run the complete extraction pipeline with DOI-first and LLM-optional strategy.
        
        Args:
            pdf_path: Path to PDF file
            paper_id: Database paper ID
            force_llm: If True, force LLM analysis even if APIs return results
            
        Returns:
            Dict with extracted metadata and confidence scores
        """
        if DEBUG:
            print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
            print(f"{Colors.HEADER}{Colors.BOLD}AI EXTRACTION PIPELINE - Paper {paper_id}{Colors.ENDC}")
            print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
        
        pipeline_result = {
            "paper_id": paper_id,
            "pdf_path": pdf_path,
            "extraction_status": "processing",
            "confidence": 0.0,
            "metadata": {},
            "sources": [],
            "errors": [],
            "validation_notes": []
        }
        
        try:
            # Step 1: PDF Content Extraction
            debug_log(f"{'─'*80}", Colors.OKCYAN)
            debug_log(f"STEP 1: PDF Content Extraction", Colors.BOLD + Colors.OKCYAN)
            debug_log(f"{'─'*80}", Colors.OKCYAN)
            logger.debug(f"Step 1: PDF extraction for paper {paper_id}")
            
            pdf_result = self.pdf_extractor.extract_content(pdf_path)
            pipeline_result["sources"].append("pdf_extraction")
            
            debug_result("PDF Extractor", pdf_result)
            if pdf_result.get("text"):
                debug_log(f"  Extracted {len(pdf_result['text'])} characters from {pdf_result.get('page_count', '?')} pages", Colors.OKGREEN)
            
            if not pdf_result.get("text"):
                error_msg = (
                    "Failed to extract text from PDF. "
                    "Possible causes: (1) Scanned document without OCR, "
                    "(2) Password-protected file, (3) Corrupted PDF. "
                    "Try: Re-scan with OCR, remove password protection, or check file integrity."
                )
                pipeline_result["errors"].append(error_msg)
                pipeline_result["extraction_status"] = "failed"
                pipeline_result["user_action"] = "manual_entry_required"
                debug_log("✗ PDF extraction failed - no text found", Colors.FAIL)
                logger.error(f"Paper {paper_id}: {error_msg}")
                return pipeline_result
            
            # Step 2: Direct Metadata Extraction (Fast, Free)
            debug_log(f"\n{'─'*80}", Colors.OKCYAN)
            debug_log(f"STEP 2: Direct Metadata Extraction", Colors.BOLD + Colors.OKCYAN)
            debug_log(f"{'─'*80}", Colors.OKCYAN)
            logger.debug(f"Step 2: Direct metadata extraction for paper {paper_id}")
            
            basic_metadata = self.pdf_extractor.extract_basic_metadata(pdf_path)
            pipeline_result["sources"].append("direct_extraction")
            
            title = basic_metadata.get("title")
            authors = basic_metadata.get("authors")
            doi = basic_metadata.get("doi")
            
            debug_result("Direct PDF Metadata", basic_metadata)
            logger.debug(f"Extracted - Title: {title}, DOI: {doi}")
            
            # Step 3: DOI-First Lookup Strategy
            debug_log(f"\n{'─'*80}", Colors.OKCYAN)
            debug_log(f"STEP 3: DOI-First Lookup Strategy", Colors.BOLD + Colors.OKCYAN)
            debug_log(f"{'─'*80}", Colors.OKCYAN)
            
            doi_metadata = None
            if doi:
                debug_log(f"DOI found: {doi}", Colors.OKGREEN)
                logger.debug(f"Step 3: DOI lookup for paper {paper_id} with DOI {doi}")
                doi_metadata = await self._doi_lookup_by_value(doi)
                if doi_metadata:
                    pipeline_result["sources"].append("doi_lookup")
                    pipeline_result["validation_notes"].append("DOI found and successfully queried")
                    debug_result("DOI Lookup", doi_metadata, 0.95)
                else:
                    debug_log("DOI lookup returned no results", Colors.WARNING)
            else:
                debug_log("No DOI found in PDF, skipping direct lookup", Colors.WARNING)
                logger.debug(f"Step 3: No DOI found, skipping direct lookup")
            
            # Step 4: Search Scientific Databases
            debug_log(f"\n{'─'*80}", Colors.OKCYAN)
            debug_log(f"STEP 4: Scientific Database Search", Colors.BOLD + Colors.OKCYAN)
            debug_log(f"{'─'*80}", Colors.OKCYAN)
            logger.debug(f"Step 4: Scientific database search for paper {paper_id}")
            
            search_results = await self._search_scientific_databases_direct(
                title, authors, doi_metadata
            )
            pipeline_result["sources"].extend(search_results.get("sources", []))
            
            # Check if we have good results from APIs
            has_good_results = any(search_results.get(key) for key in [
                "crossref", "semantic_scholar_match", "semantic_scholar"
            ])
            
            debug_log(f"\nAPI Results Summary:", Colors.BOLD)
            debug_log(f"  Good results found: {has_good_results}", Colors.OKGREEN if has_good_results else Colors.WARNING)
            debug_log(f"  Total sources: {len(search_results.get('sources', []))}", Colors.OKBLUE)
            
            # Step 5: LLM Analysis (Optional - only if APIs failed and LLM enabled)
            debug_log(f"\n{'─'*80}", Colors.OKCYAN)
            debug_log(f"STEP 5: LLM Analysis (Optional)", Colors.BOLD + Colors.OKCYAN)
            debug_log(f"{'─'*80}", Colors.OKCYAN)
            
            llm_metadata = None
            if (not has_good_results or force_llm) and self.use_llm:
                if force_llm:
                    debug_log("Forcing LLM analysis (low confidence on previous run)", Colors.WARNING)
                    logger.debug(f"Step 5: Forcing LLM analysis for low confidence")
                else:
                    debug_log("APIs returned poor results, using LLM analysis", Colors.WARNING)
                    logger.debug(f"Step 5: APIs returned poor results, using LLM analysis")
                llm_metadata = await self._analyze_pdf_content(pdf_result)
                pipeline_result["sources"].append("llm_analysis")
                debug_result("LLM Analysis", llm_metadata)
                
                # Retry API search with LLM-extracted metadata
                debug_log("Retrying API search with LLM-extracted metadata...", Colors.OKBLUE)
                llm_search = await self._search_scientific_databases_direct(
                    llm_metadata.get("title"),
                    llm_metadata.get("authors"),
                    doi_metadata
                )
                # Merge search results
                for key in ["crossref", "arxiv", "semantic_scholar", "semantic_scholar_match"]:
                    if llm_search.get(key) and not search_results.get(key):
                        search_results[key] = llm_search[key]
                        if key not in search_results["sources"]:
                            search_results["sources"].append(key)
            elif not has_good_results:
                debug_log("APIs returned poor results but LLM disabled", Colors.WARNING)
                logger.debug(f"Step 5: APIs returned poor results but LLM disabled")
                pipeline_result["validation_notes"].append("Limited results - consider enabling LLM analysis")
            elif not force_llm:
                debug_log("✓ APIs returned good results, skipping LLM (saved tokens!)", Colors.OKGREEN)
                logger.debug(f"Step 5: APIs returned good results, skipping LLM (saved tokens!)")
            
            # Step 6: Validate and Merge Results
            debug_log(f"\n{'─'*80}", Colors.OKCYAN)
            debug_log(f"STEP 6: Validation & Merging", Colors.BOLD + Colors.OKCYAN)
            debug_log(f"{'─'*80}", Colors.OKCYAN)
            logger.debug(f"Step 6: Validation and merging for paper {paper_id}")
            
            # Build initial metadata from direct extraction
            initial_metadata = {
                "title": title,
                "authors": authors,
                "doi": doi,
                "abstract": None,
                "year": None,
                "journal": None,
                "keywords": None
            }
            
            # If we have LLM metadata, merge it intelligently
            if llm_metadata:
                for key in ["title", "authors", "abstract", "year", "journal", "keywords"]:
                    llm_value = llm_metadata.get(key)
                    if llm_value:
                        # For authors specifically: LLM often extracts better than PDF metadata
                        # Use LLM authors if:
                        # 1. No authors in initial_metadata, OR
                        # 2. LLM was explicitly requested (force_llm=True), OR  
                        # 3. Initial authors look suspicious (single word, very short)
                        if key == "authors":
                            initial_authors = initial_metadata.get(key)
                            if not initial_authors:
                                # No authors - use LLM
                                initial_metadata[key] = llm_value
                            elif force_llm:
                                # LLM explicitly requested - trust it
                                initial_metadata[key] = llm_value
                            elif isinstance(initial_authors, str) and len(initial_authors.split()) <= 1:
                                # Suspicious author (single word) - prefer LLM
                                initial_metadata[key] = llm_value
                        else:
                            # For other fields, only fill if missing
                            if not initial_metadata.get(key):
                                initial_metadata[key] = llm_value
            
            validation_result = await self._validate_and_merge(
                initial_metadata, 
                search_results, 
                doi_metadata,
                prefer_llm=False  # Never prefer LLM over validated database sources
            )
            
            final_metadata = validation_result["metadata"]
            pipeline_result["validation_notes"].extend(validation_result.get("notes", []))
            
            # Calculate final confidence
            # Pass force_llm to indicate if this was a manual LLM rerun
            # Pass doi_used to indicate if DOI lookup was successful
            confidence = self._calculate_confidence(
                final_metadata, 
                search_results, 
                validation_result,
                llm_used=force_llm,  # True if manual rerun was triggered
                doi_used=bool(doi_metadata)  # True if DOI lookup was successful
            )
            
            pipeline_result.update({
                "extraction_status": "completed",
                "confidence": confidence,
                "metadata": final_metadata,
                "sources": list(set(pipeline_result["sources"]))
            })
            
            # Final summary
            debug_log(f"\n{'='*80}", Colors.OKGREEN)
            debug_log(f"EXTRACTION COMPLETE", Colors.BOLD + Colors.OKGREEN)
            debug_log(f"{'='*80}", Colors.OKGREEN)
            debug_log(f"Confidence: {confidence:.2%}", Colors.BOLD + Colors.OKGREEN)
            debug_log(f"Sources: {', '.join(pipeline_result['sources'])}", Colors.OKGREEN)
            debug_log(f"Title: {final_metadata.get('title', 'N/A')[:80]}", Colors.OKGREEN)
            debug_log(f"{'='*80}\n", Colors.OKGREEN)
            
            logger.debug(f"Pipeline completed for paper {paper_id} with confidence {confidence:.2f}")
            
        except Exception as e:
            logger.error(f"Pipeline failed for paper {paper_id}: {e}")
            pipeline_result.update({
                "extraction_status": "failed",
                "errors": [str(e)]
            })
        
        return pipeline_result
    
    async def _doi_lookup_by_value(self, doi: str) -> Optional[Dict]:
        """
        Lookup metadata by DOI value directly.
        """
        results = {}
        
        logger.debug(f"Performing DOI lookup for: {doi}")
        debug_log(f"  Querying CrossRef, Semantic Scholar, and OpenAlex with DOI...", Colors.OKBLUE)
        
        # CrossRef lookup
        try:
            crossref_data = self.crossref_tool.search_by_doi(doi)
            if crossref_data:
                results["crossref"] = self.crossref_tool.extract_bibtex_fields(crossref_data)
                results["source"] = "crossref_doi"
                debug_result("  CrossRef (DOI)", results["crossref"])
            else:
                debug_log("  CrossRef (DOI) - No results", Colors.WARNING)
        except Exception as e:
            logger.error(f"CrossRef DOI lookup failed: {e}")
            debug_log(f"  CrossRef (DOI) - Error: {str(e)[:60]}", Colors.FAIL)
        
        # OpenAlex lookup (no rate limits)
        try:
            openalex_data = self.openalex_tool.search_by_doi(doi)
            if openalex_data:
                results["openalex"] = self.openalex_tool.extract_bibtex_fields(openalex_data)
                if not results.get("source"):
                    results["source"] = "openalex_doi"
                debug_result("  OpenAlex (DOI)", results["openalex"])
            else:
                debug_log("  OpenAlex (DOI) - No results", Colors.WARNING)
        except Exception as e:
            logger.error(f"OpenAlex DOI lookup failed: {e}")
            debug_log(f"  OpenAlex (DOI) - Error: {str(e)[:60]}", Colors.FAIL)
        
        # Semantic Scholar lookup
        try:
            s2_data = self.semantic_scholar_tool.get_paper_by_doi(doi)
            if s2_data:
                results["semantic_scholar"] = self.semantic_scholar_tool.extract_bibtex_fields(s2_data)
                if not results.get("source"):
                    results["source"] = "semantic_scholar_doi"
                debug_result("  Semantic Scholar (DOI)", results["semantic_scholar"])
            else:
                debug_log("  Semantic Scholar (DOI) - No results", Colors.WARNING)
        except Exception as e:
            logger.error(f"Semantic Scholar DOI lookup failed: {e}")
            debug_log(f"  Semantic Scholar (DOI) - Error: {str(e)[:60]}", Colors.FAIL)
        
        return results if results else None
    
    async def _analyze_pdf_content(self, pdf_result: Dict) -> Dict:
        """Use LLM to analyze PDF content and extract structured metadata."""
        
        debug_log("  Analyzing PDF with LLM (GPT-4o-mini)...", Colors.OKBLUE)
        
        system_prompt = """You are an expert at extracting bibliographic metadata from academic papers. 
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
If information is not clearly available, use null for that field."""
        
        try:
            text_length = len(pdf_result.get("text", ""))
            debug_log(f"  Sending {min(text_length, 8000)} chars to LLM...", Colors.OKBLUE)
            
            pdf_text = pdf_result.get("text", "")[:8000]  # Limit to ~8k chars
            
            response = await self.llm.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract metadata from this PDF text:\n\n{pdf_text}"}
                ],
                temperature=0.1
            )
            
            # Parse JSON response with robust error handling
            content = response.choices[0].message.content.strip()
            
            debug_log(f"  LLM returned {len(content)} characters", Colors.OKBLUE)
            
            # Remove code block markers if present
            if content.startswith('```json'):
                content = content[7:].strip()
            if content.startswith('```'):
                content = content[3:].strip()
            if content.endswith('```'):
                content = content[:-3].strip()
            
            # Try to find JSON object in the response
            # Sometimes LLM adds text before/after the JSON
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx+1]
                print(f"[DEBUG] Extracted JSON from {start_idx} to {end_idx}, length: {len(content)}")
                print(f"[DEBUG] Extracted JSON preview: {content[:300]}")
                logger.debug(f"Extracted JSON from position {start_idx} to {end_idx}")
                debug_log(f"  Extracted JSON from position {start_idx} to {end_idx}", Colors.OKBLUE)
                debug_log(f"  JSON content preview: {content[:200]}", Colors.OKBLUE)
            
            # Try to parse JSON
            print(f"[DEBUG] Attempting to parse JSON...")
            metadata = json.loads(content)
            print(f"[DEBUG] ✓ JSON parsed successfully!")
            debug_log(f"  ✓ JSON parsed successfully", Colors.OKGREEN)
            
            # Ensure required fields exist
            required_fields = ["title", "authors", "abstract", "year", "journal", "doi", "keywords", "confidence"]
            for field in required_fields:
                if field not in metadata:
                    metadata[field] = None
            
            # Adjust confidence based on PDF extraction quality
            pdf_confidence = pdf_result.get("confidence", 0.5)
            llm_confidence = metadata.get("confidence", 0.5) or 0.5
            combined_confidence = (pdf_confidence + llm_confidence) / 2
            metadata["confidence"] = combined_confidence
            
            debug_result("  LLM Extraction", metadata, combined_confidence)
            
            return metadata
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM JSON parsing failed: {e}")
            logger.error(f"Response preview: {response.content[:300]}")
            debug_log(f"  LLM JSON parsing failed: {str(e)}", Colors.FAIL)
            return self._get_fallback_metadata(pdf_result, f"JSON parsing error: {e}")
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            debug_log(f"  LLM analysis failed: {str(e)}", Colors.FAIL)
            return self._get_fallback_metadata(pdf_result, str(e))
    
    def _get_fallback_metadata(self, pdf_result: Dict, error_msg: str) -> Dict:
        """Return fallback metadata when LLM extraction fails."""
        # Try to extract title from PDF metadata
        pdf_metadata = pdf_result.get("metadata", {})
        fallback_title = pdf_metadata.get("title", "Unknown Title")
        fallback_authors = pdf_metadata.get("author", "Unknown Authors")
        
        return {
            "title": fallback_title,
            "authors": fallback_authors,
            "abstract": None,
            "year": None,
            "journal": None,
            "doi": None,
            "keywords": None,
            "confidence": 0.2,
            "error": error_msg
        }
    
    async def _search_scientific_databases_direct(self, title: str, authors: str, doi_metadata: Optional[Dict]) -> Dict:
        """
        Search scientific databases using directly extracted title/authors.
        """
        search_results = {
            "sources": [],
            "crossref": None,
            "arxiv": None,
            "semantic_scholar": None,
            "semantic_scholar_match": None,
            "openalex": None,
            "exa": None
        }
        
        # If we already have DOI metadata, use it
        if doi_metadata:
            debug_log("  Using DOI metadata directly", Colors.OKGREEN)
            if "crossref" in doi_metadata:
                search_results["crossref"] = doi_metadata["crossref"]
                search_results["sources"].append("crossref")
            if "openalex" in doi_metadata:
                search_results["openalex"] = doi_metadata["openalex"]
                search_results["sources"].append("openalex")
            if "semantic_scholar" in doi_metadata:
                search_results["semantic_scholar"] = doi_metadata["semantic_scholar"]
                search_results["sources"].append("semantic_scholar")
            return search_results
        
        if not title:
            logger.warning("No title available for database search")
            debug_log("  No title available - skipping API searches", Colors.WARNING)
            return search_results
        
        debug_log(f"  Searching APIs with title: {title[:60]}...", Colors.OKBLUE)
        
        # Search tasks
        search_tasks = []
        
        # CrossRef search
        search_tasks.append(self._search_crossref(title))
        
        # arXiv search  
        search_tasks.append(self._search_arxiv(title))
        
        # Semantic Scholar - both regular search and title match
        search_tasks.append(self._search_semantic_scholar(title))
        search_tasks.append(self._search_semantic_scholar_match(title))
        
        # OpenAlex search
        search_tasks.append(self._search_openalex(title))
        
        # Execute searches in parallel
        try:
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Process results
            idx = 0
            
            # CrossRef
            if not isinstance(results[idx], Exception) and results[idx]:
                search_results["crossref"] = results[idx]
                search_results["sources"].append("crossref")
                debug_result("  CrossRef (Title)", results[idx])
            else:
                debug_log("  CrossRef (Title) - No results", Colors.WARNING)
            idx += 1
            
            # arXiv
            if not isinstance(results[idx], Exception) and results[idx]:
                search_results["arxiv"] = results[idx]
                search_results["sources"].append("arxiv")
                debug_result("  arXiv (Title)", results[idx])
            else:
                debug_log("  arXiv (Title) - No results", Colors.WARNING)
            idx += 1
            
            # Semantic Scholar regular search
            if not isinstance(results[idx], Exception) and results[idx]:
                search_results["semantic_scholar"] = results[idx]
                search_results["sources"].append("semantic_scholar")
                debug_result("  Semantic Scholar (Search)", results[idx])
            else:
                debug_log("  Semantic Scholar (Search) - No results", Colors.WARNING)
            idx += 1
            
            # Semantic Scholar title match (often more accurate)
            if not isinstance(results[idx], Exception) and results[idx]:
                search_results["semantic_scholar_match"] = results[idx]
                search_results["sources"].append("semantic_scholar_match")
                debug_result("  Semantic Scholar (Match)", results[idx], 0.9)
            else:
                debug_log("  Semantic Scholar (Match) - No results", Colors.WARNING)
            idx += 1
            
            # OpenAlex
            if not isinstance(results[idx], Exception) and results[idx]:
                search_results["openalex"] = results[idx]
                search_results["sources"].append("openalex")
                debug_result("  OpenAlex", results[idx])
            else:
                debug_log("  OpenAlex - No results", Colors.WARNING)
            idx += 1
            
        except Exception as e:
            logger.error(f"Database search failed: {e}")
            debug_log(f"  Database search error: {str(e)[:60]}", Colors.FAIL)
        
        # Fallback to Exa web search if no good results
        if not any(search_results[key] for key in ["crossref", "arxiv", "semantic_scholar", "semantic_scholar_match", "openalex"]):
            debug_log("  No API results - trying Exa fallback...", Colors.WARNING)
            if self.exa_tool and title:
                try:
                    exa_result = await self._search_exa(title, authors or "")
                    if exa_result:
                        search_results["exa"] = exa_result
                        search_results["sources"].append("exa")
                        debug_result("  Exa Search", exa_result)
                except Exception as e:
                    logger.error(f"Exa search failed: {e}")
                    debug_log(f"  Exa search error: {str(e)[:60]}", Colors.FAIL)
        
        return search_results
        """Search scientific databases with enhanced title matching."""
        
        search_results = {
            "sources": [],
            "crossref": None,
            "arxiv": None,
            "semantic_scholar": None,
            "semantic_scholar_match": None,  # Best match result
            "exa": None
        }
        
        # If we already have DOI metadata, use it
        if doi_metadata:
            if "crossref" in doi_metadata:
                search_results["crossref"] = doi_metadata["crossref"]
                search_results["sources"].append("crossref")
            if "semantic_scholar" in doi_metadata:
                search_results["semantic_scholar"] = doi_metadata["semantic_scholar"]
                search_results["sources"].append("semantic_scholar")
            return search_results
        
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
        
        # Semantic Scholar - both regular search and title match
        if title:
            search_tasks.append(self._search_semantic_scholar(title))
            search_tasks.append(self._search_semantic_scholar_match(title))
        
        # Execute searches in parallel
        try:
            results = await asyncio.gather(*search_tasks, return_exceptions=True)
            
            # Process results
            idx = 0
            if title:
                # CrossRef
                if not isinstance(results[idx], Exception) and results[idx]:
                    search_results["crossref"] = results[idx]
                    search_results["sources"].append("crossref")
                idx += 1
                
                # arXiv
                if not isinstance(results[idx], Exception) and results[idx]:
                    search_results["arxiv"] = results[idx]
                    search_results["sources"].append("arxiv")
                idx += 1
                
                # Semantic Scholar regular search
                if not isinstance(results[idx], Exception) and results[idx]:
                    search_results["semantic_scholar"] = results[idx]
                    search_results["sources"].append("semantic_scholar")
                idx += 1
                
                # Semantic Scholar title match (often more accurate)
                if not isinstance(results[idx], Exception) and results[idx]:
                    search_results["semantic_scholar_match"] = results[idx]
                    search_results["sources"].append("semantic_scholar_match")
                idx += 1
            
        except Exception as e:
            logger.error(f"Database search failed: {e}")
        
        # Fallback to Exa web search if no good results
        if not any(search_results[key] for key in ["crossref", "arxiv", "semantic_scholar", "semantic_scholar_match", "openalex"]):
            debug_log("  No API results - trying Exa fallback...", Colors.WARNING)
            if self.exa_tool and title:
                try:
                    exa_result = await self._search_exa(title, authors)
                    if exa_result:
                        search_results["exa"] = exa_result
                        search_results["sources"].append("exa")
                except Exception as e:
                    logger.error(f"Exa search failed: {e}")
        
        return search_results
    
    async def _search_crossref(self, title: str) -> Optional[Dict]:
        """Search CrossRef API."""
        try:
            result = self.crossref_tool.search_by_title(title)
            if result:
                return result[0] if isinstance(result, list) and result else None  # Return best match
        except Exception as e:
            logger.error(f"CrossRef search failed: {e}")
        return None
    
    async def _search_arxiv(self, title: str) -> Optional[Dict]:
        """Search arXiv API."""
        try:
            result = self.arxiv_tool.search_by_title(title)
            if result:
                return result[0] if isinstance(result, list) and result else None  # Return best match
        except Exception as e:
            logger.error(f"arXiv search failed: {e}")
        return None
    
    async def _search_semantic_scholar(self, title: str) -> Optional[Dict]:
        """Search Semantic Scholar API."""
        try:
            results = self.semantic_scholar_tool.search_by_title(title)
            if results and len(results) > 0:
                # Return the top result
                return self.semantic_scholar_tool.extract_bibtex_fields(results[0])
        except Exception as e:
            logger.error(f"Semantic Scholar search failed: {e}")
        return None
    
    async def _search_semantic_scholar_match(self, title: str) -> Optional[Dict]:
        """Search Semantic Scholar API using title match endpoint (more accurate)."""
        try:
            result = self.semantic_scholar_tool.search_by_title_match(title)
            if result:
                return self.semantic_scholar_tool.extract_bibtex_fields(result)
        except Exception as e:
            logger.error(f"Semantic Scholar title match failed: {e}")
        return None
    
    async def _search_openalex(self, title: str) -> Optional[Dict]:
        """Search OpenAlex API (free, no rate limits)."""
        try:
            results = self.openalex_tool.search_by_title(title)
            if results and len(results) > 0:
                # Return the top result
                return self.openalex_tool.extract_bibtex_fields(results[0])
        except Exception as e:
            logger.error(f"OpenAlex search failed: {e}")
        return None
    
    async def _search_exa(self, title: str, authors: str = "") -> Optional[Dict]:
        """Search Exa.ai for fallback."""
        try:
            results = self.exa_tool.search_paper_metadata(title, authors)
            if results and len(results) > 0:
                return results[0]  # Return best match
        except Exception as e:
            logger.error(f"Exa search failed: {e}")
        return None
    
    async def _validate_and_merge(self, llm_metadata: Dict, search_results: Dict, doi_metadata: Optional[Dict], prefer_llm: bool = False) -> Dict:
        """
        Validate and merge metadata from multiple sources with cross-checking.
        This is the key validation step that ensures quality.
        
        Args:
            llm_metadata: Metadata extracted from LLM or initial extraction
            search_results: Results from API searches
            doi_metadata: DOI lookup results if available
            prefer_llm: If True, trust LLM data more (used when LLM is a retry after low confidence)
        """
        validation_notes = []
        
        debug_log("  Comparing and validating sources...", Colors.OKBLUE)
        if prefer_llm:
            debug_log("  Prioritizing LLM results (retry mode)", Colors.WARNING)
        
        # Start with LLM metadata as base
        merged = {
            "title": llm_metadata.get("title"),
            "authors": llm_metadata.get("authors"),
            "abstract": llm_metadata.get("abstract"),
            "year": llm_metadata.get("year"),
            "journal": llm_metadata.get("journal"),
            "doi": llm_metadata.get("doi"),
            "keywords": llm_metadata.get("keywords"),
            "url": None,
            "bibtex_type": "article",
            # Extended BibTeX fields
            "publisher": llm_metadata.get("publisher"),
            "volume": llm_metadata.get("volume"),
            "issue": llm_metadata.get("issue"),
            "pages": llm_metadata.get("pages"),
            "booktitle": llm_metadata.get("booktitle"),
            "series": llm_metadata.get("series"),
            "edition": llm_metadata.get("edition"),
            "isbn": llm_metadata.get("isbn"),
            "month": llm_metadata.get("month"),
            "note": llm_metadata.get("note"),
            "publication_type": llm_metadata.get("publication_type")
        }
        
        # Collect all source data for validation
        all_sources = []
        
        # Priority order for merging
        source_priority = [
            ("crossref", "CrossRef"),
            ("semantic_scholar_match", "Semantic Scholar (Match)"),
            ("openalex", "OpenAlex"),
            ("semantic_scholar", "Semantic Scholar"),
            ("arxiv", "arXiv"),
            ("exa", "Exa")
        ]
        
        # Build list of available sources
        for source_key, source_name in source_priority:
            source_data = search_results.get(source_key)
            if source_data:
                all_sources.append({
                    "key": source_key,
                    "name": source_name,
                    "data": source_data
                })
                debug_log(f"    Using source: {source_name}", Colors.OKCYAN)
        
        # Validate title across sources
        if merged.get("title"):
            debug_log("  Validating title...", Colors.OKBLUE)
            title_validation = self._validate_title_across_sources(
                merged["title"], 
                all_sources
            )
            
            if title_validation["best_match"]:
                if title_validation["similarity"] < 0.8:
                    validation_notes.append(
                        f"Title similarity low ({title_validation['similarity']:.2f}). "
                        f"Using {title_validation['source']} version."
                    )
                    debug_log(f"    Title adjusted (similarity: {title_validation['similarity']:.2f})", Colors.WARNING)
                else:
                    debug_log(f"    Title validated (similarity: {title_validation['similarity']:.2f})", Colors.OKGREEN)
                merged["title"] = title_validation["best_match"]
            
            if title_validation["similarity"] >= 0.9:
                validation_notes.append("Title validated across multiple sources")
        
        # Merge fields with source priority
        debug_log("  Merging metadata fields...", Colors.OKBLUE)
        
        # Define all fields to merge (basic + extended BibTeX)
        basic_fields = ["authors", "abstract", "year", "journal", "doi", "url", "keywords"]
        extended_fields = ["publisher", "volume", "issue", "pages", "booktitle", "series", 
                          "edition", "chapter", "isbn", "month", "note", "institution", 
                          "report_number", "publication_type"]
        all_fields = basic_fields + extended_fields
        
        for source in all_sources:
            source_data = source["data"]
            source_name = source["name"]
            
            # For each field, prefer high-quality sources
            for field in all_fields:
                source_value = self._extract_field_from_source(source_data, field)
                
                if source_value and not merged.get(field):
                    # Field was missing, fill it in
                    merged[field] = source_value
                    # Mark high-quality sources as validated, not just filled
                    if source["key"] in ["crossref", "semantic_scholar_match", "openalex"]:
                        validation_notes.append(f"{field.title()} validated from {source_name}")
                    else:
                        validation_notes.append(f"{field.title()} from {source_name}")
                    debug_log(f"    Added {field} from {source_name}", Colors.OKGREEN)
                    
                elif source_value and merged.get(field):
                    # Field already exists - check if high-quality source confirms it
                    if source["key"] in ["crossref", "semantic_scholar_match", "openalex"]:
                        # For simple fields (year, journal, doi, url), check exact match
                        if field in ["year", "journal", "doi", "url"]:
                            existing_normalized = str(merged[field]).lower().strip()
                            source_normalized = str(source_value).lower().strip()
                            if existing_normalized == source_normalized or existing_normalized in source_normalized or source_normalized in existing_normalized:
                                validation_notes.append(f"{field.title()} validated from {source_name}")
                                debug_log(f"    Validated {field} from {source_name}", Colors.OKGREEN)
                        # For authors, check if they actually match
                        elif field == "authors":
                            if self._validate_authors(merged[field], source_value):
                                # Authoritative source confirms - use their version (more accurate)
                                merged[field] = source_value
                                validation_notes.append(f"Authors validated from {source_name}")
                                debug_log(f"    Validated authors from {source_name}", Colors.OKGREEN)
                            else:
                                debug_log(f"    Authors mismatch with {source_name}", Colors.WARNING)
                        # For abstract, just mark as validated if source has it (abstracts can vary slightly)
                        elif field == "abstract":
                            validation_notes.append(f"Abstract validated from {source_name}")
                            debug_log(f"    Validated abstract from {source_name}", Colors.OKGREEN)
                    # Don't process override logic if prefer_llm is True
                    continue
                    
                elif source_value and source["key"] in ["crossref", "semantic_scholar_match"] and not prefer_llm:
                    # High-quality source, potentially override (but not if we prefer LLM)
                    if field == "title":
                        # Title already validated above
                        continue
                    elif field == "authors":
                        # Validate authors
                        if self._validate_authors(merged[field], source_value):
                            merged[field] = source_value
                            validation_notes.append(f"Authors validated and updated from {source_name}")
                            debug_log(f"    Updated authors from {source_name}", Colors.OKGREEN)
                    elif field == "doi":
                        # DOI should match if both exist
                        if merged[field] != source_value:
                            validation_notes.append(f"DOI mismatch detected, using {source_name}")
                            merged[field] = source_value
                            debug_log(f"    Updated DOI from {source_name}", Colors.WARNING)
                    else:
                        # For other fields, trust high-quality sources
                        merged[field] = source_value
        
        # Clean and normalize all fields
        merged = self._clean_metadata(merged)
        
        # Determine BibTeX type
        merged["bibtex_type"] = self._determine_bibtex_type(merged)
        
        debug_log(f"  Validation complete - {len(validation_notes)} notes", Colors.OKGREEN)
        
        return {
            "metadata": merged,
            "notes": validation_notes
        }
    
    def _validate_title_across_sources(self, base_title: str, sources: List[Dict]) -> Dict:
        """
        Validate title by comparing across multiple sources.
        Returns the best matching title and similarity score.
        """
        if not base_title or not sources:
            return {"best_match": base_title, "similarity": 0.0, "source": "llm"}
        
        best_match = base_title
        best_similarity = 1.0
        best_source = "llm"
        
        base_normalized = self._normalize_title(base_title)
        
        for source in sources:
            source_title = self._extract_field_from_source(source["data"], "title")
            if not source_title:
                continue
            
            source_normalized = self._normalize_title(source_title)
            similarity = SequenceMatcher(None, base_normalized, source_normalized).ratio()
            
            # Prefer API sources if similarity is high
            if similarity > 0.75 and source["key"] in ["crossref", "semantic_scholar_match"]:
                if similarity > best_similarity or best_source == "llm":
                    best_match = source_title
                    best_similarity = similarity
                    best_source = source["name"]
        
        return {
            "best_match": best_match,
            "similarity": best_similarity,
            "source": best_source
        }
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison."""
        if not title:
            return ""
        # Lowercase, remove extra whitespace, remove punctuation
        title = title.lower().strip()
        title = re.sub(r'[^\w\s]', '', title)
        title = re.sub(r'\s+', ' ', title)
        return title
    
    def _validate_authors(self, authors1: Any, authors2: Any) -> bool:
        """
        Validate if two author representations are similar.
        Returns True if they should be considered matching.
        
        Handles:
        - Full names vs initials (J. Smith vs John Smith)
        - Multiple first names (John David Smith vs John Smith)
        - Different formatting variations
        """
        # Convert to string representations
        str1 = self._authors_to_string(authors1)
        str2 = self._authors_to_string(authors2)
        
        if not str1 or not str2:
            return False
        
        # Extract individual author names from both strings
        # Split by common separators (semicolon, comma, 'and')
        authors_list1 = re.split(r'[;,]|\band\b', str1)
        authors_list2 = re.split(r'[;,]|\band\b', str2)
        
        # Normalize and extract last names + first initial for each author
        def normalize_author(author_str):
            """Extract last name and first initial from author string."""
            author_str = author_str.strip().lower()
            
            # Extract all letter sequences
            letter_sequences = re.findall(r"[a-z]+", author_str)
            if not letter_sequences:
                return None
            
            # Last name is typically the longest sequence (heuristic for OCR errors)
            # or the last sequence if there are only 2-3 parts
            if len(letter_sequences) <= 3:
                last_name = letter_sequences[-1]
            else:
                # For complex cases, use the longest as it's likely the surname
                last_name = max(letter_sequences, key=len)
            
            # First initial from the first letter sequence
            first_initial = letter_sequences[0][0] if letter_sequences[0] else ''
            
            return (first_initial, last_name)
        
        normalized1 = [normalize_author(a) for a in authors_list1]
        normalized2 = [normalize_author(a) for a in authors_list2]
        
        # Remove None values
        normalized1 = [n for n in normalized1 if n]
        normalized2 = [n for n in normalized2 if n]
        
        if not normalized1 or not normalized2:
            return False
        
        # Check if there's significant overlap (at least 50% of authors match)
        matches = 0
        for auth1 in normalized1:
            for auth2 in normalized2:
                # Match if first initial and last name match (with fuzzy matching for OCR errors)
                first_initial_match = auth1[0] == auth2[0]
                
                # Use fuzzy matching for last names to handle OCR errors
                last_name_similarity = SequenceMatcher(None, auth1[1], auth2[1]).ratio()
                last_name_match = last_name_similarity > 0.60  # 60% similarity threshold for OCR errors
                
                if first_initial_match and last_name_match:
                    matches += 1
                    break
        
        # Consider matching if at least half of the authors match
        min_authors = min(len(normalized1), len(normalized2))
        match_threshold = max(1, min_authors // 2)
        
        return matches >= match_threshold
    
    def _authors_to_string(self, authors: Any) -> str:
        """Convert authors to string representation."""
        if isinstance(authors, str):
            return authors
        elif isinstance(authors, list):
            # Handle structured author list
            names = []
            for author in authors:
                if isinstance(author, dict):
                    given = author.get("given", "")
                    family = author.get("family", "")
                    names.append(f"{given} {family}".strip())
                else:
                    names.append(str(author))
            return " ".join(names)
        return ""
    
    def _extract_field_from_source(self, source_data: Dict, field: str) -> Optional[str]:
        """Extract field value from source data."""
        
        # Direct mapping
        if field in source_data:
            val = source_data[field]
            # For authors, preserve structured lists/dicts so cleaning can normalize
            if field == 'authors' and isinstance(val, (list, dict)):
                return val
            # For other list-like fields (e.g., title from CrossRef), return first element or string
            if isinstance(val, list):
                return str(val[0]).strip() if val else None
            if isinstance(val, dict):
                return val
            return str(val).strip() if val else None
        
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
                val = source_data[alt_field]
                if field == 'authors' and isinstance(val, (list, dict)):
                    return val
                if isinstance(val, list):
                    return str(val[0]).strip() if val else None
                if isinstance(val, dict):
                    return val
                return str(val).strip()
        
        return None
    
    def _clean_metadata(self, metadata: Dict) -> Dict:
        """Clean and normalize metadata fields."""
        
        # Clean title
        if metadata.get("title"):
            title = metadata["title"].strip()
            # Remove trailing periods, normalize whitespace
            title = title.rstrip(".")
            metadata["title"] = " ".join(title.split())
        
        # Clean authors: normalize into a structured list of {given,family,affiliation}
        if metadata.get("authors"):
            authors = metadata["authors"]
            structured = []

            def normalize_name(name_str: str) -> Dict[str, Any]:
                name = name_str.strip()
                # Handle 'Last, First' format
                if ',' in name and not name.count(',') > 1:
                    parts = [p.strip() for p in name.split(',')]
                    family = parts[0]
                    given = parts[1] if len(parts) > 1 else ''
                else:
                    parts = name.rsplit(' ', 1)
                    if len(parts) == 2:
                        given, family = parts[0].strip(), parts[1].strip()
                    else:
                        given, family = name, ''

                # Normalize punctuation issues like 'N.Gomez' -> 'N. Gomez'
                family = re.sub(r'\.(?=[A-Za-z])', '. ', family).strip()

                return {"given": given, "family": family, "affiliation": []}

            # If authors is a string, split by common delimiters
            if isinstance(authors, str):
                raw_list = []
                if ';' in authors:
                    raw_list = [a.strip() for a in authors.split(';') if a.strip()]
                elif ' and ' in authors and ',' not in authors:
                    raw_list = [a.strip() for a in authors.split(' and ') if a.strip()]
                else:
                    # Split on commas but try to detect 'Last, First' pairs
                    parts = [p.strip() for p in authors.split(',') if p.strip()]
                    # If parts look like alternating Last, First, recombine
                    if len(parts) >= 2 and all(' ' not in p for p in parts[:2]):
                        # fallback: treat the whole string as one name
                        raw_list = [authors.strip()]
                    else:
                        raw_list = parts

                for name in raw_list:
                    structured.append(normalize_name(name))

            elif isinstance(authors, list):
                for a in authors:
                    if isinstance(a, dict):
                        given = a.get('given') or a.get('first') or ''
                        family = a.get('family') or a.get('last') or ''
                        family = re.sub(r'\.(?=[A-Za-z])', '. ', str(family)).strip()
                        aff = []
                        if isinstance(a.get('affiliation'), list):
                            aff = a.get('affiliation')
                        structured.append({"given": given, "family": family, "affiliation": aff})
                    else:
                        structured.append(normalize_name(str(a)))

            metadata["authors"] = structured
        
        # Clean year
        if metadata.get("year"):
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
        """
        Determine BibTeX entry type based on metadata fields.
        
        Supported BibTeX types:
        - article: Journal articles
        - inproceedings: Conference papers
        - book: Complete books
        - inbook: Chapter/section of a book with pages
        - incollection: Part of a book with its own title (edited volume)
        - phdthesis: PhD dissertation
        - mastersthesis: Master's thesis
        - techreport: Technical report
        - misc: Anything else (arXiv, working papers, etc.)
        """
        
        title = (metadata.get("title") or "").lower()
        journal = (metadata.get("journal") or "").lower()
        booktitle = (metadata.get("booktitle") or "").lower()
        publisher = (metadata.get("publisher") or "").lower()
        url = (metadata.get("url") or "").lower()
        doi = (metadata.get("doi") or "").lower()
        
        # Check for thesis indicators
        thesis_keywords = ["thesis", "dissertation", "doctoral", "phd"]
        masters_keywords = ["master", "msc", "m.sc", "ma thesis", "mphil"]
        
        if any(kw in title for kw in thesis_keywords + masters_keywords):
            if any(kw in title for kw in ["phd", "doctoral", "ph.d"]):
                return "phdthesis"
            elif any(kw in title for kw in masters_keywords):
                return "mastersthesis"
            return "phdthesis"  # Default to PhD if unspecified
        
        # Check for technical report
        report_keywords = ["technical report", "tech report", "report no", "technical note", "working paper"]
        if any(kw in title.lower() for kw in report_keywords) or metadata.get("report_number"):
            return "techreport"
        
        # Check for book
        book_patterns = ["book", "monograph", "textbook", "handbook", "manual", "guide"]
        if metadata.get("isbn") and not booktitle:
            # Has ISBN and no booktitle → likely a complete book
            if metadata.get("chapter") or metadata.get("pages"):
                return "inbook"  # Chapter/section of a book
            return "book"
        
        if any(pattern in title for pattern in book_patterns) and publisher:
            return "book"
        
        # Check for inbook/incollection (part of book)
        if booktitle and not journal:
            # Has booktitle → part of a larger work
            if any(pattern in booktitle for pattern in ["handbook", "encyclopedia", "collection", "edited"]):
                return "incollection"
            # Conference proceedings
            if any(pattern in booktitle for pattern in [
                "conference", "proceedings", "workshop", "symposium", 
                "ieee", "acm", "icml", "neurips", "nips", "cvpr", "iccv", "eccv", "aaai",
                "international", "annual meeting", "congress"
            ]):
                return "inproceedings"
            # Default to incollection if booktitle present but not clearly conference
            return "incollection"
        
        # Conference patterns in journal field (common misuse)
        if any(pattern in journal for pattern in [
            "conference", "proceedings", "workshop", "symposium", "ieee", "acm",
            "international", "annual"
        ]):
            return "inproceedings"
        
        # arXiv preprints
        if "arxiv" in journal or "arxiv" in url or "arxiv" in doi:
            return "misc"
        
        # bioRxiv, medRxiv preprints
        if any(preprint in url or preprint in doi for preprint in ["biorxiv", "medrxiv", "ssrn"]):
            return "misc"
        
        # Has journal → article
        if journal:
            return "article"
        
        # Default to misc if nothing matches
        return "misc"
    
    def _calculate_confidence(self, metadata: Dict, search_results: Dict, validation_result: Dict, llm_used: bool = False, doi_used: bool = False) -> float:
        """
        Calculate overall confidence score for extracted metadata.
        
        This is the heart of the pipeline's quality assessment. The confidence score (0.0-1.0)
        indicates how reliable the extracted metadata is based on multiple factors.
        
        ## Confidence Score Breakdown:
        
        ### 1. Field Completeness (40% total)
           - Critical fields (30%): title, authors, year
             * These are essential for paper identification and citation
             * Missing any of these significantly impacts usefulness
           - Optional fields (10%): doi, journal, abstract
             * Nice to have but not critical for basic citation
        
        ### 2. Source Diversity (15%)
           - 0 sources: 0% (only PDF extraction, no validation)
           - 1 source: 8% (limited validation)
           - 2 sources: 12% (good cross-validation opportunity)
           - 3+ sources: 15% (excellent cross-validation)
        
        ### 3. Cross-Validation Quality (45%)
           - Title validation (13%): Sources agree on paper title
           - Authors validation (13%): Author names consistent across sources
           - Year validation (5%): Publication year matches
           - DOI validation (9%): DOI consistent and valid
           - Journal validation (5%): Publication venue matches
           
           Note: This is where incorrect metadata gets caught. If sources disagree,
           validation scores are reduced even if fields are filled.
        
        ### 4. DOI Lookup Bonus (5%)
           - Direct DOI-based lookup is most reliable
           - Applies when DOI was extracted from PDF and successfully queried
        
        ### 5. LLM Enhancement Bonus (10%)
           - Applied when LLM was used for analysis/validation
           - LLM helps resolve conflicts and improve field extraction
        
        ## Confidence Thresholds (Guidelines):
        - 0.90-1.00: Excellent - High confidence, minimal review needed
        - 0.80-0.89: Good - Acceptable quality, spot check recommended
        - 0.60-0.79: Fair - Review recommended, some issues likely
        - 0.40-0.59: Poor - Manual verification required
        - 0.00-0.39: Failed - Extraction unreliable, manual entry needed
        
        ## Examples:
        - Paper with DOI, all fields, 3 agreeing sources = ~0.95 confidence
        - Paper with title/authors from 2 sources, no DOI = ~0.70 confidence
        - Paper with only PDF-extracted title, no validation = ~0.35 confidence
        
        Args:
            metadata: Extracted metadata dictionary
            search_results: Results from scientific API searches
            validation_result: Cross-validation results between sources
            llm_used: Whether LLM was used in extraction
            doi_used: Whether DOI-based lookup was performed
        
        Returns:
            float: Confidence score between 0.0 and 1.0
        """
        confidence = 0.0
        breakdown = []
        
        # 1. FIELD COMPLETENESS (40% total)
        # Critical fields (30%): title, authors, year
        critical_fields = ["title", "authors", "year"]
        present_critical = sum(1 for field in critical_fields if metadata.get(field))
        critical_score = (present_critical / len(critical_fields)) * 0.30
        confidence += critical_score
        breakdown.append(f"Critical fields: {critical_score:.2f} ({present_critical}/{len(critical_fields)})")
        
        # Optional but important fields (10%): doi, journal/venue, abstract
        optional_fields = ["doi", "journal", "abstract"]
        present_optional = sum(1 for field in optional_fields if metadata.get(field))
        optional_score = (present_optional / len(optional_fields)) * 0.10
        confidence += optional_score
        breakdown.append(f"Optional fields: {optional_score:.2f} ({present_optional}/{len(optional_fields)})")
        
        # 2. SOURCE DIVERSITY (15%)
        # Multiple sources provide more confidence, but not if they disagree
        sources = search_results.get("sources", [])
        num_sources = len(sources)
        diversity_score = 0.0
        if num_sources == 0:
            diversity_score = 0.0
            diversity_label = "no external sources"
        elif num_sources == 1:
            diversity_score = 0.08
            diversity_label = "1 source"
        elif num_sources == 2:
            diversity_score = 0.12
            diversity_label = "2 sources"
        else:  # 3+
            diversity_score = 0.15
            diversity_label = f"{num_sources} sources"
        confidence += diversity_score
        breakdown.append(f"Source diversity: {diversity_score:.2f} ({diversity_label})")
        
        # 3. CROSS-VALIDATION QUALITY (45%)
        # Rewards agreement between sources - catches cases where sources are wrong
        validation_notes = validation_result.get("notes", [])
        validation_score = 0.0
        validation_details = []
        
        # Title validation (13%)
        if any("title validated" in note.lower() and "across" in note.lower() for note in validation_notes):
            validation_score += 0.13
            validation_details.append("title ✓✓")
        elif any("title validated" in note.lower() for note in validation_notes):
            validation_score += 0.11
            validation_details.append("title ✓")
        elif any("title" in note.lower() and "from" in note.lower() for note in validation_notes):
            # Title from source but not validated - some credit
            validation_score += 0.06
            validation_details.append("title (filled)")
        
        # Authors validation (13%)
        if any("authors validated" in note.lower() and ("updated" in note.lower() or "across" in note.lower()) for note in validation_notes):
            validation_score += 0.13
            validation_details.append("authors ✓✓")
        elif any("authors validated" in note.lower() for note in validation_notes):
            validation_score += 0.11
            validation_details.append("authors ✓")
        elif any("authors" in note.lower() and "from" in note.lower() for note in validation_notes):
            validation_score += 0.06
            validation_details.append("authors (filled)")
        
        # Year/Journal/DOI validation (19% total)
        # Give credit for both validated and filled fields
        validated_count = 0
        filled_count = 0
        for field in ["year", "journal", "doi"]:
            if any(field in note.lower() and "validated" in note.lower() for note in validation_notes):
                validated_count += 1
            elif any(field in note.lower() and "from" in note.lower() for note in validation_notes):
                filled_count += 1
        
        # Validated fields: full credit (0.13), filled fields: partial credit (0.07)
        validation_score += (validated_count / 3) * 0.13 + (filled_count / 3) * 0.07
        if validated_count > 0:
            validation_details.append(f"{validated_count}/3 validated")
        if filled_count > 0:
            validation_details.append(f"{filled_count}/3 filled")
        
        confidence += validation_score
        validation_label = ", ".join(validation_details) if validation_details else "none"
        breakdown.append(f"Cross-validation: {validation_score:.2f} ({validation_label})")
        
        # 4. DOI LOOKUP BONUS (5%)
        # Direct DOI lookup is highly reliable - metadata comes from authoritative sources
        doi_bonus = 0.0
        if doi_used:
            doi_bonus = 0.05
            breakdown.append(f"DOI lookup bonus: {doi_bonus:.2f} (direct lookup)")
            confidence += doi_bonus
        
        # 5. LLM ENHANCEMENT BONUS (up to 10%)
        # Only applies if LLM was used as a manual rerun (not initial extraction)
        llm_bonus = 0.0
        if llm_used:
            # LLM rerun was triggered - means we're using enhanced extraction
            llm_bonus = 0.10
            breakdown.append(f"LLM rerun bonus: {llm_bonus:.2f} (manual enhancement)")
            confidence += llm_bonus
        
        final_confidence = min(confidence, 1.0)
        
        if DEBUG:
            debug_log("\n  Confidence Breakdown:", Colors.BOLD + Colors.OKCYAN)
            for item in breakdown:
                debug_log(f"    {item}", Colors.OKCYAN)
            debug_log(f"    {'─'*60}", Colors.OKCYAN)
            debug_log(f"    Total: {final_confidence:.2%}", Colors.BOLD + Colors.OKGREEN)
        
        return final_confidence