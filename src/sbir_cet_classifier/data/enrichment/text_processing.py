"""Solicitation text parsing and keyword extraction."""

import re
from typing import List, Dict, Tuple, Optional
from collections import Counter


class SolicitationTextProcessor:
    """Process and extract information from solicitation text."""

    def extract_technical_requirements(self, full_text: str) -> str:
        """Extract technical requirements section from solicitation text."""
        # Look for common section headers
        patterns = [
            r"TECHNICAL\s+REQUIREMENTS?\s*:?\s*(.*?)(?=\n[A-Z\s]{3,}:|$)",
            r"TECHNICAL\s+APPROACH\s*:?\s*(.*?)(?=\n[A-Z\s]{3,}:|$)",
            r"TECHNICAL\s+OBJECTIVES?\s*:?\s*(.*?)(?=\n[A-Z\s]{3,}:|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if match:
                return self.clean_text(match.group(1))

        return ""

    def extract_evaluation_criteria(self, full_text: str) -> str:
        """Extract evaluation criteria section from solicitation text."""
        patterns = [
            r"EVALUATION\s+CRITERIA\s*:?\s*(.*?)(?=\n[A-Z\s]{3,}:|$)",
            r"SELECTION\s+CRITERIA\s*:?\s*(.*?)(?=\n[A-Z\s]{3,}:|$)",
            r"AWARD\s+CRITERIA\s*:?\s*(.*?)(?=\n[A-Z\s]{3,}:|$)",
        ]

        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if match:
                return self.clean_text(match.group(1))

        return ""

    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove excessive newlines
        text = re.sub(r"\n\s*\n", "\n", text)

        return text.strip()

    def extract_funding_information(self, full_text: str) -> Dict[str, Optional[int]]:
        """Extract funding information from solicitation text."""
        funding_info = {
            "phase_i_min": None,
            "phase_i_max": None,
            "phase_ii_min": None,
            "phase_ii_max": None,
        }

        # Look for Phase I funding patterns
        phase_i_patterns = [
            r"Phase\s+I\s+awards?:?\s*\$?(\d{1,3}(?:,\d{3})*)\s*-\s*\$?(\d{1,3}(?:,\d{3})*)",
            r"Phase\s+I:?\s*\$?(\d{1,3}(?:,\d{3})*)\s*to\s*\$?(\d{1,3}(?:,\d{3})*)",
        ]

        for pattern in phase_i_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                funding_info["phase_i_min"] = int(match.group(1).replace(",", ""))
                funding_info["phase_i_max"] = int(match.group(2).replace(",", ""))
                break

        # Look for Phase II funding patterns
        phase_ii_patterns = [
            r"Phase\s+II\s+awards?:?\s*\$?(\d{1,3}(?:,\d{3})*)\s*-\s*\$?(\d{1,3}(?:,\d{3})*)",
            r"Phase\s+II:?\s*\$?(\d{1,3}(?:,\d{3})*)\s*to\s*\$?(\d{1,3}(?:,\d{3})*)",
        ]

        for pattern in phase_ii_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                funding_info["phase_ii_min"] = int(match.group(1).replace(",", ""))
                funding_info["phase_ii_max"] = int(match.group(2).replace(",", ""))
                break

        return funding_info

    def extract_deadlines(self, full_text: str) -> Dict[str, Optional[str]]:
        """Extract important dates from solicitation text."""
        deadlines = {
            "proposal_deadline": None,
            "award_notification": None,
            "performance_start": None,
        }

        # Date patterns
        date_patterns = [
            r"(\w+\s+\d{1,2},\s+\d{4})",  # Month DD, YYYY
            r"(\d{1,2}/\d{1,2}/\d{4})",  # MM/DD/YYYY
            r"(\d{4}-\d{2}-\d{2})",  # YYYY-MM-DD
        ]

        # Look for proposal deadline
        deadline_patterns = [
            r"proposal\s+submission\s+deadline:?\s*([^.\n]+)",
            r"due\s+date:?\s*([^.\n]+)",
            r"deadline:?\s*([^.\n]+)",
        ]

        for pattern in deadline_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                date_text = match.group(1)
                for date_pattern in date_patterns:
                    date_match = re.search(date_pattern, date_text)
                    if date_match:
                        deadlines["proposal_deadline"] = date_match.group(1)
                        break
                if deadlines["proposal_deadline"]:
                    break

        return deadlines


class TechnicalKeywordExtractor:
    """Extract technical keywords from solicitation text."""

    def __init__(self):
        """Initialize with CET keyword mappings."""
        # Load CET keyword mappings from configuration so they can be tuned without code changes.
        # Fall back to an in-code default if loading fails for any reason.
        try:
            from sbir_cet_classifier.common.classification_config import get_cet_keywords_map

            cet_map = get_cet_keywords_map()
            # Convert CETKeywords models (with core/related buckets) into a simple list
            # used by the extractor (core + related). Negative keywords are handled
            # separately in scoring if needed.
            self.cet_keywords = {
                cet_id: [
                    kw
                    for kw in (getattr(bucket, "core", []) + getattr(bucket, "related", []))
                    if kw
                ]
                for cet_id, bucket in cet_map.items()
            }
        except Exception:
            # Fallback to a minimal static mapping if configuration is not available
            self.cet_keywords = {
                "quantum_computing": [
                    "quantum computing",
                    "quantum algorithm",
                    "quantum cryptography",
                    "quantum sensing",
                    "quantum communication",
                    "qubit",
                    "quantum entanglement",
                ],
                "artificial_intelligence": [
                    "artificial intelligence",
                    "machine learning",
                    "deep learning",
                    "neural network",
                    "ai",
                    "ml",
                    "computer vision",
                    "natural language processing",
                ],
                "cybersecurity": [
                    "cybersecurity",
                    "cyber security",
                    "information security",
                    "encryption",
                    "cryptography",
                    "firewall",
                    "intrusion detection",
                    "malware",
                ],
                "advanced_materials": [
                    "advanced materials",
                    "nanomaterials",
                    "composites",
                    "metamaterials",
                    "smart materials",
                    "biomaterials",
                    "carbon nanotubes",
                ],
                "nanotechnology": [
                    "nanotechnology",
                    "nanoparticles",
                    "nanoscale",
                    "nanostructures",
                    "nanofabrication",
                    "nanoelectronics",
                ],
                "biotechnology": [
                    "biotechnology",
                    "bioengineering",
                    "synthetic biology",
                    "gene therapy",
                    "bioinformatics",
                    "biomedical",
                    "pharmaceutical",
                ],
                "autonomous_systems": [
                    "autonomous systems",
                    "autonomous vehicles",
                    "robotics",
                    "unmanned",
                    "self-driving",
                    "autonomous navigation",
                    "robot",
                ],
                "semiconductors": [
                    "semiconductors",
                    "microelectronics",
                    "integrated circuits",
                    "chips",
                    "silicon",
                    "gallium arsenide",
                    "semiconductor fabrication",
                ],
            }

        # Technical terms that indicate advanced research
        self.technical_terms = [
            "algorithm",
            "protocol",
            "system",
            "framework",
            "architecture",
            "methodology",
            "technique",
            "approach",
            "solution",
            "platform",
            "interface",
            "network",
            "sensor",
            "device",
            "component",
        ]

    def extract_cet_keywords(self, text: str) -> List[str]:
        """Extract CET-related keywords from text."""
        if not text:
            return []

        text_lower = text.lower()
        found_keywords = []

        # Check for CET category keywords
        for category, keywords in self.cet_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_keywords.append(keyword)

        # Remove duplicates and sort
        return sorted(list(set(found_keywords)))

    def extract_technical_phrases(self, text: str) -> List[str]:
        """Extract technical phrases from text."""
        if not text:
            return []

        # Use regex to find technical phrases (2-4 words with technical terms)
        technical_phrase_pattern = (
            r"\b(?:[A-Za-z]+\s+){0,2}(?:" + "|".join(self.technical_terms) + r")\b"
        )

        phrases = re.findall(technical_phrase_pattern, text, re.IGNORECASE)

        # Clean and filter phrases
        cleaned_phrases = []
        for phrase in phrases:
            phrase = phrase.strip()
            if len(phrase.split()) >= 2 and len(phrase) > 5:
                cleaned_phrases.append(phrase.lower())

        return sorted(list(set(cleaned_phrases)))

    def filter_domain_specific_terms(self, terms: List[str]) -> List[str]:
        """Filter out non-technical terms."""
        # Common non-technical terms to exclude
        exclude_terms = {
            "project management",
            "team collaboration",
            "budget planning",
            "schedule",
            "timeline",
            "meeting",
            "report",
            "documentation",
            "administration",
            "coordination",
            "communication",
        }

        return [term for term in terms if term.lower() not in exclude_terms]

    def rank_keywords_by_relevance(self, keywords: List[str]) -> List[str]:
        """Rank keywords by CET relevance."""
        # Create relevance scores
        relevance_scores = {}

        for keyword in keywords:
            score = 0
            keyword_lower = keyword.lower()

            # Check if it's a CET keyword
            for category, cet_keywords in self.cet_keywords.items():
                if keyword_lower in [k.lower() for k in cet_keywords]:
                    score += 10
                    break

            # Check if it contains technical terms
            for tech_term in self.technical_terms:
                if tech_term in keyword_lower:
                    score += 5
                    break

            # Longer phrases get slight boost
            score += len(keyword.split())

            relevance_scores[keyword] = score

        # Sort by relevance score (descending)
        return sorted(keywords, key=lambda k: relevance_scores.get(k, 0), reverse=True)


class CETRelevanceScorer:
    """Calculate CET relevance scores for solicitation text."""

    def __init__(self):
        """Initialize with CET category definitions."""
        self.cet_categories = {
            "quantum_computing": {
                "keywords": [
                    "quantum",
                    "qubit",
                    "superposition",
                    "entanglement",
                    "quantum algorithm",
                ],
                "weight": 1.0,
            },
            "artificial_intelligence": {
                "keywords": [
                    "ai",
                    "artificial intelligence",
                    "machine learning",
                    "neural network",
                    "deep learning",
                ],
                "weight": 1.0,
            },
            "cybersecurity": {
                "keywords": ["cybersecurity", "encryption", "cryptography", "security", "cyber"],
                "weight": 1.0,
            },
            "advanced_materials": {
                "keywords": ["materials", "composites", "nanomaterials", "metamaterials"],
                "weight": 1.0,
            },
            "nanotechnology": {
                "keywords": ["nanotechnology", "nanoscale", "nanoparticles", "nanofabrication"],
                "weight": 1.0,
            },
            "biotechnology": {
                "keywords": [
                    "biotechnology",
                    "bioengineering",
                    "synthetic biology",
                    "bioinformatics",
                ],
                "weight": 1.0,
            },
            "autonomous_systems": {
                "keywords": ["autonomous", "robotics", "unmanned", "self-driving", "robot"],
                "weight": 1.0,
            },
            "semiconductors": {
                "keywords": ["semiconductor", "microelectronics", "integrated circuit", "chip"],
                "weight": 1.0,
            },
        }

    def calculate_relevance_scores(self, text: str) -> Dict[str, float]:
        """Calculate relevance scores for all CET categories."""
        if not text:
            return {}

        text_lower = text.lower()
        scores = {}

        for category, config in self.cet_categories.items():
            score = self.score_cet_category(text_lower, category)
            scores[category] = score

        return self.normalize_scores(scores)

    def score_cet_category(self, text: str, category: str) -> float:
        """Score text relevance for a specific CET category."""
        if category not in self.cet_categories:
            return 0.0

        config = self.cet_categories[category]
        keywords = config["keywords"]
        weight = config["weight"]

        # Count keyword occurrences
        total_score = 0.0
        text_words = text.split()
        text_length = len(text_words)

        if text_length == 0:
            return 0.0

        for keyword in keywords:
            # Count exact matches
            exact_matches = text.count(keyword)

            # Count partial matches (keyword appears in compound words)
            partial_matches = sum(1 for word in text_words if keyword in word and word != keyword)

            # Calculate keyword score
            keyword_score = (exact_matches * 2 + partial_matches) / text_length
            total_score += keyword_score

        # Apply category weight and normalize
        final_score = min(total_score * weight, 1.0)

        return final_score

    def normalize_scores(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Normalize scores to ensure they're between 0 and 1."""
        if not scores:
            return {}

        # Ensure all scores are between 0 and 1
        normalized = {}
        for category, score in scores.items():
            normalized[category] = max(0.0, min(1.0, score))

        return normalized

    def get_top_relevant_categories(
        self, scores: Dict[str, float], top_n: int = 5
    ) -> List[Tuple[str, float]]:
        """Get top N most relevant CET categories."""
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:top_n]

    def extract_entities(self, text: str) -> List[str]:
        """Extract named entities using spaCy (if available)."""
        try:
            import spacy

            nlp = spacy.load("en_core_web_sm")
            doc = nlp(text)

            entities = []
            for ent in doc.ents:
                if ent.label_ in ["ORG", "PRODUCT", "TECHNOLOGY", "GPE"]:
                    entities.append(ent.text)

            return entities

        except ImportError:
            # Fallback to simple pattern matching if spaCy not available
            return self._extract_entities_simple(text)

    def _extract_entities_simple(self, text: str) -> List[str]:
        """Simple entity extraction without spaCy."""
        # Look for capitalized phrases that might be entities
        entity_pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
        entities = re.findall(entity_pattern, text)

        # Filter out common words
        common_words = {"The", "This", "That", "These", "Those", "And", "Or", "But"}
        entities = [e for e in entities if e not in common_words]

        return list(set(entities))
