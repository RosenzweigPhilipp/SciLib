"""
AI module for SciLib - Scientific Literature Manager

This module provides AI-powered metadata extraction functionality using:
- LangChain agents for orchestrating extraction workflows
- Multiple PDF extraction methods (text + OCR)  
- Scientific APIs (CrossRef, arXiv, Semantic Scholar)
- Semantic web search (Exa.ai)
- Background processing with Celery
- Confidence scoring and validation

Main components:
- agents/: LangChain agent pipeline orchestration
- extractors/: PDF content extraction services  
- tools/: Scientific APIs and search tools
- tasks.py: Celery background task definitions
- endpoints.py: FastAPI routes for AI functionality
"""

__version__ = "1.0.0"
__author__ = "SciLib Team"

# Main exports
from .agents.metadata_pipeline import MetadataExtractionPipeline
from .tasks import extract_pdf_metadata_task, get_extraction_status

__all__ = [
    "MetadataExtractionPipeline",
    "extract_pdf_metadata_task", 
    "get_extraction_status"
]