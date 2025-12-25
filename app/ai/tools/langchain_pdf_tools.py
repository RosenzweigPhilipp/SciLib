"""
LangChain tool wrappers for PDF extraction functionality.
"""
from langchain.tools import BaseTool
from typing import Dict, Any, Optional
from pydantic import Field
import json
import asyncio

from ..extractors.pdf_extractor import PDFExtractor


class PDFExtractionTool(BaseTool):
    """Tool for extracting text content from PDF files."""
    
    name: str = "pdf_text_extractor"
    description: str = """
    Extract text content from PDF files using multiple methods (direct text, OCR).
    Input: PDF file path as string
    Output: JSON with extracted text, confidence score, and extraction method used
    """
    
    pdf_extractor: PDFExtractor = Field(default_factory=PDFExtractor)
    
    def _run(self, pdf_path: str) -> str:
        """Extract text from PDF synchronously."""
        try:
            result = asyncio.run(self.pdf_extractor.extract_content(pdf_path))
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "text": "", "confidence": 0.0})
    
    async def _arun(self, pdf_path: str) -> str:
        """Extract text from PDF asynchronously."""
        try:
            result = await self.pdf_extractor.extract_content(pdf_path)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "text": "", "confidence": 0.0})


class PDFMetadataTool(BaseTool):
    """Tool for extracting metadata from PDF files."""
    
    name: str = "pdf_metadata_extractor" 
    description: str = """
    Extract metadata and bibliographic information from PDF files.
    Looks for title, authors, abstract, keywords in PDF metadata and text.
    Input: PDF file path as string
    Output: JSON with extracted metadata fields and confidence scores
    """
    
    pdf_extractor: PDFExtractor = Field(default_factory=PDFExtractor)
    
    def _run(self, pdf_path: str) -> str:
        """Extract PDF metadata synchronously."""
        try:
            # Get basic content extraction
            content_result = asyncio.run(self.pdf_extractor.extract_content(pdf_path))
            
            # Enhanced metadata extraction 
            metadata_result = self._extract_metadata_fields(content_result)
            
            return json.dumps(metadata_result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "metadata": {}, "confidence": 0.0})
    
    async def _arun(self, pdf_path: str) -> str:
        """Extract PDF metadata asynchronously."""
        try:
            content_result = await self.pdf_extractor.extract_content(pdf_path)
            metadata_result = self._extract_metadata_fields(content_result)
            
            return json.dumps(metadata_result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "metadata": {}, "confidence": 0.0})
    
    def _extract_metadata_fields(self, content_result: Dict) -> Dict:
        """Extract structured metadata fields from PDF content."""
        text = content_result.get("text", "")
        confidence_base = content_result.get("confidence", 0.0)
        
        metadata = {
            "title": self._extract_title(text),
            "authors": self._extract_authors(text),
            "abstract": self._extract_abstract(text),
            "keywords": self._extract_keywords(text),
            "year": self._extract_year(text),
            "doi": self._extract_doi(text),
            "journal": self._extract_journal(text)
        }
        
        # Calculate field-specific confidence scores
        field_confidences = {}
        for field, value in metadata.items():
            if value:
                field_confidences[f"{field}_confidence"] = min(confidence_base * 1.1, 1.0)
            else:
                field_confidences[f"{field}_confidence"] = 0.0
        
        return {
            "metadata": metadata,
            "field_confidences": field_confidences,
            "overall_confidence": confidence_base,
            "extraction_method": content_result.get("method", "unknown")
        }
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extract paper title from text."""
        lines = text.split('\n')
        
        # Look for title patterns in first few lines
        for i, line in enumerate(lines[:10]):
            line = line.strip()
            if len(line) > 10 and len(line) < 200:  # Reasonable title length
                # Skip obvious non-titles
                if any(skip in line.lower() for skip in [
                    'abstract', 'introduction', 'keywords', 
                    'arxiv:', 'doi:', 'email', '@'
                ]):
                    continue
                
                # Check if it looks like a title
                if (line[0].isupper() and 
                    not line.endswith('.') and 
                    ' ' in line):
                    return line
        
        return None
    
    def _extract_authors(self, text: str) -> Optional[str]:
        """Extract authors from text."""
        lines = text.split('\n')
        
        for i, line in enumerate(lines[:20]):
            line = line.strip()
            
            # Look for author patterns
            if any(pattern in line.lower() for pattern in [
                'author', 'by ', 'et al', '@'
            ]):
                # Clean up the line
                cleaned = line.replace('Authors:', '').replace('By:', '').strip()
                if len(cleaned) > 5 and len(cleaned) < 300:
                    return cleaned
        
        return None
    
    def _extract_abstract(self, text: str) -> Optional[str]:
        """Extract abstract from text."""
        text_lower = text.lower()
        
        # Find abstract section
        abstract_start = text_lower.find('abstract')
        if abstract_start == -1:
            return None
        
        # Get text after "abstract"
        abstract_text = text[abstract_start:]
        
        # Find the end (next section or reasonable length)
        end_markers = [
            '\nintroduction', '\n1.', '\nkeywords', 
            '\nindex terms', '\nreferences'
        ]
        
        end_pos = len(abstract_text)
        for marker in end_markers:
            marker_pos = abstract_text.lower().find(marker)
            if marker_pos != -1 and marker_pos < end_pos:
                end_pos = marker_pos
        
        abstract_content = abstract_text[:end_pos]
        
        # Clean up and extract just the abstract content
        lines = abstract_content.split('\n')
        abstract_lines = []
        
        started = False
        for line in lines:
            line = line.strip()
            if not started and line.lower().startswith('abstract'):
                started = True
                # Skip the "Abstract" line itself
                continue
            elif started and line:
                abstract_lines.append(line)
        
        if abstract_lines:
            return ' '.join(abstract_lines)
        
        return None
    
    def _extract_keywords(self, text: str) -> Optional[str]:
        """Extract keywords from text."""
        text_lower = text.lower()
        
        # Look for keywords section
        keywords_patterns = ['keywords:', 'index terms:', 'key words:']
        
        for pattern in keywords_patterns:
            start_pos = text_lower.find(pattern)
            if start_pos != -1:
                # Get text after keywords marker
                after_keywords = text[start_pos + len(pattern):]
                
                # Find end (next line or section)
                end_pos = after_keywords.find('\n')
                if end_pos == -1:
                    end_pos = min(200, len(after_keywords))  # Max 200 chars
                
                keywords_text = after_keywords[:end_pos].strip()
                if keywords_text:
                    return keywords_text
        
        return None
    
    def _extract_year(self, text: str) -> Optional[str]:
        """Extract publication year from text."""
        import re
        
        # Look for 4-digit years (reasonable range for papers)
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, text[:1000])  # Search first 1000 chars
        
        if years:
            # Return the most reasonable year (prefer recent)
            year_candidates = [int(y) for y in years if 1990 <= int(y) <= 2025]
            if year_candidates:
                return str(max(year_candidates))
        
        return None
    
    def _extract_doi(self, text: str) -> Optional[str]:
        """Extract DOI from text."""
        import re
        
        # DOI pattern
        doi_pattern = r'doi[:\s]*([10]\.\d+/[^\s\]]+)'
        match = re.search(doi_pattern, text.lower())
        
        if match:
            return match.group(1)
        
        # Alternative pattern
        doi_pattern2 = r'(10\.\d+/[^\s\]]+)'
        match2 = re.search(doi_pattern2, text)
        
        if match2:
            return match2.group(1)
        
        return None
    
    def _extract_journal(self, text: str) -> Optional[str]:
        """Extract journal/conference name from text."""
        lines = text.split('\n')
        
        # Look for common journal/conference patterns
        for line in lines[:30]:  # Search first 30 lines
            line = line.strip()
            
            # Journal patterns
            if any(marker in line.lower() for marker in [
                'journal of', 'proceedings of', 'conference on',
                'ieee', 'acm', 'nature', 'science'
            ]):
                # Clean up the line
                if len(line) > 5 and len(line) < 200:
                    return line
        
        return None