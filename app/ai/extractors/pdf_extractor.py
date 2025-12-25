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