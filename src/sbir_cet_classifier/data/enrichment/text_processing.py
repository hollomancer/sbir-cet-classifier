"""Solicitation text parsing and keyword extraction."""

import re
from typing import List, Dict, Tuple, Optional
from collections import Counter
from datetime import datetime


class SolicitationTextProcessor:
    """Process and extract information from solicitation text."""

    def extract_technical_requirements(self, full_text: str) -> str:
        """Extract technical requirements section from solicitation text."""
        # Look for common section headers
        patterns = [
            r"TECHNICAL\s+REQUIREMENTS?\s*:?\s*(.*?)(?=^\s*[A-Z][A-Z ]+(?::|$)|\Z)",
            r"TECHNICAL\s+APPROACH\s*:?\s*(.*?)(?=^\s*[A-Z][A-Z ]+(?::|$)|\Z)",
            r"TECHNICAL\s+OBJECTIVES?\s*:?\s*(.*?)(?=^\s*[A-Z][A-Z ]+(?::|$)|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
            if match:
                return self.clean_text(match.group(1)).lower()

        return ""

    def extract_evaluation_criteria(self, full_text: str) -> str:
        """Extract evaluation criteria section from solicitation text."""
        patterns = [
            r"EVALUATION\s+CRITERIA\s*:?\s*(.*?)(?=^\s*[A-Z][A-Z ]+(?::|$)|\Z)",
            r"SELECTION\s+CRITERIA\s*:?\s*(.*?)(?=^\s*[A-Z][A-Z ]+(?::|$)|\Z)",
            r"AWARD\s+CRITERIA\s*:?\s*(.*?)(?=^\s*[A-Z][A-Z ]+(?::|$)|\Z)",
        ]

        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL | re.MULTILINE)
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

        def normalize(date_str: str) -> Optional[str]:
            """Normalize a date string to YYYY-MM-DD."""
            if not date_str:
                return None
            date_str = date_str.strip()
            # Try common formats
            for fmt in ("%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except Exception:
                    continue
            # If raw string contains a date-like pattern, extract and retry
            for pat in [
                r"(\w+\s+\d{1,2},\s+\d{4})",
                r"(\d{1,2}/\d{1,2}/\d{4})",
                r"(\d{4}-\d{2}-\d{2})",
            ]:
                m = re.search(pat, date_str)
                if m:
                    return normalize(m.group(1))
            return None

        # Map patterns to deadline keys
        label_patterns: Dict[str, List[str]] = {
            "proposal_deadline": [
                r"proposal\s+submission\s+deadline:?\s*([^.\n]+)",
                r"due\s+date:?\s*([^.\n]+)",
                r"deadline:?\s*([^.\n]+)",
            ],
            "award_notification": [
                r"award\s+notification:?\s*([^.\n]+)",
                r"notification\s+date:?\s*([^.\n]+)",
            ],
            "performance_start": [
                r"performance\s+start(?:\s+date)?:?\s*([^.\n]+)",
                r"start\s+date:?\s*([^.\n]+)",
            ],
        }

        for key, patterns in label_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    normalized = normalize(match.group(1))
                    if normalized:
                        deadlines[key] = normalized
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
        fallback_defaults = {
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
        # Merge fallback defaults with any config-provided keywords to ensure baseline coverage
        if hasattr(self, "cet_keywords") and isinstance(self.cet_keywords, dict):
            for cet_id, kw_list in fallback_defaults.items():
                existing = self.cet_keywords.get(cet_id, [])
                # Normalize to lowercase for substring matching
                merged = sorted(list(set([k.lower() for k in existing + kw_list])))
                self.cet_keywords[cet_id] = merged
        else:
            self.cet_keywords = {
                k: sorted(list(set([kw.lower() for kw in v]))) for k, v in fallback_defaults.items()
            }
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

        # Check for CET category keywords (normalize to lowercase for substring matching)
        for _, keywords in self.cet_keywords.items():
            for keyword in keywords:
                kw_lower = keyword.lower()
                if kw_lower in text_lower:
                    found_keywords.append(kw_lower)

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


from sbir_cet_classifier.models.cet_relevance_scorer import CETRelevanceScorer
