"""
Summary Service for SciLib

Generates AI summaries for scientific papers using OpenAI's GPT-4o-mini.
Creates multi-level summaries: short overview, detailed summary, and key findings.
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from openai import AsyncOpenAI
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key)

# Constants
SUMMARY_MODEL = "gpt-4o-mini"
MAX_CONTENT_LENGTH = 15000  # Characters for input content


class SummaryService:
    """Service for generating AI summaries of scientific papers"""
    
    @staticmethod
    async def generate_short_summary(title: str, abstract: Optional[str] = None) -> Optional[str]:
        """
        Generate a concise ~50 word summary for quick overview.
        
        Args:
            title: Paper title
            abstract: Paper abstract (optional)
            
        Returns:
            Short summary string or None if generation fails
        """
        if not title:
            logger.warning("Cannot generate summary without title")
            return None
        
        # Build content from available information
        content = f"Title: {title}"
        if abstract and abstract.strip():
            content += f"\n\nAbstract: {abstract}"
        
        prompt = f"""You are a scientific paper summarizer. Generate a concise, easy-to-understand summary in about 50 words.

Paper information:
{content}

Generate a brief summary that explains what this paper is about in simple language that a non-expert can understand. Focus on the main topic and significance.

Summary (50 words):"""

        try:
            response = await client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that explains complex scientific papers in simple, accessible language."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.3  # Lower temperature for more focused summaries
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Generated short summary ({len(summary)} chars)")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate short summary: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    async def generate_detailed_summary(
        title: str, 
        abstract: Optional[str] = None,
        full_text_excerpt: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate a detailed ~200 word summary with more context.
        
        Args:
            title: Paper title
            abstract: Paper abstract (optional)
            full_text_excerpt: Excerpt from paper full text (optional)
            
        Returns:
            Detailed summary string or None if generation fails
        """
        if not title:
            logger.warning("Cannot generate summary without title")
            return None
        
        # Build content from available information
        content = f"Title: {title}"
        if abstract and abstract.strip():
            content += f"\n\nAbstract: {abstract}"
        if full_text_excerpt and full_text_excerpt.strip():
            # Truncate if too long
            if len(full_text_excerpt) > MAX_CONTENT_LENGTH:
                full_text_excerpt = full_text_excerpt[:MAX_CONTENT_LENGTH] + "..."
            content += f"\n\nExcerpt: {full_text_excerpt}"
        
        prompt = f"""You are a scientific paper summarizer. Generate a detailed, accessible summary in about 200 words.

Paper information:
{content}

Generate a comprehensive summary that:
1. Explains the research problem or question
2. Describes the methodology or approach
3. Highlights the main findings or contributions
4. Explains the significance or implications

Write in clear, simple language that makes the research accessible to non-experts while remaining accurate.

Detailed Summary (200 words):"""

        try:
            response = await client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that explains complex scientific research in clear, accessible language while maintaining technical accuracy."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Generated detailed summary ({len(summary)} chars)")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate detailed summary: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    async def generate_eli5_summary(
        title: str,
        abstract: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate an ELI5 (Explain Like I'm 5) summary - very simple explanation.
        
        Args:
            title: Paper title
            abstract: Paper abstract (optional)
            
        Returns:
            ELI5 summary string or None if generation fails
        """
        if not title:
            logger.warning("Cannot generate ELI5 summary without title")
            return None
        
        # Build content from available information
        content = f"Title: {title}"
        if abstract and abstract.strip():
            content += f"\n\nAbstract: {abstract}"
        
        prompt = f"""You are explaining a scientific paper to a 5-year-old child. Use very simple words, fun analogies, and short sentences.

Paper information:
{content}

Explain what this research is about as if you were talking to a curious 5-year-old. Use:
- Very simple everyday words (no technical jargon)
- Fun comparisons to things kids know (toys, animals, games, food)
- Short sentences
- An enthusiastic, friendly tone
- About 50-75 words

ELI5 Explanation:"""

        try:
            response = await client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": "You are a friendly teacher who explains complex scientific concepts to young children using simple words, fun analogies, and an enthusiastic tone."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7  # Slightly higher temperature for more creative analogies
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Generated ELI5 summary ({len(summary)} chars)")
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate ELI5 summary: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    async def extract_key_findings(
        title: str,
        abstract: Optional[str] = None,
        full_text_excerpt: Optional[str] = None
    ) -> Optional[List[str]]:
        """
        Extract key findings as bullet points.
        
        Args:
            title: Paper title
            abstract: Paper abstract (optional)
            full_text_excerpt: Excerpt from paper full text (optional)
            
        Returns:
            List of key findings or None if extraction fails
        """
        if not title:
            logger.warning("Cannot extract findings without title")
            return None
        
        # Build content
        content = f"Title: {title}"
        if abstract and abstract.strip():
            content += f"\n\nAbstract: {abstract}"
        if full_text_excerpt and full_text_excerpt.strip():
            if len(full_text_excerpt) > MAX_CONTENT_LENGTH:
                full_text_excerpt = full_text_excerpt[:MAX_CONTENT_LENGTH] + "..."
            content += f"\n\nExcerpt: {full_text_excerpt}"
        
        prompt = f"""You are a scientific paper analyzer. Extract 3-5 key findings or contributions from this paper.

Paper information:
{content}

Extract the most important findings, contributions, or insights from this research. Each finding should be:
- Clear and concise (one sentence)
- Specific and actionable
- Understandable to non-experts

Format your response as a JSON array of strings, like this:
["First key finding", "Second key finding", "Third key finding"]

Key Findings:"""

        try:
            response = await client.chat.completions.create(
                model=SUMMARY_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts key insights from scientific papers. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                # Try direct array parse
                findings = json.loads(content)
                if isinstance(findings, dict) and "findings" in findings:
                    findings = findings["findings"]
                elif isinstance(findings, dict) and "key_findings" in findings:
                    findings = findings["key_findings"]
                
                if isinstance(findings, list):
                    logger.info(f"Extracted {len(findings)} key findings")
                    return findings
                else:
                    logger.warning(f"Unexpected findings format: {type(findings)}")
                    return None
                    
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse findings JSON: {e}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to extract key findings: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    async def generate_complete_summary(
        title: str,
        abstract: Optional[str] = None,
        full_text_excerpt: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[List[str]], Optional[str]]:
        """
        Generate all summary components in parallel for efficiency.
        
        Args:
            title: Paper title
            abstract: Paper abstract (optional)
            full_text_excerpt: Excerpt from paper full text (optional)
            
        Returns:
            Tuple of (short_summary, detailed_summary, key_findings, eli5_summary)
        """
        import asyncio
        
        # Run all four generation tasks in parallel
        results = await asyncio.gather(
            SummaryService.generate_short_summary(title, abstract),
            SummaryService.generate_detailed_summary(title, abstract, full_text_excerpt),
            SummaryService.extract_key_findings(title, abstract, full_text_excerpt),
            SummaryService.generate_eli5_summary(title, abstract),
            return_exceptions=True
        )
        
        # Extract results, handling any exceptions
        short_summary = results[0] if not isinstance(results[0], Exception) else None
        detailed_summary = results[1] if not isinstance(results[1], Exception) else None
        key_findings = results[2] if not isinstance(results[2], Exception) else None
        eli5_summary = results[3] if not isinstance(results[3], Exception) else None
        
        return short_summary, detailed_summary, key_findings, eli5_summary


# Convenience functions
async def generate_paper_summary(
    title: str,
    abstract: Optional[str] = None,
    full_text_excerpt: Optional[str] = None
) -> Dict[str, any]:
    """
    Generate all summaries for a paper.
    
    Returns dict with keys: short_summary, detailed_summary, key_findings, eli5_summary
    """
    short, detailed, findings, eli5 = await SummaryService.generate_complete_summary(
        title, abstract, full_text_excerpt
    )
    
    return {
        "short_summary": short,
        "detailed_summary": detailed,
        "key_findings": findings,
        "eli5_summary": eli5
    }
