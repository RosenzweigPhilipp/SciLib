"""
AI service for smart research field classification.
Analyzes papers and assigns them to 1-3 research field collections.
"""
import logging
from typing import List, Dict, Any
import json
from openai import OpenAI

logger = logging.getLogger(__name__)


class SmartCollectionService:
    """Service for AI-powered research field classification."""
    
    # Common research fields that can be auto-created
    COMMON_FIELDS = [
        "Machine Learning",
        "Natural Language Processing",
        "Computer Vision",
        "Robotics",
        "Quantum Computing",
        "Bioinformatics",
        "Neuroscience",
        "Materials Science",
        "Climate Science",
        "Astrophysics",
        "Molecular Biology",
        "Genetics",
        "Computational Biology",
        "Data Science",
        "Artificial Intelligence",
        "Human-Computer Interaction",
        "Software Engineering",
        "Databases",
        "Distributed Systems",
        "Cryptography",
        "Cybersecurity",
        "Nanotechnology",
        "Drug Discovery",
        "Medical Imaging",
        "Healthcare Informatics",
        "Social Network Analysis",
        "Recommender Systems",
        "Reinforcement Learning",
        "Deep Learning",
        "Cognitive Science",
        "Physics",
        "Chemistry",
        "Mathematics",
        "Statistics",
        "Economics",
        "Psychology",
        "Sociology"
    ]
    
    def __init__(self, openai_api_key: str):
        """Initialize with OpenAI API key."""
        self.client = OpenAI(api_key=openai_api_key)
    
    def classify_paper(self, title: str, abstract: str = None) -> List[Dict[str, str]]:
        """
        Classify a paper into 1-3 research fields with descriptions.
        
        Args:
            title: Paper title
            abstract: Paper abstract (optional but recommended)
            
        Returns:
            List of 1-3 dicts with 'name' and 'description' keys
        """
        try:
            # Build prompt
            text = f"Title: {title}"
            if abstract:
                text += f"\n\nAbstract: {abstract}"
            
            prompt = f"""Analyze this research paper and identify the 1-3 most relevant research fields.

{text}

Choose from these common fields (or suggest closely related ones if none fit):
{', '.join(self.COMMON_FIELDS)}

Return ONLY a JSON array of 1-3 objects with "name" and "description" fields.
Each description should be 1-3 sentences explaining what that research field encompasses.

Example format:
[
  {{"name": "Machine Learning", "description": "Study of algorithms and statistical models that enable computers to learn and improve from experience without explicit programming."}},
  {{"name": "Computer Vision", "description": "Field focused on enabling computers to understand and process visual information from images and videos."}}
]

Ensure fields are general enough to group multiple papers but specific enough to be meaningful.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a research field classification expert. Return only valid JSON arrays with name and description fields."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                fields = json.loads(result_text)
                if isinstance(fields, list) and 1 <= len(fields) <= 3:
                    # Validate structure
                    if all(isinstance(f, dict) and 'name' in f and 'description' in f for f in fields):
                        logger.info(f"Classified paper '{title}' into fields: {[f['name'] for f in fields]}")
                        return fields
                    else:
                        logger.warning(f"Invalid field structure: {fields}")
                        return []
                else:
                    logger.warning(f"Invalid field count: {fields}")
                    return []
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {result_text}")
                return []
                
        except Exception as e:
            logger.error(f"Error classifying paper: {e}")
            return []
    
    def classify_papers_batch(self, papers: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, str]]]:
        """
        Classify multiple papers.
        
        Args:
            papers: List of paper dicts with 'id', 'title', 'abstract'
            
        Returns:
            Dict mapping paper_id to list of research fields
        """
        results = {}
        for paper in papers:
            paper_id = paper.get('id')
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')
            
            if not title:
                logger.warning(f"Skipping paper {paper_id} with no title")
                continue
            
            fields = self.classify_paper(title, abstract)
            if fields:
                results[paper_id] = fields
        
        return results
