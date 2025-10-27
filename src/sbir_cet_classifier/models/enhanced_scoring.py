# sbir-cet-classifier/src/sbir_cet_classifier/models/enhanced_scoring.py
"""
Enhanced CET classifier with solicitation text integration.

This module provides:
- EnhancedCETClassifier: a thin wrapper around the canonical `MultiSourceTextVectorizer`
  and a scikit-learn `LogisticRegression` classifier. It supports optional
  solicitation text inclusion and exposes helper methods for training and scoring.
- SolicitationEnhancedScorer: a helper that can combine base classifier probabilities
  with solicitation-provided CET relevance scores.

The file intentionally avoids duplicate vectorizer implementations and relies on the
canonical `MultiSourceTextVectorizer` in `sbir_cet_classifier.models.vectorizers`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.linear_model import LogisticRegression

from sbir_cet_classifier.models.vectorizers import MultiSourceTextVectorizer


class EnhancedCETClassifier:
    """Enhanced CET classifier with optional solicitation text integration.

    This class wires a canonical multi-source TF-IDF vectorizer to a simple
    logistic regression classifier. It provides convenience methods to prepare
    training data, fit the model, predict probabilities, and extract feature
    importance.
    """

    def __init__(
        self,
        include_solicitation_text: bool = True,
        solicitation_weight: float = 0.3,
        abstract_weight: float = 0.5,
        keywords_weight: float = 0.2,
        *,
        max_features: int = 10_000,
        ngram_range: Tuple[int, int] = (1, 2),
        **classifier_params: Any,
    ) -> None:
        # Validate weights
        if include_solicitation_text:
            if abs(solicitation_weight + abstract_weight + keywords_weight - 1.0) > 1e-6:
                raise ValueError("Weights must sum to 1.0")
        else:
            if abs(abstract_weight + keywords_weight - 1.0) > 1e-6:
                raise ValueError("Weights must sum to 1.0")
            solicitation_weight = 0.0

        self.include_solicitation_text = include_solicitation_text
        self.solicitation_weight = solicitation_weight
        self.abstract_weight = abstract_weight
        self.keywords_weight = keywords_weight

        # Canonical vectorizer
        self.vectorizer_: MultiSourceTextVectorizer = MultiSourceTextVectorizer(
            abstract_weight=abstract_weight,
            keywords_weight=keywords_weight,
            solicitation_weight=solicitation_weight,
            include_solicitation=include_solicitation_text,
            max_features=max_features,
            ngram_range=ngram_range,
        )

        # Base classifier
        self.classifier_: LogisticRegression = LogisticRegression(**classifier_params)
        self.is_fitted: bool = False
        self.cet_categories_: List[str] = []

    def prepare_training_data(
        self, awards_data: List[Dict[str, Any]]
    ) -> Tuple[csr_matrix, List[str]]:
        """Prepare document matrix and feature names from raw award dicts."""
        documents: List[Dict[str, str]] = []
        for award in awards_data:
            doc: Dict[str, str] = {
                "abstract": award.get("abstract", ""),
                "keywords": award.get("keywords", ""),
            }
            if self.include_solicitation_text:
                doc["solicitation_text"] = award.get("solicitation_text", "")
            documents.append(doc)

        X: csr_matrix = self.vectorizer_.fit_transform(documents)
        feature_names: List[str] = self.vectorizer_.get_feature_names_out()
        return X, feature_names

    def fit(
        self, awards_data: List[Dict[str, Any]], y: np.ndarray, cet_categories: List[str]
    ) -> "EnhancedCETClassifier":
        """Fit vectorizer and classifier.

        Args:
            awards_data: List of award-like dicts containing text fields.
            y: Integer-encoded labels aligned with awards_data.
            cet_categories: List of CET category ids in the classifier label order.
        """
        X, _ = self.prepare_training_data(awards_data)
        self.classifier_.fit(X, y)
        self.cet_categories_ = list(cet_categories)
        self.is_fitted = True
        return self

    def predict_proba(self, awards_data: List[Dict[str, Any]]) -> np.ndarray:
        """Predict class probabilities for given award dicts.

        Returns:
            numpy array shape (n_samples, n_classes)
        """
        if not self.is_fitted:
            raise ValueError("Classifier must be fitted before prediction")

        documents: List[Dict[str, str]] = []
        for award in awards_data:
            doc: Dict[str, str] = {
                "abstract": award.get("abstract", ""),
                "keywords": award.get("keywords", ""),
            }
            if self.include_solicitation_text:
                doc["solicitation_text"] = award.get("solicitation_text", "")
            documents.append(doc)

        X: csr_matrix = self.vectorizer_.transform(documents)
        return self.classifier_.predict_proba(X)

    def predict_top_categories(
        self, award_data: Dict[str, Any], top_n: int = 3
    ) -> List[Tuple[str, float]]:
        """Return top-N CET categories (cet_id, probability) for a single award."""
        probs = self.predict_proba([award_data])[0]
        top_indices = np.argsort(probs)[-top_n:][::-1]
        return [(self.cet_categories_[i], float(probs[i])) for i in top_indices]

    def get_feature_importance(self) -> Dict[str, float]:
        """Return feature importance (mean absolute coefficient) keyed by feature name."""
        if not self.is_fitted:
            raise ValueError("Classifier must be fitted before getting feature importance")

        feature_names = self.vectorizer_.get_feature_names_out()
        if hasattr(self.classifier_, "coef_"):
            importance_scores = np.mean(np.abs(self.classifier_.coef_), axis=0)
            return dict(zip(feature_names, importance_scores.tolist()))
        return {}


class SolicitationEnhancedScorer:
    """Scorer that enhances base classifier outputs with solicitation-provided CET relevance."""

    def __init__(self, base_classifier: Optional[EnhancedCETClassifier] = None) -> None:
        self.base_classifier = base_classifier

    def enhance_award_with_solicitation(
        self, award: Dict[str, Any], solicitation: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Attach solicitation text and pre-computed CET relevance scores to an award dict."""
        enhanced_award = award.copy()
        if solicitation:
            enhanced_award["solicitation_text"] = solicitation.get("full_text", "")
            enhanced_award["solicitation_cet_scores"] = solicitation.get("cet_relevance_scores", {})
        else:
            enhanced_award["solicitation_text"] = ""
            enhanced_award["solicitation_cet_scores"] = {}
        return enhanced_award

    def calculate_enhanced_scores(
        self, enhanced_award: Dict[str, Any], boost_factor: float = 0.3
    ) -> Dict[str, float]:
        """Combine base classifier probabilities with solicitation CET relevance scores.

        Args:
            enhanced_award: Award dict that may contain `solicitation_cet_scores`.
            boost_factor: Fractional boost applied to solicitation scores (0..1).

        Returns:
            Mapping of cet_id -> combined score (0..1).
        """
        # Base scores from classifier (if available)
        base_scores: Dict[str, float] = {}
        if self.base_classifier is not None and self.base_classifier.is_fitted:
            base_prob_vector = self.base_classifier.predict_proba([enhanced_award])[0]
            base_scores = dict(zip(self.base_classifier.cet_categories_, base_prob_vector.tolist()))

        solicitation_scores: Dict[str, float] = (
            enhanced_award.get("solicitation_cet_scores", {}) or {}
        )

        return self.combine_scores_with_solicitation_boost(
            base_scores, solicitation_scores, boost_factor=boost_factor
        )

    @staticmethod
    def combine_scores_with_solicitation_boost(
        base_scores: Dict[str, float],
        solicitation_scores: Dict[str, float],
        boost_factor: float = 0.3,
    ) -> Dict[str, float]:
        """Linearly combine base scores with solicitation-derived boosts.

        Existing categories receive: min(1.0, base + solicitation * boost_factor)
        New categories (only in solicitation) are added as solicitation * boost_factor.
        """
        combined_scores: Dict[str, float] = base_scores.copy()
        for category, sol_score in solicitation_scores.items():
            if category in combined_scores:
                boosted = combined_scores[category] + sol_score * boost_factor
                combined_scores[category] = min(1.0, float(boosted))
            else:
                combined_scores[category] = float(sol_score * boost_factor)
        return combined_scores
