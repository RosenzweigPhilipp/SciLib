"""
PDF content extraction service with text and OCR capabilities.
"""
import fitz  # PyMuPDF
import pdfplumber
import pytesseract
from PIL import Image
from typing import Dict, Optional, List
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extracts text and metadata from PDF files using multiple methods."""
    
    def __init__(self, max_ocr_pages: int = 10):
        self.max_ocr_pages = max_ocr_pages
    
    def extract_content(self, pdf_path: str) -> Dict:
        """
        Extract comprehensive content from PDF.
        
        Returns:
            Dict with extracted text, metadata, and extraction method used
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        result = {
            "text": "",
            "metadata": {},
            "method": "unknown",
            "page_count": 0,
            "confidence": 0.0,
            "error": None
        }
        
        try:
            # Try text extraction first (fastest)
            text_result = self._extract_text(str(pdf_path))
            
            if text_result["text"].strip() and len(text_result["text"]) > 100:
                # Good text extraction
                result.update(text_result)
                result["method"] = "text_extraction"
                result["confidence"] = 0.9
            else:
                # Fallback to OCR for scanned documents
                logger.info(f"Text extraction yielded little content, trying OCR for {pdf_path}")
                ocr_result = self._extract_with_ocr(str(pdf_path))
                result.update(ocr_result)
                result["method"] = "ocr"
                result["confidence"] = 0.7
                
        except Exception as e:
            logger.error(f"PDF extraction failed for {pdf_path}: {e}")
            result["error"] = str(e)
            result["confidence"] = 0.0
        
        return result
    
    def _extract_text(self, pdf_path: str) -> Dict:
        """Extract text using PyMuPDF and pdfplumber."""
        text = ""
        metadata = {}
        page_count = 0
        
        try:
            # Try PyMuPDF first (fastest)
            with fitz.open(pdf_path) as doc:
                page_count = len(doc)
                metadata = dict(doc.metadata) if doc.metadata else {}
                
                # Extract text from all pages
                for page in doc:
                    page_text = page.get_text()
                    if page_text.strip():
                        text += page_text + "\n"
            
            # If PyMuPDF didn't get much text, try pdfplumber
            if len(text.strip()) < 100:
                try:
                    with pdfplumber.open(pdf_path) as pdf:
                        for page in pdf.pages[:5]:  # First 5 pages for speed
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                except Exception as e:
                    logger.warning(f"pdfplumber extraction failed: {e}")
            
        except Exception as e:
            raise Exception(f"Text extraction failed: {e}")
        
        return {
            "text": text.strip(),
            "metadata": metadata,
            "page_count": page_count
        }
    
    def _extract_with_ocr(self, pdf_path: str) -> Dict:
        """Extract text using OCR for scanned documents."""
        text = ""
        page_count = 0
        
        try:
            with fitz.open(pdf_path) as doc:
                page_count = len(doc)
                
                # Limit OCR to first few pages for speed
                pages_to_process = min(self.max_ocr_pages, page_count)
                
                for page_num in range(pages_to_process):
                    page = doc[page_num]
                    
                    # Convert page to image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Perform OCR
                    try:
                        page_text = pytesseract.image_to_string(img, lang='eng')
                        if page_text.strip():
                            text += page_text + "\n"
                    except Exception as e:
                        logger.warning(f"OCR failed for page {page_num}: {e}")
                        continue
                
        except Exception as e:
            raise Exception(f"OCR extraction failed: {e}")
        
        return {
            "text": text.strip(),
            "metadata": {},
            "page_count": page_count
        }
    
    def get_first_page_text(self, pdf_path: str, max_chars: int = 2000) -> str:
        """Get text from first page only (for quick metadata extraction)."""
        try:
            with fitz.open(pdf_path) as doc:
                if len(doc) > 0:
                    first_page = doc[0]
                    text = first_page.get_text()
                    return text[:max_chars] if text else ""
        except Exception as e:
            logger.error(f"Failed to extract first page text: {e}")
        
        return ""
    
    def extract_basic_metadata(self, pdf_path: str) -> Dict:
        """
        Extract basic metadata (title, authors, DOI) directly from PDF without LLM.
        Uses PDF metadata and first-page heuristics.
        
        Returns:
            Dict with title, authors, doi if found
        """
        result = {
            "title": None,
            "authors": None,
            "doi": None,
            "method": "direct_extraction"
        }
        
        try:
            with fitz.open(pdf_path) as doc:
                # Try PDF metadata first
                if doc.metadata:
                    if doc.metadata.get("title") and len(doc.metadata.get("title", "").strip()) > 5:
                        result["title"] = doc.metadata["title"].strip()
                    if doc.metadata.get("author") and len(doc.metadata.get("author", "").strip()) > 3:
                        result["authors"] = doc.metadata["author"].strip()
                
                # If no metadata, try extracting from first page
                if not result["title"] and len(doc) > 0:
                    first_page_text = doc[0].get_text()
                    
                    # Extract title (usually first large text block)
                    if first_page_text:
                        lines = [line.strip() for line in first_page_text.split('\n') if line.strip()]
                        if lines:
                            # Title is typically the first substantial line after headers
                            title_candidates = []
                            skip_keywords = [
                                'university', 'institute', 'department', 'faculty',
                                'college', 'school', 'center', 'centre', 'laboratory', 'email',
                                '@', 'www.', 'http', '.edu', '.com', '.org', '.ac.uk',
                                'short papers', 'conference', 'proceedings', 
                                'volume', 'issue', 'pp.', 'pages', 'page ',
                                'ieee', 'acm', 'springer', 'elsevier',
                                'transactions', 'journal of', 'letters', 'practice',
                                'copyright', '©', 'published', 'received',
                                'contents lists', 'sciencedirect', 'available at',
                                'journal homepage', 'preprint', 'submitted'
                            ]
                            
                            for i, line in enumerate(lines[:20]):  # Check first 20 lines
                                # Skip very short lines or very long lines (likely not titles)
                                if len(line) < 15 or len(line) > 150:
                                    continue
                                    
                                # Skip pure numbers or page numbers
                                if re.match(r'^\d+\s*$', line):
                                    continue
                                
                                # Skip lines that look like journal citations (e.g., "Journal Name 80 (2018) 83-93")
                                if re.search(r'\d+\s*\(\d{4}\)\s*\d+[-–]\d+', line):
                                    continue
                                    
                                # Skip lines with journal/conference markers
                                if any(marker in line.lower() for marker in skip_keywords):
                                    continue
                                    
                                # Skip lines with numbers at the start (likely author refs or page numbers)
                                if re.match(r'^\d+[A-Z]', line):
                                    continue
                                    
                                # Skip lines with lots of commas (likely author lists)
                                if line.count(',') > 3:
                                    continue
                                    
                                # Skip very short uppercase lines (likely section headers like "Abstract")
                                if len(line) < 30 and line.isupper():
                                    continue
                                
                                # Skip lines that end with dates (like "OCTOBER 1969")
                                if re.search(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}\b', line, re.IGNORECASE):
                                    continue
                                
                                # Skip lines with special markers like ✩ or * at the end (footnote markers)
                                if re.search(r'[✩★*†‡§]$', line):
                                    continue
                                
                                # Check if next line continues the title
                                potential_title = line
                                if i + 1 < len(lines):
                                    next_line = lines[i + 1].strip()
                                    # If next line looks like a continuation (reasonable length, not author name pattern)
                                    if next_line and 5 < len(next_line) < 100:
                                        # Check for footnote marker at the end
                                        has_footnote = re.search(r'[✩★*†‡§]$', next_line)
                                        if has_footnote:
                                            # Remove the marker and include the line
                                            next_line = re.sub(r'[✩★*†‡§]$', '', next_line).strip()
                                        
                                        # Not an author line (doesn't have patterns like "NAME, IEEE" or multiple commas)
                                        if (next_line.count(',') <= 1 and 
                                            not re.search(r'[A-Z][A-Z\s\.]+,\s*(MEMBER|SENIOR|FELLOW|IEEE|ACM)', next_line, re.IGNORECASE) and
                                            not any(marker in next_line.lower() for marker in skip_keywords)):
                                            # Check if it starts with lowercase (definitely continuation) or looks like title text
                                            if next_line[0].islower() or (next_line[0].isupper() and not next_line.isupper()):
                                                potential_title += " " + next_line
                                
                                # This looks like a potential title
                                title_candidates.append(potential_title)
                                if len(title_candidates) >= 1:  # Take first good candidate
                                    break
                            
                            if title_candidates:
                                # Use the first good candidate
                                result["title"] = title_candidates[0]
                
                # Extract DOI from first page (regardless of whether title was found)
                if len(doc) > 0 and not result.get("doi"):
                    # Always extract first page text for DOI search
                    doi_page_text = doc[0].get_text()
                    
                    if doi_page_text:
                        # Extract DOI using regex
                        doi_patterns = [
                            r'(?:doi:?\s*)(10\.\d{4,}/[^\s]+)',
                            r'(?:DOI:?\s*)(10\.\d{4,}/[^\s]+)',
                            r'\b(10\.\d{4,}/[^\s\]<>]+)'
                        ]
                        
                        text_to_search = doi_page_text[:8000]  # Increased from 3000 to capture DOIs near end of page
                        for pattern in doi_patterns:
                            match = re.search(pattern, text_to_search, re.IGNORECASE)
                            if match:
                                result["doi"] = match.group(1).rstrip('.')
                                break
                
        except Exception as e:
            logger.error(f"Failed to extract basic metadata: {e}")
        
        return result