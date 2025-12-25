"""
LangChain tool wrappers for metadata validation and merging functionality.
"""
from langchain_core.tools import BaseTool
from typing import Dict, Any, Optional, List
from pydantic import Field
import json
import re
from datetime import datetime


class MetadataMergeTool(BaseTool):
    """Tool for merging metadata from multiple sources."""
    
    name: str = "metadata_merger"
    description: str = """
    Merge and consolidate metadata from multiple sources (PDF extraction, APIs, web search).
    Resolves conflicts by prioritizing more reliable sources and cross-validating information.
    Input: JSON with multiple metadata sources
    Output: JSON with merged metadata and conflict resolution notes
    """
    
    def _run(self, metadata_sources: str) -> str:
        """Merge metadata sources synchronously."""
        try:
            sources = json.loads(metadata_sources)
            merged = self._merge_metadata(sources)
            return json.dumps(merged, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "merged_metadata": {}})
    
    async def _arun(self, metadata_sources: str) -> str:
        """Merge metadata sources asynchronously."""
        return self._run(metadata_sources)
    
    def _merge_metadata(self, sources: Dict) -> Dict:
        """Merge metadata from multiple sources with conflict resolution."""
        
        # Source reliability ranking
        source_reliability = {
            "crossref": 5,
            "semantic_scholar": 4,
            "arxiv": 3,
            "pdf_extraction": 2,
            "exa": 1
        }
        
        merged = {
            "title": None,
            "authors": None,
            "abstract": None,
            "year": None,
            "journal": None,
            "doi": None,
            "keywords": None,
            "url": None,
            "pdf_url": None,
            "bibtex_type": "article"  # Default
        }
        
        conflicts = {}
        source_tracking = {}
        
        # Process each field
        for field in merged.keys():
            if field == "bibtex_type":
                continue
                
            candidates = []
            
            # Collect candidates from all sources
            for source_name, source_data in sources.items():
                if isinstance(source_data, dict):
                    value = self._extract_field_value(source_data, field)
                    if value:
                        reliability = source_reliability.get(
                            source_name.lower().replace(" ", "_"), 0
                        )
                        candidates.append({
                            "value": value,
                            "source": source_name,
                            "reliability": reliability
                        })
            
            # Resolve conflicts and select best value
            if candidates:
                best_candidate = self._resolve_field_conflicts(field, candidates)
                merged[field] = best_candidate["value"]
                source_tracking[field] = best_candidate["source"]
                
                # Track conflicts if multiple candidates exist
                if len(candidates) > 1:
                    conflicts[field] = [
                        {"value": c["value"], "source": c["source"]} 
                        for c in candidates
                    ]
        
        # Determine BibTeX type based on available metadata
        merged["bibtex_type"] = self._determine_bibtex_type(merged)
        
        return {
            "merged_metadata": merged,
            "source_tracking": source_tracking,
            "conflicts": conflicts,
            "merge_timestamp": datetime.now().isoformat()
        }
    
    def _extract_field_value(self, source_data: Dict, field: str) -> Optional[str]:
        """Extract field value from source data with various key patterns."""
        
        # Direct field mapping
        if field in source_data:
            return self._clean_field_value(source_data[field])
        
        # Alternative key patterns
        field_mappings = {
            "title": ["title", "paper_title", "name"],
            "authors": ["authors", "author", "creators", "author_list"],
            "abstract": ["abstract", "summary", "description"],
            "year": ["year", "publication_year", "pub_year", "date"],
            "journal": ["journal", "venue", "publisher", "publication", "container-title"],
            "doi": ["doi", "DOI"],
            "keywords": ["keywords", "tags", "subjects"],
            "url": ["url", "link", "external_url"],
            "pdf_url": ["pdf_url", "pdf_link", "download_url"]
        }
        
        for alt_key in field_mappings.get(field, []):
            if alt_key in source_data:
                value = source_data[alt_key]
                if value:
                    return self._clean_field_value(value)
        
        # Handle nested metadata
        if "metadata" in source_data and isinstance(source_data["metadata"], dict):
            nested_value = self._extract_field_value(source_data["metadata"], field)
            if nested_value:
                return nested_value
        
        return None
    
    def _clean_field_value(self, value: Any) -> Optional[str]:
        """Clean and normalize field values."""
        if not value:
            return None
        
        # Handle lists (e.g., multiple authors)
        if isinstance(value, list):
            if all(isinstance(item, str) for item in value):
                return "; ".join(str(item).strip() for item in value if item)
            else:
                return str(value[0]) if value else None
        
        # Handle strings
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        
        # Convert other types to string
        return str(value).strip()
    
    def _resolve_field_conflicts(self, field: str, candidates: List[Dict]) -> Dict:
        """Resolve conflicts between different sources for the same field."""
        
        if len(candidates) == 1:
            return candidates[0]
        
        # Sort by reliability first
        candidates.sort(key=lambda x: x["reliability"], reverse=True)
        
        # Field-specific conflict resolution
        if field == "title":
            return self._resolve_title_conflicts(candidates)
        elif field == "authors":
            return self._resolve_authors_conflicts(candidates)
        elif field == "year":
            return self._resolve_year_conflicts(candidates)
        elif field == "doi":
            return self._resolve_doi_conflicts(candidates)
        else:
            # Default: take highest reliability source
            return candidates[0]
    
    def _resolve_title_conflicts(self, candidates: List[Dict]) -> Dict:
        """Resolve title conflicts by choosing the most complete version."""
        
        # Prefer longer, more complete titles
        candidates.sort(key=lambda x: (x["reliability"], len(x["value"])), reverse=True)
        
        # Check for obvious truncations or abbreviations
        best = candidates[0]
        for candidate in candidates[1:]:
            title1 = best["value"].lower()
            title2 = candidate["value"].lower()
            
            # If one title contains the other, prefer the longer one
            if title2 in title1 and len(title1) > len(title2):
                continue  # Keep best
            elif title1 in title2 and len(title2) > len(title1):
                best = candidate
        
        return best
    
    def _resolve_authors_conflicts(self, candidates: List[Dict]) -> Dict:
        """Resolve author conflicts by merging or choosing most complete."""
        
        # Prefer sources with more complete author information
        def author_completeness(authors_str: str) -> int:
            # Count number of authors and check for first names
            authors = authors_str.split(";")
            score = len(authors)
            
            # Bonus for full names (not just initials)
            for author in authors:
                if any(part.lower() not in ["and", "et", "al"] and len(part.strip()) > 2 
                      for part in author.split()):
                    score += 1
            
            return score
        
        candidates.sort(
            key=lambda x: (x["reliability"], author_completeness(x["value"])),
            reverse=True
        )
        
        return candidates[0]
    
    def _resolve_year_conflicts(self, candidates: List[Dict]) -> Dict:
        """Resolve year conflicts by validating reasonable publication years."""
        
        valid_candidates = []
        current_year = datetime.now().year
        
        for candidate in candidates:
            try:
                year = int(re.findall(r'\d{4}', candidate["value"])[0])
                # Reasonable publication year range
                if 1950 <= year <= current_year + 2:
                    candidate["parsed_year"] = year
                    valid_candidates.append(candidate)
            except (ValueError, IndexError):
                continue
        
        if not valid_candidates:
            return candidates[0]  # Fallback to reliability
        
        # Sort by reliability, then prefer more recent years
        valid_candidates.sort(
            key=lambda x: (x["reliability"], x["parsed_year"]),
            reverse=True
        )
        
        return valid_candidates[0]
    
    def _resolve_doi_conflicts(self, candidates: List[Dict]) -> Dict:
        """Resolve DOI conflicts by validating DOI format."""
        
        doi_pattern = r'10\.\d+/[^\s\]]+$'
        
        valid_candidates = []
        for candidate in candidates:
            # Clean DOI
            doi = candidate["value"].lower()
            doi = re.sub(r'^(doi:?\s*)', '', doi)  # Remove "doi:" prefix
            
            if re.match(doi_pattern, doi):
                candidate["cleaned_doi"] = doi
                valid_candidates.append(candidate)
        
        if not valid_candidates:
            return candidates[0]  # Fallback
        
        # Sort by reliability
        valid_candidates.sort(key=lambda x: x["reliability"], reverse=True)
        return valid_candidates[0]
    
    def _determine_bibtex_type(self, metadata: Dict) -> str:
        """Determine appropriate BibTeX entry type based on metadata."""
        
        journal = metadata.get("journal", "").lower()
        
        # Conference patterns
        if any(pattern in journal for pattern in [
            "conference", "proceedings", "workshop", "symposium",
            "ieee", "acm", "icml", "nips", "iclr"
        ]):
            return "inproceedings"
        
        # arXiv preprints
        if "arxiv" in journal or metadata.get("url", "").find("arxiv") != -1:
            return "misc"
        
        # Default to article
        return "article"


class ConfidenceScoringTool(BaseTool):
    """Tool for calculating confidence scores for extracted metadata."""
    
    name: str = "confidence_scorer"
    description: str = """
    Calculate confidence scores for extracted metadata based on source reliability,
    field completeness, cross-validation, and data quality indicators.
    Input: JSON with merged metadata and source information
    Output: JSON with detailed confidence scores and quality assessment
    """
    
    def _run(self, merged_metadata: str) -> str:
        """Calculate confidence scores synchronously."""
        try:
            data = json.loads(merged_metadata)
            scores = self._calculate_confidence_scores(data)
            return json.dumps(scores, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e), "confidence_scores": {}})
    
    async def _arun(self, merged_metadata: str) -> str:
        """Calculate confidence scores asynchronously."""
        return self._run(merged_metadata)
    
    def _calculate_confidence_scores(self, data: Dict) -> Dict:
        """Calculate comprehensive confidence scores."""
        
        metadata = data.get("merged_metadata", {})
        source_tracking = data.get("source_tracking", {})
        conflicts = data.get("conflicts", {})
        
        # Field importance weights
        field_weights = {
            "title": 0.25,
            "authors": 0.20,
            "year": 0.15,
            "journal": 0.10,
            "doi": 0.10,
            "abstract": 0.10,
            "keywords": 0.05,
            "url": 0.05
        }
        
        field_scores = {}
        overall_score = 0.0
        
        for field, weight in field_weights.items():
            field_score = self._calculate_field_confidence(
                field, metadata.get(field), source_tracking.get(field),
                conflicts.get(field, [])
            )
            
            field_scores[field] = field_score
            overall_score += field_score * weight
        
        # Quality indicators
        quality_indicators = self._assess_quality_indicators(metadata, conflicts)
        
        # Adjust overall score based on quality
        quality_adjustment = quality_indicators["quality_score"] * 0.1
        final_score = min(overall_score + quality_adjustment, 1.0)
        
        return {
            "overall_confidence": round(final_score, 3),
            "field_confidence": {k: round(v, 3) for k, v in field_scores.items()},
            "quality_indicators": quality_indicators,
            "recommendation": self._generate_recommendation(final_score, quality_indicators)
        }
    
    def _calculate_field_confidence(self, field: str, value: Any, source: str, conflicts: List) -> float:
        """Calculate confidence for a specific field."""
        
        if not value:
            return 0.0
        
        confidence = 0.0
        
        # Source reliability
        source_scores = {
            "crossref": 0.9,
            "semantic_scholar": 0.8,
            "arxiv": 0.7,
            "pdf_extraction": 0.6,
            "exa": 0.5
        }
        
        source_key = source.lower().replace(" ", "_") if source else "unknown"
        confidence += source_scores.get(source_key, 0.3)
        
        # Field-specific validation
        validation_score = self._validate_field_content(field, value)
        confidence *= validation_score
        
        # Conflict penalty
        if conflicts:
            conflict_penalty = min(len(conflicts) * 0.1, 0.3)
            confidence -= conflict_penalty
        
        return max(confidence, 0.0)
    
    def _validate_field_content(self, field: str, value: str) -> float:
        """Validate field content quality and format."""
        
        if field == "title":
            return self._validate_title(value)
        elif field == "authors":
            return self._validate_authors(value)
        elif field == "year":
            return self._validate_year(value)
        elif field == "doi":
            return self._validate_doi(value)
        elif field == "journal":
            return self._validate_journal(value)
        else:
            return 1.0 if value else 0.0
    
    def _validate_title(self, title: str) -> float:
        """Validate title quality."""
        if not title:
            return 0.0
        
        score = 1.0
        
        # Length check
        if len(title) < 10:
            score *= 0.5
        elif len(title) > 200:
            score *= 0.8
        
        # Check for proper capitalization
        if not title[0].isupper():
            score *= 0.9
        
        # Check for reasonable content
        if title.count(' ') < 2:
            score *= 0.7
        
        return score
    
    def _validate_authors(self, authors: str) -> float:
        """Validate author list quality."""
        if not authors:
            return 0.0
        
        score = 1.0
        
        # Check for multiple authors
        author_count = len(authors.split(";"))
        if author_count == 1 and "et al" not in authors.lower():
            score *= 0.8
        
        # Check for reasonable name patterns
        if not any(c.isupper() for c in authors):
            score *= 0.6
        
        return score
    
    def _validate_year(self, year: str) -> float:
        """Validate publication year."""
        try:
            year_int = int(re.findall(r'\d{4}', year)[0])
            current_year = datetime.now().year
            
            if 1950 <= year_int <= current_year + 2:
                return 1.0
            else:
                return 0.3
        except (ValueError, IndexError):
            return 0.2
    
    def _validate_doi(self, doi: str) -> float:
        """Validate DOI format."""
        if not doi:
            return 0.0
        
        # DOI pattern
        doi_pattern = r'10\.\d+/[^\s\]]+'
        if re.search(doi_pattern, doi):
            return 1.0
        else:
            return 0.3
    
    def _validate_journal(self, journal: str) -> float:
        """Validate journal/venue name."""
        if not journal:
            return 0.0
        
        score = 1.0
        
        # Check length
        if len(journal) < 5:
            score *= 0.5
        
        # Check for common journal patterns
        if any(pattern in journal.lower() for pattern in [
            "journal", "proceedings", "conference", "ieee", "acm"
        ]):
            score *= 1.1
        
        return min(score, 1.0)
    
    def _assess_quality_indicators(self, metadata: Dict, conflicts: Dict) -> Dict:
        """Assess overall metadata quality indicators."""
        
        indicators = {
            "completeness": self._calculate_completeness(metadata),
            "consistency": self._calculate_consistency(metadata, conflicts),
            "format_validity": self._calculate_format_validity(metadata),
            "source_diversity": self._calculate_source_diversity(metadata)
        }
        
        # Overall quality score
        quality_score = sum(indicators.values()) / len(indicators)
        indicators["quality_score"] = quality_score
        
        return indicators
    
    def _calculate_completeness(self, metadata: Dict) -> float:
        """Calculate metadata completeness score."""
        important_fields = ["title", "authors", "year"]
        optional_fields = ["journal", "doi", "abstract"]
        
        important_present = sum(1 for field in important_fields if metadata.get(field))
        optional_present = sum(1 for field in optional_fields if metadata.get(field))
        
        important_score = important_present / len(important_fields)
        optional_score = optional_present / len(optional_fields)
        
        return important_score * 0.8 + optional_score * 0.2
    
    def _calculate_consistency(self, metadata: Dict, conflicts: Dict) -> float:
        """Calculate consistency score based on conflicts."""
        total_fields = len(metadata)
        conflict_fields = len(conflicts)
        
        if total_fields == 0:
            return 0.0
        
        return 1.0 - (conflict_fields / total_fields)
    
    def _calculate_format_validity(self, metadata: Dict) -> float:
        """Calculate format validity score."""
        validations = []
        
        for field, value in metadata.items():
            if value:
                validation_score = self._validate_field_content(field, str(value))
                validations.append(validation_score)
        
        return sum(validations) / len(validations) if validations else 0.0
    
    def _calculate_source_diversity(self, metadata: Dict) -> float:
        """Calculate source diversity (placeholder)."""
        return 0.8  # Simplified for now
    
    def _generate_recommendation(self, confidence: float, quality: Dict) -> str:
        """Generate recommendation based on confidence and quality."""
        
        if confidence >= 0.8:
            return "High confidence - Ready for publication"
        elif confidence >= 0.6:
            return "Medium confidence - Minor review recommended"
        elif confidence >= 0.4:
            return "Low confidence - Manual verification required"
        else:
            return "Very low confidence - Requires manual entry"


class BibtexGeneratorTool(BaseTool):
    """Tool for generating BibTeX entries from extracted metadata."""
    
    name: str = "bibtex_generator"
    description: str = """
    Generate properly formatted BibTeX entries from extracted paper metadata.
    Handles different entry types (article, inproceedings, misc) and required fields.
    Input: JSON with paper metadata and confidence scores
    Output: Formatted BibTeX entry string
    """
    
    def _run(self, metadata_with_scores: str) -> str:
        """Generate BibTeX entry synchronously."""
        try:
            data = json.loads(metadata_with_scores)
            bibtex_entry = self._generate_bibtex(data)
            return bibtex_entry
        except Exception as e:
            return f"% Error generating BibTeX: {e}"
    
    async def _arun(self, metadata_with_scores: str) -> str:
        """Generate BibTeX entry asynchronously."""
        return self._run(metadata_with_scores)
    
    def _generate_bibtex(self, data: Dict) -> str:
        """Generate BibTeX entry from metadata."""
        
        metadata = data.get("merged_metadata", {})
        confidence_scores = data.get("confidence_scores", {})
        
        # Generate citation key
        citation_key = self._generate_citation_key(metadata)
        
        # Determine entry type
        entry_type = metadata.get("bibtex_type", "article")
        
        # Start BibTeX entry
        bibtex_lines = [f"@{entry_type}{{{citation_key},"]
        
        # Add fields based on entry type
        if entry_type == "article":
            bibtex_lines.extend(self._add_article_fields(metadata))
        elif entry_type == "inproceedings":
            bibtex_lines.extend(self._add_inproceedings_fields(metadata))
        elif entry_type == "misc":
            bibtex_lines.extend(self._add_misc_fields(metadata))
        else:
            bibtex_lines.extend(self._add_article_fields(metadata))  # Default
        
        bibtex_lines.append("}")
        
        # Add confidence comment
        overall_confidence = confidence_scores.get("overall_confidence", 0.0)
        confidence_comment = f"% AI Extraction Confidence: {overall_confidence:.1%}"
        
        return confidence_comment + "\n" + "\n".join(bibtex_lines)
    
    def _generate_citation_key(self, metadata: Dict) -> str:
        """Generate a citation key from metadata."""
        
        # Get first author surname
        authors = metadata.get("authors", "")
        first_author = "Unknown"
        
        if authors:
            # Extract first author
            author_list = authors.split(";")[0].split(",")[0].strip()
            # Get last name (assume last word is surname)
            first_author = author_list.split()[-1].replace(".", "")
        
        # Get year
        year = metadata.get("year", "")
        year_str = re.findall(r'\d{4}', year)[0] if year else "XXXX"
        
        # Get title words
        title = metadata.get("title", "")
        title_words = []
        if title:
            # Take first few significant words
            words = title.split()
            for word in words[:3]:
                clean_word = re.sub(r'[^a-zA-Z]', '', word)
                if len(clean_word) > 3:  # Skip short words
                    title_words.append(clean_word.lower().capitalize())
        
        if not title_words:
            title_words = ["Paper"]
        
        # Combine parts
        citation_key = first_author + year_str + "".join(title_words)
        
        # Clean up the key
        citation_key = re.sub(r'[^a-zA-Z0-9]', '', citation_key)
        
        return citation_key
    
    def _add_article_fields(self, metadata: Dict) -> List[str]:
        """Add fields for journal articles."""
        fields = []
        
        # Required fields
        if metadata.get("title"):
            fields.append(f'  title={{{metadata["title"]}}},')
        
        if metadata.get("authors"):
            fields.append(f'  author={{{metadata["authors"]}}},')
        
        if metadata.get("journal"):
            fields.append(f'  journal={{{metadata["journal"]}}},')
        
        if metadata.get("year"):
            year = re.findall(r'\d{4}', metadata["year"])[0] if metadata["year"] else ""
            if year:
                fields.append(f'  year={{{year}}},')
        
        # Optional fields
        if metadata.get("doi"):
            fields.append(f'  doi={{{metadata["doi"]}}},')
        
        if metadata.get("abstract"):
            # Truncate very long abstracts
            abstract = metadata["abstract"]
            if len(abstract) > 500:
                abstract = abstract[:500] + "..."
            fields.append(f'  abstract={{{abstract}}},')
        
        if metadata.get("keywords"):
            fields.append(f'  keywords={{{metadata["keywords"]}}},')
        
        if metadata.get("url"):
            fields.append(f'  url={{{metadata["url"]}}},')
        
        return fields
    
    def _add_inproceedings_fields(self, metadata: Dict) -> List[str]:
        """Add fields for conference proceedings."""
        fields = []
        
        # Required fields
        if metadata.get("title"):
            fields.append(f'  title={{{metadata["title"]}}},')
        
        if metadata.get("authors"):
            fields.append(f'  author={{{metadata["authors"]}}},')
        
        if metadata.get("journal"):
            # For conferences, journal field becomes booktitle
            fields.append(f'  booktitle={{{metadata["journal"]}}},')
        
        if metadata.get("year"):
            year = re.findall(r'\d{4}', metadata["year"])[0] if metadata["year"] else ""
            if year:
                fields.append(f'  year={{{year}}},')
        
        # Optional fields
        if metadata.get("doi"):
            fields.append(f'  doi={{{metadata["doi"]}}},')
        
        if metadata.get("abstract"):
            abstract = metadata["abstract"]
            if len(abstract) > 500:
                abstract = abstract[:500] + "..."
            fields.append(f'  abstract={{{abstract}}},')
        
        return fields
    
    def _add_misc_fields(self, metadata: Dict) -> List[str]:
        """Add fields for miscellaneous entries (e.g., arXiv preprints)."""
        fields = []
        
        # Required fields
        if metadata.get("title"):
            fields.append(f'  title={{{metadata["title"]}}},')
        
        if metadata.get("authors"):
            fields.append(f'  author={{{metadata["authors"]}}},')
        
        if metadata.get("year"):
            year = re.findall(r'\d{4}', metadata["year"])[0] if metadata["year"] else ""
            if year:
                fields.append(f'  year={{{year}}},')
        
        # Optional fields
        if metadata.get("journal") or metadata.get("url"):
            # For misc entries, use howpublished
            howpub = metadata.get("journal") or metadata.get("url")
            fields.append(f'  howpublished={{{howpub}}},')
        
        if metadata.get("abstract"):
            abstract = metadata["abstract"]
            if len(abstract) > 500:
                abstract = abstract[:500] + "..."
            fields.append(f'  abstract={{{abstract}}},')
        
        if metadata.get("url"):
            fields.append(f'  url={{{metadata["url"]}}},')
        
        return fields