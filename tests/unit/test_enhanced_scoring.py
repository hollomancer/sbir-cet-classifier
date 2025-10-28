"""Tests for enhanced CET classifier with solicitation text."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from sbir_cet_classifier.models.enhanced_scoring import (
    EnhancedCETClassifier,
    SolicitationEnhancedScorer,
)
from sbir_cet_classifier.models.vectorizers import MultiSourceTextVectorizer


class TestEnhancedCETClassifier:
    """Test EnhancedCETClassifier."""

    @pytest.fixture
    def sample_awards_data(self):
        """Sample awards data for testing."""
        return [
            {
                "award_id": "AWARD-001",
                "abstract": "Quantum computing research for cryptographic applications",
                "keywords": "quantum, cryptography, security",
                "solicitation_text": "Advanced quantum algorithms for secure communications",
            },
            {
                "award_id": "AWARD-002",
                "abstract": "Machine learning for autonomous vehicle navigation",
                "keywords": "AI, autonomous, navigation",
                "solicitation_text": "Artificial intelligence systems for autonomous transportation",
            },
        ]

    @pytest.fixture
    def sample_cet_labels(self):
        """Sample CET labels for testing."""
        return ["quantum_computing", "artificial_intelligence"]

    @pytest.fixture
    def classifier(self):
        """Create enhanced CET classifier."""
        return EnhancedCETClassifier(
            include_solicitation_text=True,
            solicitation_weight=0.3,
            abstract_weight=0.5,
            keywords_weight=0.2,
        )

    def test_classifier_initialization(self, classifier):
        """Test classifier initialization."""
        assert classifier.include_solicitation_text is True
        assert classifier.solicitation_weight == 0.3
        assert classifier.abstract_weight == 0.5
        assert classifier.keywords_weight == 0.2
        assert (
            classifier.solicitation_weight + classifier.abstract_weight + classifier.keywords_weight
            == 1.0
        )

    def test_weight_validation(self):
        """Test weight validation during initialization."""
        with pytest.raises(ValueError) as exc_info:
            EnhancedCETClassifier(
                solicitation_weight=0.5,
                abstract_weight=0.5,
                keywords_weight=0.2,  # Sum > 1.0
            )
        assert "Weights must sum to 1.0" in str(exc_info.value)

    def test_prepare_training_data(self, classifier, sample_awards_data, sample_cet_labels):
        """Test preparation of training data."""
        X, feature_names = classifier.prepare_training_data(sample_awards_data)

        assert X.shape[0] == len(sample_awards_data)
        assert X.shape[1] > 0  # Should have features
        assert len(feature_names) == X.shape[1]

        # Should include features from all text sources
        assert any("abstract_" in name for name in feature_names)
        assert any("keywords_" in name for name in feature_names)
        assert any("solicitation_" in name for name in feature_names)

    def test_fit_classifier(self, classifier, sample_awards_data, sample_cet_labels):
        """Test fitting the classifier."""
        # Expand labels to match number of samples
        y = np.array([0, 1])  # quantum_computing, artificial_intelligence

        classifier.fit(sample_awards_data, y, sample_cet_labels)

        assert classifier.is_fitted
        assert hasattr(classifier, "vectorizer_")
        assert hasattr(classifier, "classifier_")
        assert len(classifier.cet_categories_) == len(sample_cet_labels)

    def test_predict_probabilities(self, classifier, sample_awards_data, sample_cet_labels):
        """Test probability prediction."""
        y = np.array([0, 1])
        classifier.fit(sample_awards_data, y, sample_cet_labels)

        # Test prediction on new data
        test_data = [
            {
                "award_id": "TEST-001",
                "abstract": "Quantum machine learning algorithms",
                "keywords": "quantum, ML, algorithms",
                "solicitation_text": "Quantum computing applications in AI",
            }
        ]

        probabilities = classifier.predict_proba(test_data)

        assert len(probabilities) == 1
        assert len(probabilities[0]) == len(sample_cet_labels)
        assert all(0 <= prob <= 1 for prob in probabilities[0])
        assert abs(sum(probabilities[0]) - 1.0) < 1e-6  # Should sum to 1

    def test_predict_top_categories(self, classifier, sample_awards_data, sample_cet_labels):
        """Test prediction of top CET categories."""
        y = np.array([0, 1])
        classifier.fit(sample_awards_data, y, sample_cet_labels)

        test_data = [
            {
                "award_id": "TEST-001",
                "abstract": "Quantum computing research",
                "keywords": "quantum, computing",
                "solicitation_text": "Advanced quantum algorithms",
            }
        ]

        top_categories = classifier.predict_top_categories(test_data[0], top_n=2)

        assert len(top_categories) <= 2
        assert all(isinstance(cat, tuple) and len(cat) == 2 for cat in top_categories)
        assert all(isinstance(cat[0], str) and isinstance(cat[1], float) for cat in top_categories)

    def test_feature_importance(self, classifier, sample_awards_data, sample_cet_labels):
        """Test feature importance extraction."""
        y = np.array([0, 1])
        classifier.fit(sample_awards_data, y, sample_cet_labels)

        importance = classifier.get_feature_importance()

        assert isinstance(importance, dict)
        assert len(importance) > 0
        assert all(isinstance(k, str) and isinstance(v, float) for k, v in importance.items())

    def test_solicitation_text_disabled(self):
        """Test classifier with solicitation text disabled."""
        classifier = EnhancedCETClassifier(
            include_solicitation_text=False, abstract_weight=0.7, keywords_weight=0.3
        )

        sample_data = [
            {
                "award_id": "AWARD-001",
                "abstract": "Test abstract",
                "keywords": "test, keywords",
                "solicitation_text": "This should be ignored",
            }
        ]

        X, feature_names = classifier.prepare_training_data(sample_data)

        # Should not include solicitation features
        assert not any("solicitation_" in name for name in feature_names)
        assert any("abstract_" in name for name in feature_names)
        assert any("keywords_" in name for name in feature_names)


class TestSolicitationEnhancedScorer:
    """Test SolicitationEnhancedScorer."""

    @pytest.fixture
    def scorer(self):
        """Create solicitation enhanced scorer."""
        return SolicitationEnhancedScorer()

    @pytest.fixture
    def sample_award(self):
        """Sample award data."""
        return {
            "award_id": "AWARD-001",
            "abstract": "Quantum computing research for secure communications",
            "keywords": "quantum, cryptography, security",
            "solicitation_id": "SOL-2024-001",
        }

    @pytest.fixture
    def sample_solicitation(self):
        """Sample solicitation data."""
        return {
            "solicitation_id": "SOL-2024-001",
            "full_text": "Advanced quantum algorithms for cryptographic applications",
            "technical_requirements": "Quantum error correction and cryptographic protocols",
            "cet_relevance_scores": {"quantum_computing": 0.95, "cybersecurity": 0.8},
        }

    def test_enhance_award_with_solicitation(self, scorer, sample_award, sample_solicitation):
        """Test enhancing award with solicitation data."""
        enhanced_award = scorer.enhance_award_with_solicitation(sample_award, sample_solicitation)

        assert "solicitation_text" in enhanced_award
        assert "solicitation_cet_scores" in enhanced_award
        assert enhanced_award["solicitation_text"] == sample_solicitation["full_text"]
        assert (
            enhanced_award["solicitation_cet_scores"] == sample_solicitation["cet_relevance_scores"]
        )

    def test_calculate_enhanced_scores(self, scorer, sample_award, sample_solicitation):
        """Test calculation of enhanced CET scores."""
        enhanced_award = scorer.enhance_award_with_solicitation(sample_award, sample_solicitation)

        # Mock the base classifier
        with patch.object(scorer, "base_classifier") as mock_classifier:
            mock_classifier.predict_proba.return_value = [[0.7, 0.3]]  # quantum, AI
            mock_classifier.cet_categories_ = ["quantum_computing", "artificial_intelligence"]

            enhanced_scores = scorer.calculate_enhanced_scores(enhanced_award)

            assert isinstance(enhanced_scores, dict)
            assert "quantum_computing" in enhanced_scores
            assert enhanced_scores["quantum_computing"] > 0.7  # Should be boosted by solicitation

    def test_combine_scores_with_solicitation_boost(self, scorer):
        """Test combining base scores with solicitation boost."""
        base_scores = {"quantum_computing": 0.6, "artificial_intelligence": 0.4}
        solicitation_scores = {"quantum_computing": 0.9, "cybersecurity": 0.7}

        combined_scores = scorer.combine_scores_with_solicitation_boost(
            base_scores, solicitation_scores, boost_factor=0.3
        )

        # Quantum should be boosted
        assert combined_scores["quantum_computing"] > base_scores["quantum_computing"]

        # AI should remain similar (no solicitation boost)
        assert (
            abs(combined_scores["artificial_intelligence"] - base_scores["artificial_intelligence"])
            < 0.1
        )

        # Cybersecurity should appear with solicitation influence
        assert "cybersecurity" in combined_scores

    def test_missing_solicitation_handling(self, scorer, sample_award):
        """Test handling of missing solicitation data."""
        enhanced_award = scorer.enhance_award_with_solicitation(sample_award, None)

        assert enhanced_award["solicitation_text"] == ""
        assert enhanced_award["solicitation_cet_scores"] == {}

    def test_batch_enhancement(self, scorer):
        """Test batch enhancement of multiple awards."""
        awards = [
            {"award_id": "A1", "abstract": "Quantum research", "solicitation_id": "S1"},
            {"award_id": "A2", "abstract": "AI research", "solicitation_id": "S2"},
        ]

        solicitations = {
            "S1": {
                "solicitation_id": "S1",
                "full_text": "Quantum text",
                "cet_relevance_scores": {"quantum_computing": 0.9},
            },
            "S2": {
                "solicitation_id": "S2",
                "full_text": "AI text",
                "cet_relevance_scores": {"artificial_intelligence": 0.9},
            },
        }

        enhanced_awards = scorer.batch_enhance_awards(awards, solicitations)

        assert len(enhanced_awards) == 2
        assert enhanced_awards[0]["solicitation_text"] == "Quantum text"
        assert enhanced_awards[1]["solicitation_text"] == "AI text"


class TestMultiSourceTextVectorizer:
    """Test MultiSourceTextVectorizer."""

    @pytest.fixture
    def vectorizer(self):
        """Create multi-source text vectorizer."""
        return MultiSourceTextVectorizer(
            abstract_weight=0.5, keywords_weight=0.2, solicitation_weight=0.3
        )

    @pytest.fixture
    def sample_documents(self):
        """Sample documents for vectorization."""
        return [
            {
                "abstract": "Quantum computing algorithms for cryptography",
                "keywords": "quantum, crypto, algorithms",
                "solicitation_text": "Advanced quantum cryptographic systems",
            },
            {
                "abstract": "Machine learning for autonomous systems",
                "keywords": "ML, autonomous, systems",
                "solicitation_text": "AI-driven autonomous vehicle navigation",
            },
        ]

    def test_vectorizer_fit(self, vectorizer, sample_documents):
        """Test fitting the vectorizer."""
        vectorizer.fit(sample_documents)

        assert vectorizer.is_fitted_
        assert hasattr(vectorizer, "abstract_vectorizer")
        assert hasattr(vectorizer, "keywords_vectorizer")
        assert hasattr(vectorizer, "solicitation_vectorizer")

    def test_vectorizer_transform(self, vectorizer, sample_documents):
        """Test transforming documents to feature vectors."""
        vectorizer.fit(sample_documents)
        X = vectorizer.transform(sample_documents)

        assert X.shape[0] == len(sample_documents)
        assert X.shape[1] > 0

        # Should be sparse matrix
        assert hasattr(X, "toarray")

    def test_get_feature_names(self, vectorizer, sample_documents):
        """Test getting feature names."""
        vectorizer.fit(sample_documents)
        feature_names = vectorizer.get_feature_names_out()

        assert len(feature_names) > 0
        assert any(name.startswith("abstract_") for name in feature_names)
        assert any(name.startswith("keywords_") for name in feature_names)
        assert any(name.startswith("solicitation_") for name in feature_names)

    def test_weighted_combination(self, vectorizer, sample_documents):
        """Test weighted combination of different text sources."""
        vectorizer.fit(sample_documents)
        X = vectorizer.transform(sample_documents)

        # Transform individual sources
        abstract_X = vectorizer.abstract_vectorizer.transform(
            [doc["abstract"] for doc in sample_documents]
        )
        keywords_X = vectorizer.keywords_vectorizer.transform(
            [doc["keywords"] for doc in sample_documents]
        )
        solicitation_X = vectorizer.solicitation_vectorizer.transform(
            [doc["solicitation_text"] for doc in sample_documents]
        )

        # Combined matrix should reflect weighted combination
        assert X.shape[1] == (abstract_X.shape[1] + keywords_X.shape[1] + solicitation_X.shape[1])

    def test_missing_text_handling(self, vectorizer):
        """Test handling of missing text fields."""
        documents_with_missing = [
            {
                "abstract": "Complete abstract text",
                "keywords": "",  # Empty keywords
                "solicitation_text": "Solicitation text",
            },
            {
                "abstract": "",  # Empty abstract
                "keywords": "some, keywords",
                "solicitation_text": "",  # Empty solicitation
            },
        ]

        vectorizer.fit(documents_with_missing)
        X = vectorizer.transform(documents_with_missing)

        assert X.shape[0] == 2
        assert X.shape[1] > 0
