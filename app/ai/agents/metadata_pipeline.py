"""
LangChain agents for scientific paper metadata extraction pipeline.
"""
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import BaseTool
from typing import Dict, List, Optional, Any
import json
import logging

logger = logging.getLogger(__name__)


class MetadataExtractionPipeline:
    """
    Orchestrates the multi-agent pipeline for PDF metadata extraction.
    
    Pipeline:
    1. PDF Extraction Agent -> Extract text/metadata from PDF
    2. Metadata Search Agent -> Find additional metadata via APIs/web search  
    3. Validation Agent -> Validate and merge results
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
        
        # Initialize tools
        self.pdf_tools = self._create_pdf_tools()
        self.search_tools = self._create_search_tools(
            exa_api_key, crossref_email, semantic_scholar_key
        )
        self.validation_tools = self._create_validation_tools()
        
        # Create agents
        self.pdf_agent = self._create_pdf_agent()
        self.search_agent = self._create_search_agent()  
        self.validation_agent = self._create_validation_agent()
    
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
            pdf_result = await self._run_pdf_extraction(pdf_path)
            pipeline_result["sources"].append("pdf_extraction")
            
            if not pdf_result.get("text"):
                pipeline_result["errors"].append("Failed to extract text from PDF")
                pipeline_result["extraction_status"] = "failed"
                return pipeline_result
            
            # Step 2: Metadata Search & Enrichment
            logger.info(f"Starting metadata search for paper {paper_id}")
            search_result = await self._run_metadata_search(pdf_result)
            pipeline_result["sources"].extend(search_result.get("sources", []))
            
            # Step 3: Validation & Merging
            logger.info(f"Starting validation for paper {paper_id}")
            validation_result = await self._run_validation(pdf_result, search_result)
            
            # Compile final result
            pipeline_result.update({
                "extraction_status": "completed",
                "confidence": validation_result.get("confidence", 0.0),
                "metadata": validation_result.get("metadata", {}),
                "sources": list(set(pipeline_result["sources"] + validation_result.get("sources", [])))
            })
            
            logger.info(f"Pipeline completed for paper {paper_id} with confidence {pipeline_result['confidence']}")
            
        except Exception as e:
            logger.error(f"Pipeline failed for paper {paper_id}: {e}")
            pipeline_result.update({
                "extraction_status": "failed",
                "errors": [str(e)]
            })
        
        return pipeline_result
    
    async def _run_pdf_extraction(self, pdf_path: str) -> Dict:
        """Run PDF extraction agent."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert PDF analysis agent. Your job is to extract and analyze content from academic papers.

Extract the following information from the PDF:
1. Title (exact title of the paper)
2. Authors (full author list)
3. Abstract (if available)
4. Year/Publication date
5. Journal/Conference name
6. DOI (if present)
7. Keywords (if available)

Return results in JSON format with confidence scores for each field.
Be precise and only extract information you are confident about.
"""),
            ("human", "Analyze this PDF and extract academic paper metadata: {pdf_path}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_tools_agent(self.llm, self.pdf_tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=self.pdf_tools, verbose=True)
        
        result = await agent_executor.ainvoke({"pdf_path": pdf_path})
        return result
    
    async def _run_metadata_search(self, pdf_result: Dict) -> Dict:
        """Run metadata search agent."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a metadata search specialist. Use scientific APIs and web search to find complete bibliographic information.

Your goal is to find missing metadata for academic papers using:
1. CrossRef API for DOI lookup and citation data
2. ArXiv API for preprint information
3. Semantic Scholar API for additional metadata
4. Exa.ai semantic search as fallback

Prioritize official sources over web search. Return comprehensive BibTeX-ready metadata.
"""),
            ("human", "Find complete metadata for this paper: {extracted_info}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_tools_agent(self.llm, self.search_tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=self.search_tools, verbose=True)
        
        result = await agent_executor.ainvoke({"extracted_info": json.dumps(pdf_result)})
        return result
    
    async def _run_validation(self, pdf_result: Dict, search_result: Dict) -> Dict:
        """Run validation agent."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a data validation expert. Your job is to merge and validate metadata from multiple sources.

Compare information from:
1. PDF extraction results
2. API search results

Rules:
- Prefer official sources (CrossRef, ArXiv) over web search
- Cross-validate conflicting information
- Assign confidence scores based on source reliability
- Generate complete BibTeX entry
- Flag any inconsistencies

Return final validated metadata with confidence scores.
"""),
            ("human", "Validate and merge these results:\nPDF: {pdf_data}\nSearch: {search_data}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        agent = create_openai_tools_agent(self.llm, self.validation_tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=self.validation_tools, verbose=True)
        
        result = await agent_executor.ainvoke({
            "pdf_data": json.dumps(pdf_result),
            "search_data": json.dumps(search_result)
        })
        return result
    
    def _create_pdf_agent(self):
        """Create PDF extraction agent."""
        # Will be implemented with the tools
        pass
    
    def _create_search_agent(self):
        """Create metadata search agent."""
        pass
    
    def _create_validation_agent(self):
        """Create validation agent."""
        pass
    
    def _create_pdf_tools(self) -> List[BaseTool]:
        """Create tools for PDF content extraction."""
        from .tools.langchain_pdf_tools import PDFExtractionTool, PDFMetadataTool
        
        return [
            PDFExtractionTool(),
            PDFMetadataTool()
        ]
    
    def _create_search_tools(self, exa_key: Optional[str], crossref_email: Optional[str], 
                           semantic_scholar_key: Optional[str]) -> List[BaseTool]:
        """Create tools for metadata search."""
        from .tools.langchain_search_tools import (
            CrossRefSearchTool, ArxivSearchTool, SemanticScholarSearchTool, ExaSearchTool
        )
        
        tools = [
            CrossRefSearchTool(email=crossref_email),
            ArxivSearchTool(),
        ]
        
        if semantic_scholar_key:
            tools.append(SemanticScholarSearchTool(api_key=semantic_scholar_key))
        
        if exa_key:
            tools.append(ExaSearchTool(api_key=exa_key))
        
        return tools
    
    def _create_validation_tools(self) -> List[BaseTool]:
        """Create tools for validation and merging."""
        from .tools.langchain_validation_tools import (
            MetadataMergeTool, ConfidenceScoringTool, BibtexGeneratorTool
        )
        
        return [
            MetadataMergeTool(),
            ConfidenceScoringTool(),
            BibtexGeneratorTool()
        ]