"""Tests for solicitation-enhanced TF-IDF vectorization."""

import pytest
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer

from src.sbir_cet_classifier.models.vectorizers import MultiSourceTextVectorizer
from src.sbir_cet_classifier.models.enhanced_vectorization import CETAwareTfidfVectorizer


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


class TestCETAwareTfidfVectorizer:
    """Test CETAwareTfidfVectorizer."""

    @pytest.fixture
    def vectorizer(self):
        """Create CET-aware TF-IDF vectorizer."""
        return CETAwareTfidfVectorizer(
            cet_keywords_boost=2.0, technical_terms_boost=1.5, max_features=1000
        )

    @pytest.fixture
    def sample_documents(self):
        """Sample documents with CET-relevant content."""
        return [
            "Quantum computing algorithms for cryptographic security applications",
            "Machine learning and artificial intelligence for autonomous systems",
            "Advanced materials and nanotechnology for aerospace composites",
            "Cybersecurity protocols for secure communications networks",
        ]

    def test_cet_keyword_identification(self, vectorizer, sample_documents):
        """Test identification of CET-relevant keywords."""
        vectorizer.fit(sample_documents)

        cet_keywords = vectorizer.get_cet_keywords()

        expected_cet_terms = [
            "quantum",
            "computing",
            "machine learning",
            "artificial intelligence",
            "advanced materials",
            "nanotechnology",
            "cybersecurity",
        ]

        for term in expected_cet_terms:
            assert any(term in keyword for keyword in cet_keywords)

    def test_keyword_boosting(self, vectorizer, sample_documents):
        """Test boosting of CET keywords."""
        vectorizer.fit(sample_documents)
        X = vectorizer.transform(sample_documents)

        # Get feature names and find CET-related features
        feature_names = vectorizer.get_feature_names_out()
        quantum_idx = next((i for i, name in enumerate(feature_names) if "quantum" in name), None)

        if quantum_idx is not None:
            # Quantum-related document should have higher score for quantum features
            quantum_doc_idx = 0  # First document mentions quantum
            quantum_score = X[quantum_doc_idx, quantum_idx]

            # Score should be boosted
            assert quantum_score > 0

    def test_technical_terms_boost(self, vectorizer, sample_documents):
        """Test boosting of technical terms."""
        vectorizer.fit(sample_documents)

        technical_terms = vectorizer.get_technical_terms()

        expected_technical = [
            "algorithms",
            "protocols",
            "systems",
            "applications",
            "networks",
            "composites",
        ]

        for term in expected_technical:
            assert any(term in tech_term for tech_term in technical_terms)

    def test_feature_importance_ranking(self, vectorizer, sample_documents):
        """Test ranking of features by CET importance."""
        vectorizer.fit(sample_documents)

        importance_scores = vectorizer.get_feature_importance()

        assert isinstance(importance_scores, dict)
        assert len(importance_scores) > 0

        # CET-related terms should have higher importance
        cet_terms = ["quantum", "artificial", "nanotechnology", "cybersecurity"]
        non_cet_terms = ["for", "and", "the", "of"]

        cet_scores = [importance_scores.get(term, 0) for term in cet_terms]
        non_cet_scores = [importance_scores.get(term, 0) for term in non_cet_terms]

        if cet_scores and non_cet_scores:
            assert max(cet_scores) > max(non_cet_scores)

    def test_custom_cet_vocabulary(self):
        """Test using custom CET vocabulary."""
        custom_cet_terms = ["quantum", "ai", "nanotech", "cyber"]

        vectorizer = CETAwareTfidfVectorizer(
            custom_cet_vocabulary=custom_cet_terms, cet_keywords_boost=3.0
        )

        documents = ["quantum ai research", "nanotech cyber security"]
        vectorizer.fit(documents)

        cet_keywords = vectorizer.get_cet_keywords()
        for term in custom_cet_terms:
            assert term in cet_keywords

    def test_boost_factor_validation(self):
        """Test validation of boost factors."""
        with pytest.raises(ValueError):
            CETAwareTfidfVectorizer(cet_keywords_boost=0)  # Should be > 1

        with pytest.raises(ValueError):
            CETAwareTfidfVectorizer(technical_terms_boost=0.5)  # Should be >= 1

    def test_vocabulary_size_control(self, sample_documents):
        """Test vocabulary size control with boosting."""
        vectorizer = CETAwareTfidfVectorizer(max_features=20)
        vectorizer.fit(sample_documents)

        feature_names = vectorizer.get_feature_names_out()
        assert len(feature_names) <= 20

        # CET terms should be prioritized in limited vocabulary
        cet_terms_present = sum(
            1
            for name in feature_names
            if any(cet in name.lower() for cet in ["quantum", "machine", "artificial", "cyber"])
        )
        assert cet_terms_present > 0
