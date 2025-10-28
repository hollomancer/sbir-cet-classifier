"""CET relevance scoring for solicitation text."""

import re
from typing import Dict, List, Tuple, Optional
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sbir_cet_classifier.common.classification_config import get_cet_keywords_map


class CETRelevanceScorer:
    """Score text relevance to CET categories."""

    def __init__(self):
        """Initialize with CET category definitions."""
        # Load CET categories from YAML-backed configuration (core + related keywords).
        self.cet_categories = {}
        try:
            keyword_models = get_cet_keywords_map()
            for cet_id, buckets in keyword_models.items():
                core = getattr(buckets, "core", []) or []
                related = getattr(buckets, "related", []) or []
                keywords = [str(kw).lower() for kw in list(core) + list(related) if kw]
                self.cet_categories[cet_id] = {
                    "keywords": keywords,
                    "phrases": [],
                    "weight": 1.0,
                }
        except Exception:
            # Fallback to empty mapping if configuration unavailable
            self.cet_categories = {}

        # Initialize TF-IDF vectorizer for semantic similarity
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3), max_features=5000, stop_words="english"
        )

        # Pre-compute category vectors
        self._build_category_vectors()

    def _build_category_vectors(self):
        """Build TF-IDF vectors for each CET category."""
        category_texts = []
        self.category_names = []

        for category, config in self.cet_categories.items():
            # Combine keywords and phrases
            text = " ".join(config["keywords"] + config.get("phrases", []))
            category_texts.append(text)
            self.category_names.append(category)

        # Fit vectorizer and transform category texts
        self.category_vectors = self.vectorizer.fit_transform(category_texts)

    def calculate_relevance_scores(self, text: str) -> Dict[str, float]:
        """Calculate relevance scores for all CET categories."""
        if not text:
            return {category: 0.0 for category in self.cet_categories.keys()}

        # Combine multiple scoring methods
        keyword_scores = self._calculate_keyword_scores(text)
        semantic_scores = self._calculate_semantic_scores(text)
        phrase_scores = self._calculate_phrase_scores(text)

        # Weighted combination
        combined_scores = {}
        for category in self.cet_categories.keys():
            combined_score = (
                0.5 * keyword_scores.get(category, 0.0)
                + 0.3 * semantic_scores.get(category, 0.0)
                + 0.2 * phrase_scores.get(category, 0.0)
            )
            combined_scores[category] = min(1.0, combined_score)

        return combined_scores

    def _calculate_keyword_scores(self, text: str) -> Dict[str, float]:
        """Calculate scores based on keyword matching."""
        text_lower = text.lower()
        text_words = text_lower.split()
        text_length = len(text_words)

        if text_length == 0:
            return {category: 0.0 for category in self.cet_categories.keys()}

        scores = {}

        for category, config in self.cet_categories.items():
            keywords = config["keywords"]
            weight = config["weight"]

            total_score = 0.0

            for keyword in keywords:
                keyword_lower = keyword.lower()

                # Exact phrase matches (higher weight) with plural-aware variants
                exact_matches = 0
                if " " in keyword_lower:
                    parts = keyword_lower.split()
                    base_phrase = keyword_lower
                    last = parts[-1]
                    variants = {base_phrase, f"{' '.join(parts[:-1])} {last}s"}
                    if last.endswith("y") and len(last) > 1:
                        variants.add(f"{' '.join(parts[:-1])} {last[:-1]}ies")
                    variants.add(f"{' '.join(parts[:-1])} {last}es")
                    for var in variants:
                        exact_matches += text_lower.count(var)
                else:
                    exact_matches = text_lower.count(keyword_lower)

                # Partial matches in compound words and tokens
                partial_matches = 0
                if " " in keyword_lower:
                    for token in keyword_lower.split():
                        partial_matches += sum(
                            1 for word in text_words if token in word and word != token
                        )
                else:
                    partial_matches = sum(
                        1 for word in text_words if keyword_lower in word and word != keyword_lower
                    )

                # Calculate keyword score with diminishing returns
                keyword_score = (exact_matches * 3 + partial_matches * 0.75) / max(1, text_length)
                total_score += min(keyword_score, 0.15)  # Cap individual keyword contribution

            # Apply category weight and normalize
            final_score = min(total_score * weight, 1.0)
            scores[category] = final_score

        return scores

    def _calculate_semantic_scores(self, text: str) -> Dict[str, float]:
        """Calculate scores based on semantic similarity."""
        try:
            # Transform input text
            text_vector = self.vectorizer.transform([text])

            # Calculate cosine similarity with each category
            similarities = cosine_similarity(text_vector, self.category_vectors)[0]

            # Convert to dictionary
            scores = {}
            for i, category in enumerate(self.category_names):
                scores[category] = max(0.0, similarities[i])  # Ensure non-negative

            return scores

        except Exception:
            # Fallback to zero scores if vectorization fails
            return {category: 0.0 for category in self.cet_categories.keys()}

    def _calculate_phrase_scores(self, text: str) -> Dict[str, float]:
        """Calculate scores based on technical phrase matching."""
        text_lower = text.lower()
        scores = {}

        for category, config in self.cet_categories.items():
            phrases = list(
                set(
                    config.get("phrases", [])
                    + [kw for kw in config.get("keywords", []) if " " in kw]
                )
            )

            if not phrases:
                scores[category] = 0.0
                continue

            phrase_score = 0.0

            for phrase in phrases:
                phrase_lower = phrase.lower()

                # Check for exact phrase matches (plural-aware)
                if " " in phrase_lower:
                    parts = phrase_lower.split()
                    last = parts[-1]
                    variants = {phrase_lower, f"{' '.join(parts[:-1])} {last}s"}
                    if last.endswith("y") and len(last) > 1:
                        variants.add(f"{' '.join(parts[:-1])} {last[:-1]}ies")
                    variants.add(f"{' '.join(parts[:-1])} {last}es")
                    if any(var in text_lower for var in variants):
                        phrase_score += 0.25  # Each phrase contributes up to 0.25
                else:
                    if phrase_lower in text_lower:
                        phrase_score += 0.25  # Each phrase contributes up to 0.25

                # Check for partial phrase matches (most words present)
                phrase_words = phrase_lower.split()
                text_words = text_lower.split()

                matching_words = sum(1 for word in phrase_words if word in text_words)
                if len(phrase_words) > 1 and matching_words >= len(phrase_words) * 0.7:
                    phrase_score += 0.15  # Partial match contributes less

            scores[category] = min(phrase_score, 1.0)

        return scores

    def get_top_relevant_categories(self, text: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """Get top N most relevant CET categories for text."""
        scores = self.calculate_relevance_scores(text)
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:top_n]

    def score_cet_category(self, text: str, category: str) -> float:
        """Score text relevance for a specific CET category."""
        if category not in self.cet_categories:
            return 0.0

        scores = self.calculate_relevance_scores(text)
        return scores.get(category, 0.0)

    def explain_score(self, text: str, category: str) -> Dict[str, any]:
        """Provide explanation for a category score."""
        if category not in self.cet_categories:
            return {"error": f"Unknown category: {category}"}

        text_lower = text.lower()
        config = self.cet_categories[category]

        # Find matching keywords
        matching_keywords = []
        for keyword in config["keywords"]:
            if keyword.lower() in text_lower:
                matching_keywords.append(keyword)

        # Find matching phrases
        matching_phrases = []
        for phrase in config.get("phrases", []):
            if phrase.lower() in text_lower:
                matching_phrases.append(phrase)

        # Calculate component scores
        keyword_scores = self._calculate_keyword_scores(text)
        semantic_scores = self._calculate_semantic_scores(text)
        phrase_scores = self._calculate_phrase_scores(text)

        return {
            "category": category,
            "total_score": self.score_cet_category(text, category),
            "keyword_score": keyword_scores.get(category, 0.0),
            "semantic_score": semantic_scores.get(category, 0.0),
            "phrase_score": phrase_scores.get(category, 0.0),
            "matching_keywords": matching_keywords,
            "matching_phrases": matching_phrases,
            "explanation": f"Score based on {len(matching_keywords)} keywords and {len(matching_phrases)} phrases",
        }

    def batch_score(self, texts: List[str]) -> List[Dict[str, float]]:
        """Score multiple texts efficiently."""
        return [self.calculate_relevance_scores(text) for text in texts]
