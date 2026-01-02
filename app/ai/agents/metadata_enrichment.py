"""
LLM-based metadata enrichment for filling missing BibTeX fields.

This module provides GPT-4o-mini-powered enrichment to fill missing metadata
fields when the LLM has knowledge of the paper. Used alongside summary generation.
"""

import logging
from typing import Dict, Optional, List
from openai import AsyncOpenAI
import json

logger = logging.getLogger(__name__)


class MetadataEnricher:
    """Enriches paper metadata using LLM knowledge."""
    
    def __init__(self, api_key: str):
        """Initialize with OpenAI API key."""
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    async def enrich_metadata(
        self,
        existing_metadata: Dict,
        missing_fields: Optional[List[str]] = None
    ) -> Dict:
        """
        Use LLM to enrich metadata with missing BibTeX fields.
        
        Args:
            existing_metadata: Current metadata (title, authors, year, etc.)
            missing_fields: Specific fields to enrich. If None, checks all BibTeX fields.
        
        Returns:
            Dict with enriched metadata fields
        """
        # Define all BibTeX fields we want to enrich
        bibtex_fields = [
            "publisher", "volume", "issue", "pages", "booktitle", 
            "series", "edition", "isbn", "url", "month", "note", "publication_type"
        ]
        
        # Determine which fields are missing
        if missing_fields is None:
            missing_fields = [
                field for field in bibtex_fields 
                if not existing_metadata.get(field)
            ]
        
        if not missing_fields:
            logger.debug("No missing fields to enrich")
            return {}
        
        # Build context about the paper
        paper_context = self._build_paper_context(existing_metadata)
        
        # Create enrichment prompt
        prompt = self._create_enrichment_prompt(paper_context, missing_fields)
        
        try:
            logger.debug(f"Enriching metadata for: {existing_metadata.get('title', 'Unknown')[:60]}")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a bibliographic metadata expert. Extract accurate publication details from your knowledge of academic papers."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for factual extraction
                response_format={"type": "json_object"}
            )
            
            # Parse LLM response
            enriched_data = json.loads(response.choices[0].message.content)
            
            # Validate and clean enriched data
            validated_data = self._validate_enriched_data(
                enriched_data, 
                missing_fields,
                existing_metadata
            )
            
            logger.debug(f"Enriched {len(validated_data)} fields: {list(validated_data.keys())}")
            return validated_data
            
        except Exception as e:
            logger.error(f"Metadata enrichment failed: {e}")
            return {}
    
    def _build_paper_context(self, metadata: Dict) -> str:
        """Build context string about the paper for LLM."""
        parts = []
        
        if metadata.get("title"):
            parts.append(f"Title: {metadata['title']}")
        
        if metadata.get("authors"):
            parts.append(f"Authors: {metadata['authors']}")
        
        if metadata.get("year"):
            parts.append(f"Year: {metadata['year']}")
        
        if metadata.get("journal"):
            parts.append(f"Journal/Venue: {metadata['journal']}")
        
        if metadata.get("doi"):
            parts.append(f"DOI: {metadata['doi']}")
        
        if metadata.get("abstract"):
            # Truncate abstract to first 300 chars
            abstract = metadata['abstract'][:300]
            if len(metadata['abstract']) > 300:
                abstract += "..."
            parts.append(f"Abstract: {abstract}")
        
        return "\n".join(parts)
    
    def _create_enrichment_prompt(self, paper_context: str, missing_fields: List[str]) -> str:
        """Create enrichment prompt for LLM."""
        
        field_descriptions = {
            "publisher": "The publisher name (e.g., 'Springer', 'IEEE', 'ACM')",
            "volume": "The volume number",
            "issue": "The issue or number",
            "pages": "Page range (e.g., '123-145')",
            "booktitle": "Conference or book title (for conference papers or book chapters)",
            "series": "Book series name",
            "edition": "Edition number",
            "isbn": "ISBN number",
            "url": "Paper URL (prefer DOI URL if available)",
            "month": "Publication month as integer (1-12)",
            "note": "Additional notes or identifiers",
            "publication_type": "BibTeX type: article, inproceedings, book, inbook, phdthesis, etc."
        }
        
        # Build field descriptions for requested fields
        field_prompts = []
        for field in missing_fields:
            if field in field_descriptions:
                field_prompts.append(f"  - {field}: {field_descriptions[field]}")
        
        prompt = f"""I have a paper with the following information:

{paper_context}

Please fill in these missing bibliographic fields if you have knowledge of this paper:
{chr(10).join(field_prompts)}

Important guidelines:
- Only provide information you are confident about
- For unknown fields, use null (not empty strings)
- For 'month', use integer 1-12 (not month name)
- For 'publication_type', use standard BibTeX types
- If this is a conference paper, provide 'booktitle' instead of expanding 'journal'
- Be precise and concise

Return a JSON object with only the requested fields. Example:
{{
  "publisher": "ACM",
  "volume": "42",
  "issue": "3",
  "pages": "123-145",
  "month": 6,
  "publication_type": "article"
}}"""
        
        return prompt
    
    def _validate_enriched_data(
        self, 
        enriched: Dict, 
        requested_fields: List[str],
        existing_metadata: Dict
    ) -> Dict:
        """Validate and clean enriched data."""
        validated = {}
        
        for field in requested_fields:
            value = enriched.get(field)
            
            # Skip null, empty, or "unknown" values
            if value is None or value == "" or str(value).lower() in ["unknown", "n/a", "null"]:
                continue
            
            # Field-specific validation
            if field == "month":
                # Ensure month is integer 1-12
                try:
                    month = int(value)
                    if 1 <= month <= 12:
                        validated["month"] = month
                except (ValueError, TypeError):
                    pass
            
            elif field == "year":
                # Validate year
                try:
                    year = int(value)
                    if 1900 <= year <= 2030:
                        validated["year"] = year
                except (ValueError, TypeError):
                    pass
            
            elif field == "pages":
                # Clean page format (e.g., "123-145" or "e123456")
                pages_str = str(value).strip()
                if pages_str and (
                    "-" in pages_str or  # Range like "123-145"
                    pages_str.startswith("e") or  # Electronic like "e123456"
                    pages_str.isdigit()  # Single page
                ):
                    validated["pages"] = pages_str
            
            elif field == "volume" or field == "issue":
                # Clean volume/issue (could be numeric or alphanumeric)
                vol_str = str(value).strip()
                if vol_str:
                    validated[field] = vol_str
            
            elif field == "isbn":
                # Basic ISBN format check (10 or 13 digits with optional hyphens)
                isbn_str = str(value).replace("-", "").replace(" ", "")
                if len(isbn_str) in [10, 13] and isbn_str.replace("X", "").isdigit():
                    validated["isbn"] = str(value).strip()
            
            elif field == "url":
                # Basic URL validation
                url_str = str(value).strip()
                if url_str.startswith("http://") or url_str.startswith("https://"):
                    validated["url"] = url_str
                # If DOI exists, prefer DOI URL
                elif existing_metadata.get("doi"):
                    validated["url"] = f"https://doi.org/{existing_metadata['doi']}"
            
            elif field == "publication_type":
                # Validate against known BibTeX types
                valid_types = [
                    "article", "inproceedings", "book", "inbook", "incollection",
                    "phdthesis", "mastersthesis", "techreport", "manual", "misc"
                ]
                pub_type = str(value).lower().strip()
                if pub_type in valid_types:
                    validated["publication_type"] = pub_type
            
            else:
                # For other text fields, just clean whitespace
                text_value = str(value).strip()
                if text_value and len(text_value) > 0:
                    validated[field] = text_value
        
        return validated


async def enrich_metadata_with_llm(
    paper_metadata: Dict,
    api_key: str,
    missing_fields: Optional[List[str]] = None
) -> Dict:
    """
    Convenience function to enrich metadata.
    
    Args:
        paper_metadata: Existing paper metadata
        api_key: OpenAI API key
        missing_fields: Optional list of specific fields to enrich
    
    Returns:
        Dict with enriched fields
    """
    enricher = MetadataEnricher(api_key)
    return await enricher.enrich_metadata(paper_metadata, missing_fields)
