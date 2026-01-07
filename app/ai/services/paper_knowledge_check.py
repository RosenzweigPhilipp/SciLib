"""
Service to check if an LLM has knowledge of a paper in its training data.
"""
import os
from typing import Optional, Dict
from openai import OpenAI


class PaperKnowledgeService:
    """Check if LLM knows about a paper and can provide summaries."""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def check_paper_knowledge(
        self, 
        title: str, 
        authors: Optional[str] = None,
        year: Optional[int] = None,
        doi: Optional[str] = None
    ) -> Dict:
        """
        Ask the LLM if it has knowledge of the paper.
        
        Returns:
            {
                "has_knowledge": bool,
                "confidence": float (0.0-1.0),
                "brief_summary": str (if has_knowledge),
                "explanation": str
            }
        """
        if not title:
            return {
                "has_knowledge": False,
                "confidence": 0.0,
                "explanation": "No title provided"
            }
        
        # Construct query with available metadata
        query_parts = [f"Title: {title}"]
        if authors:
            query_parts.append(f"Authors: {authors}")
        if year:
            query_parts.append(f"Year: {year}")
        if doi:
            query_parts.append(f"DOI: {doi}")
        
        paper_info = "\n".join(query_parts)
        
        prompt = f"""You are a research assistant. I need to know if you have knowledge of the following academic paper in your training data:

{paper_info}

Please respond in JSON format with:
1. "has_knowledge": true/false - Do you recognize this paper?
2. "confidence": 0.0-1.0 - How confident are you?
3. "brief_summary": A 2-3 sentence summary (only if has_knowledge is true)
4. "explanation": Brief explanation of your answer

Only respond with the JSON object, no other text."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            import json
            result = json.loads(response.choices[0].message.content.strip())
            
            return {
                "has_knowledge": result.get("has_knowledge", False),
                "confidence": result.get("confidence", 0.0),
                "brief_summary": result.get("brief_summary", ""),
                "explanation": result.get("explanation", "")
            }
            
        except Exception as e:
            return {
                "has_knowledge": False,
                "confidence": 0.0,
                "explanation": f"Error checking paper knowledge: {str(e)}"
            }
    
    def generate_summaries_from_knowledge(
        self,
        title: str,
        authors: Optional[str] = None,
        year: Optional[int] = None
    ) -> Dict:
        """
        Generate comprehensive summaries using LLM's existing knowledge.
        
        Returns dict with short_summary, long_summary, key_findings, eli5_summary
        """
        paper_info = f"Title: {title}"
        if authors:
            paper_info += f"\nAuthors: {authors}"
        if year:
            paper_info += f"\nYear: {year}"
        
        prompt = f"""Based on your training data knowledge of this paper:

{paper_info}

Please provide:
1. A short summary (2-3 sentences)
2. A detailed summary (1 paragraph, 5-7 sentences)
3. 3-5 key findings as a list
4. An ELI5 (Explain Like I'm 5) summary - explain the paper as if talking to a curious 5-year-old using very simple words, fun analogies to things kids know (toys, animals, games, food), short sentences, and an enthusiastic friendly tone (50-75 words)

Format your response as JSON with keys: "short_summary", "long_summary", "key_findings" (array), "eli5_summary"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful research assistant. Provide accurate summaries based on your training data. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=800,
                response_format={"type": "json_object"}
            )
            
            import json
            content = response.choices[0].message.content.strip()
            result = json.loads(content)
            
            # Ensure all fields exist
            short = result.get("short_summary", "") or result.get("short", "")
            long = result.get("long_summary", "") or result.get("detailed_summary", "")
            findings = result.get("key_findings", [])
            eli5 = result.get("eli5_summary", "") or result.get("eli5", "")
            
            # Convert findings to list if it's a string or dict
            if isinstance(findings, str):
                findings = [findings]
            elif isinstance(findings, dict):
                findings = list(findings.values())
            
            return {
                "short_summary": short,
                "long_summary": long,
                "key_findings": findings if isinstance(findings, list) else [],
                "eli5_summary": eli5
            }
            
        except Exception as e:
            return {
                "error": f"Failed to generate summaries: {str(e)}"
            }
