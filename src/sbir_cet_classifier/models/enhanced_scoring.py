"""Enhanced CET classifier with solicitation text integration.

TODO(consolidation): This module overlaps with enhanced_vectorization.py and similar multi-source
vectorizers. Consider deprecating or moving these into an experimental/ namespace and unifying
the implementation under a single, config-backed vectorizer/scorer.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from scipy.sparse import hstack, csr_matrix
from sbir_cet_classifier.models.vectorizers import (
    MultiSourceTextVectorizer as CanonicalMultiSourceTextVectorizer,
)


class MultiSourceTextVectorizer:
    """Vectorizer that combines multiple text sources with weights."""

    def __init__(
        self,
        abstract_weight: float = 0.5,
        keywords_weight: float = 0.2,
        solicitation_weight: float = 0.3,
        **tfidf_params,
    ):
        """Initialize with source weights and TF-IDF parameters."""
        if abs(abstract_weight + keywords_weight + solicitation_weight - 1.0) > 1e-6:
            raise ValueError("Weights must sum to 1.0")

        self.abstract_weight = abstract_weight
        self.keywords_weight = keywords_weight
        self.solicitation_weight = solicitation_weight

        # Initialize individual vectorizers
        self.abstract_vectorizer_ = TfidfVectorizer(**tfidf_params)
        self.keywords_vectorizer_ = TfidfVectorizer(**tfidf_params)
        self.solicitation_vectorizer_ = TfidfVectorizer(**tfidf_params)

        self.is_fitted = False

    def fit(self, documents: List[Dict[str, str]]):
        """Fit vectorizers on documents."""
        abstracts = [doc.get("abstract", "") for doc in documents]
        keywords = [doc.get("keywords", "") for doc in documents]
        solicitations = [doc.get("solicitation_text", "") for doc in documents]

        self.abstract_vectorizer_.fit(abstracts)
        self.keywords_vectorizer_.fit(keywords)
        self.solicitation_vectorizer_.fit(solicitations)

        self.is_fitted = True
        return self

    def transform(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Transform documents to feature vectors."""
        if not self.is_fitted:
            raise ValueError("Vectorizer must be fitted before transform")

        abstracts = [doc.get("abstract", "") for doc in documents]
        keywords = [doc.get("keywords", "") for doc in documents]
        solicitations = [doc.get("solicitation_text", "") for doc in documents]

        # Transform each source
        abstract_features = self.abstract_vectorizer_.transform(abstracts)
        keywords_features = self.keywords_vectorizer_.transform(keywords)
        solicitation_features = self.solicitation_vectorizer_.transform(solicitations)

        # Apply weights
        abstract_features = abstract_features * self.abstract_weight
        keywords_features = keywords_features * self.keywords_weight
        solicitation_features = solicitation_features * self.solicitation_weight

        # Combine features horizontally
        combined_features = hstack([abstract_features, keywords_features, solicitation_features])

        return combined_features

    def fit_transform(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Fit and transform in one step."""
        return self.fit(documents).transform(documents)

    def get_feature_names_out(self) -> List[str]:
        """Get feature names for all sources."""
        if not self.is_fitted:
            raise ValueError("Vectorizer must be fitted before getting feature names")

        abstract_names = [
            f"abstract_{name}" for name in self.abstract_vectorizer_.get_feature_names_out()
        ]
        keywords_names = [
            f"keywords_{name}" for name in self.keywords_vectorizer_.get_feature_names_out()
        ]
        solicitation_names = [
            f"solicitation_{name}" for name in self.solicitation_vectorizer_.get_feature_names_out()
        ]

        return abstract_names + keywords_names + solicitation_names

    def _get_abstract_features(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Get abstract features for testing."""
        abstracts = [doc.get("abstract", "") for doc in documents]
        return self.abstract_vectorizer_.transform(abstracts)

    def _get_keywords_features(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Get keywords features for testing."""
        keywords = [doc.get("keywords", "") for doc in documents]
        return self.keywords_vectorizer_.transform(keywords)

    def _get_solicitation_features(self, documents: List[Dict[str, str]]) -> csr_matrix:
        """Get solicitation features for testing."""
        solicitations = [doc.get("solicitation_text", "") for doc in documents]
        return self.solicitation_vectorizer_.transform(solicitations)


class EnhancedCETClassifier:
    """Enhanced CET classifier with solicitation text integration."""

    def __init__(
        self,
        include_solicitation_text: bool = True,
        solicitation_weight: float = 0.3,
        abstract_weight: float = 0.5,
        keywords_weight: float = 0.2,
        **classifier_params,
    ):
        """Initialize enhanced classifier."""
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

        # Initialize components
        if include_solicitation_text:
            self.vectorizer_ = CanonicalMultiSourceTextVectorizer(
                abstract_weight=abstract_weight,
                keywords_weight=keywords_weight,
                solicitation_weight=solicitation_weight,
                include_solicitation=True,
                max_features=10000,
                ngram_range=(1, 2),
            )
        else:
            self.vectorizer_ = CanonicalMultiSourceTextVectorizer(
                abstract_weight=abstract_weight,
                keywords_weight=keywords_weight,
                solicitation_weight=0.0,
                include_solicitation=False,
                max_features=10000,
                ngram_range=(1, 2),
            )

        self.classifier_ = LogisticRegression(**classifier_params)
        self.is_fitted = False
        self.cet_categories_ = []

    def prepare_training_data(
        self, awards_data: List[Dict[str, Any]]
    ) -> Tuple[csr_matrix, List[str]]:
        """Prepare training data from awards."""
        # Prepare documents for vectorization
        documents = []
        for award in awards_data:
            doc = {
                "abstract": award.get("abstract", ""),
                "keywords": award.get("keywords", ""),
            }

            if self.include_solicitation_text:
                doc["solicitation_text"] = award.get("solicitation_text", "")

            documents.append(doc)

        # Vectorize
        X = self.vectorizer_.fit_transform(documents)
        feature_names = self.vectorizer_.get_feature_names_out()

        return X, feature_names

    def fit(self, awards_data: List[Dict[str, Any]], y: np.ndarray, cet_categories: List[str]):
        """Fit the enhanced classifier."""
        X, _ = self.prepare_training_data(awards_data)

        self.classifier_.fit(X, y)
        self.cet_categories_ = cet_categories
        self.is_fitted = True

        return self

    def predict_proba(self, awards_data: List[Dict[str, Any]]) -> np.ndarray:
        """Predict probabilities for awards."""
        if not self.is_fitted:
            raise ValueError("Classifier must be fitted before prediction")

        # Prepare documents
        documents = []
        for award in awards_data:
            doc = {
                "abstract": award.get("abstract", ""),
                "keywords": award.get("keywords", ""),
            }

            if self.include_solicitation_text:
                doc["solicitation_text"] = award.get("solicitation_text", "")

            documents.append(doc)

        # Transform and predict
        X = self.vectorizer_.transform(documents)
        return self.classifier_.predict_proba(X)

    def predict_top_categories(
        self, award_data: Dict[str, Any], top_n: int = 3
    ) -> List[Tuple[str, float]]:
        """Predict top CET categories for a single award."""
        probabilities = self.predict_proba([award_data])[0]

        # Get top categories
        top_indices = np.argsort(probabilities)[-top_n:][::-1]

        return [(self.cet_categories_[i], probabilities[i]) for i in top_indices]

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from the classifier."""
        if not self.is_fitted:
            raise ValueError("Classifier must be fitted before getting feature importance")

        feature_names = self.vectorizer_.get_feature_names_out()

        # For logistic regression, use coefficient magnitudes
        if hasattr(self.classifier_, "coef_"):
            # Average importance across classes
            importance_scores = np.mean(np.abs(self.classifier_.coef_), axis=0)

            return dict(zip(feature_names, importance_scores))

        return {}


class SolicitationEnhancedScorer:
    """Scorer that enhances base CET scores with solicitation data."""

    def __init__(self, base_classifier=None):
        """Initialize with optional base classifier."""
        self.base_classifier = base_classifier

    def enhance_award_with_solicitation(
        self, award: Dict[str, Any], solicitation: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Enhance award data with solicitation information."""
        enhanced_award = award.copy()

        if solicitation:
            enhanced_award["solicitation_text"] = solicitation.get("full_text", "")
            enhanced_award["solicitation_cet_scores"] = solicitation.get("cet_relevance_scores", {})
        else:
            enhanced_award["solicitation_text"] = ""
            enhanced_award["solicitation_cet_scores"] = {}

        return enhanced_award

    def calculate_enhanced_scores(self, enhanced_award: Dict[str, Any]) -> Dict[str, float]:
        """Calculate enhanced CET scores combining base and solicitation scores."""
        # Get base scores from classifier
        if self.base_classifier:
            base_probabilities = self.base_classifier.predict_proba([enhanced_award])[0]
            base_scores = dict(zip(self.base_classifier.cet_categories_, base_probabilities))
        else:
            base_scores = {}

        # Get solicitation scores
        solicitation_scores = enhanced_award.get("solicitation_cet_scores", {})

        # Combine scores
        enhanced_scores = self.combine_scores_with_solicitation_boost(
            base_scores, solicitation_scores, boost_factor=0.3
        )

        return enhanced_scores

    def combine_scores_with_solicitation_boost(
        self,
        base_scores: Dict[str, float],
        solicitation_scores: Dict[str, float],
        boost_factor: float = 0.3,
    ) -> Dict[str, float]:
        """Combine base scores with solicitation boost."""
        combined_scores = base_scores.copy()

        # Apply solicitation boost
        for category, solicitation_score in solicitation_scores.items():
            if category in combined_scores:
                # Boost existing score
                boost = solicitation_score * boost_factor
                combined_scores[category] = min(1.0, combined_scores[category] + boost)
            else:
                # Add new category with solicitation influence
                combined_scores[category] = solicitation_score * boost_factor

        return combined_scores

    def batch_enhance_awards(
        self, awards: List[Dict[str, Any]], solicitations: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Enhance multiple awards with solicitation data."""
        enhanced_awards = []

        for award in awards:
            solicitation_id = award.get("solicitation_id")
            solicitation = solicitations.get(solicitation_id) if solicitation_id else None

            enhanced_award = self.enhance_award_with_solicitation(award, solicitation)
            enhanced_awards.append(enhanced_award)

        return enhanced_awards
