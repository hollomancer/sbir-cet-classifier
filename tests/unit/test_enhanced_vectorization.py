"""Tests for solicitation-enhanced TF-IDF vectorization."""

import pytest
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from sbir_cet_classifier.models.vectorizers import MultiSourceTextVectorizer


class TestMultiSourceTextVectorizer:
    """Test canonical MultiSourceTextVectorizer."""

    @pytest.fixture
    def vectorizer(self):
        """Create multi-source TF-IDF vectorizer."""
        return MultiSourceTextVectorizer(
            abstract_weight=0.5,
            keywords_weight=0.2,
            solicitation_weight=0.3,
            include_solicitation=True,
            max_features=1000,
            ngram_range=(1, 2),
        )

    @pytest.fixture
    def sample_documents(self):
        """Sample documents for testing."""
        return [
            {
                "abstract": "Quantum computing algorithms for secure cryptographic applications",
                "keywords": "quantum computing, cryptography, security, algorithms",
                "solicitation_text": "Advanced quantum cryptographic systems for secure communications",
            },
            {
                "abstract": "Machine learning techniques for autonomous vehicle navigation systems",
                "keywords": "machine learning, autonomous vehicles, navigation, AI",
                "solicitation_text": "Artificial intelligence systems for autonomous transportation and navigation",
            },
            {
                "abstract": "Advanced materials research for aerospace applications and composites",
                "keywords": "advanced materials, aerospace, composites, nanotechnology",
                "solicitation_text": "Novel materials and nanotechnology for next-generation aerospace systems",
            },
        ]

    def test_vectorizer_initialization(self, vectorizer):
        """Test vectorizer initialization (basic)."""
        # Basic sanity: not fitted yet; fitting should succeed
        assert not vectorizer.is_fitted_
        X = vectorizer.fit_transform([{"abstract": "a", "keywords": "b", "solicitation_text": "c"}])
        assert X.shape[0] == 1

    def test_fit_vectorizer(self, vectorizer, sample_documents):
        """Test fitting the vectorizer."""
        vectorizer.fit(sample_documents)

        assert vectorizer.is_fitted_
        feature_names = vectorizer.get_feature_names_out()
        assert len(feature_names) > 0

    def test_transform_documents(self, vectorizer, sample_documents):
        """Test transforming documents to feature vectors."""
        vectorizer.fit(sample_documents)
        X = vectorizer.transform(sample_documents)

        assert isinstance(X, csr_matrix)
        assert X.shape[0] == len(sample_documents)
        feature_names = vectorizer.get_feature_names_out()
        assert X.shape[1] == len(feature_names)

    def test_fit_transform(self, vectorizer, sample_documents):
        """Test fit_transform method."""
        X = vectorizer.fit_transform(sample_documents)

        assert isinstance(X, csr_matrix)
        assert X.shape[0] == len(sample_documents)
        assert vectorizer.is_fitted_

    def test_feature_names_output(self, vectorizer, sample_documents):
        """Test feature names generation."""
        vectorizer.fit(sample_documents)
        feature_names = vectorizer.get_feature_names_out()

        assert len(feature_names) == len(vectorizer.feature_names_)
        assert all(isinstance(name, str) for name in feature_names)

        # Should include features from all text sources
        prefixes = ["abstract_", "keywords_", "solicitation_"]
        for prefix in prefixes:
            assert any(name.startswith(prefix) for name in feature_names)

    def test_weighted_feature_combination(self, vectorizer, sample_documents):
        """Test weighted combination produces non-empty feature space."""
        vectorizer.fit(sample_documents)
        X = vectorizer.transform(sample_documents)
        assert X.shape[1] > 0

    def test_ngram_feature_extraction(self, sample_documents):
        """Test n-gram feature extraction."""
        vectorizer = MultiSourceTextVectorizer(
            ngram_range=(1, 3),  # Unigrams, bigrams, trigrams
            max_features=2000,
            include_solicitation=True,
        )

        vectorizer.fit(sample_documents)
        feature_names = vectorizer.get_feature_names_out()

        # Should include unigrams, bigrams, and trigrams
        unigrams = [name for name in feature_names if len(name.split("_")[-1].split()) == 1]
        bigrams = [name for name in feature_names if len(name.split("_")[-1].split()) == 2]
        trigrams = [name for name in feature_names if len(name.split("_")[-1].split()) == 3]

        assert len(unigrams) > 0
        assert len(bigrams) > 0
        assert len(trigrams) > 0

    def test_max_features_constraint(self, sample_documents):
        """Test max_features constraint."""
        vectorizer = MultiSourceTextVectorizer(max_features=50, include_solicitation=True)
        vectorizer.fit(sample_documents)

        feature_names = vectorizer.get_feature_names_out()
        assert len(feature_names) <= 50

    def test_empty_text_handling(self, vectorizer):
        """Test handling of empty text fields."""
        documents_with_empty = [
            {
                "abstract": "Valid abstract text",
                "keywords": "",  # Empty
                "solicitation_text": "Valid solicitation text",
            },
            {
                "abstract": "",  # Empty
                "keywords": "valid, keywords",
                "solicitation_text": "",  # Empty
            },
        ]

        vectorizer.fit(documents_with_empty)
        X = vectorizer.transform(documents_with_empty)

        assert X.shape[0] == 2
        assert X.shape[1] > 0

    def test_vocabulary_access(self, vectorizer, sample_documents):
        """Test vocabulary access via feature names."""
        vectorizer.fit(sample_documents)
        feature_names = vectorizer.get_feature_names_out()

        assert isinstance(feature_names, list)
        assert len(feature_names) > 0
        assert all(isinstance(name, str) for name in feature_names)


# Removed tests for WeightedTextCombiner; superseded by MultiSourceTextVectorizer
