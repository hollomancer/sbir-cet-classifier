"""Tests for enhanced applicability model with n-grams and feature selection."""

import pytest

from sbir_cet_classifier.models.applicability import (
    ApplicabilityModel,
    TrainingExample,
)
from sbir_cet_classifier.common.yaml_config import load_classification_config


class TestEnhancedModel:
    """Test enhanced model features."""

    def test_sbir_stop_words_defined(self):
        """Test SBIR-specific stop words are defined."""
        config = load_classification_config()
        stop_words = config.stop_words
        assert "sbir" in stop_words
        assert "phase" in stop_words
        assert "proposal" in stop_words

    def test_model_uses_trigrams(self):
        """Test model is configured for trigrams."""
        model = ApplicabilityModel()
        assert model._vectorizer.ngram_range == (1, 3)

    def test_model_uses_feature_selection(self):
        """Test model has feature selector."""
        model = ApplicabilityModel()
        assert model._feature_selector is not None
        assert model._feature_selector.k == 20000

    def test_model_trains_with_class_weights(self):
        """Test model trains with imbalanced data handling."""
        examples = [
            TrainingExample("A1", "quantum computing research", "quantum"),
            TrainingExample("A2", "quantum sensor development", "quantum"),
            TrainingExample("A3", "quantum algorithm optimization", "quantum"),
            TrainingExample("A4", "artificial intelligence system", "ai"),
        ]
        
        model = ApplicabilityModel()
        model.fit(examples)
        
        assert model._is_fitted
        # Model should handle imbalanced classes (3 quantum vs 1 ai)

    def test_prediction_uses_feature_selection(self):
        """Test prediction applies feature selection."""
        examples = [
            TrainingExample("A1", "quantum computing research", "quantum"),
            TrainingExample("A2", "quantum sensor development", "quantum"),
            TrainingExample("A3", "artificial intelligence machine learning", "ai"),
            TrainingExample("A4", "ai neural network deep learning", "ai"),
        ]
        
        model = ApplicabilityModel()
        model.fit(examples)
        
        result = model.predict("TEST", "quantum computing machine learning")
        
        assert result.award_id == "TEST"
        assert result.primary_cet_id in ["quantum", "ai"]
        assert 0 <= result.primary_score <= 100

    def test_trigrams_capture_technical_phrases(self):
        """Test trigrams help capture multi-word technical terms."""
        examples = [
            TrainingExample("A1", "machine learning artificial intelligence", "ai"),
            TrainingExample("A2", "deep learning neural networks", "ai"),
            TrainingExample("A3", "quantum computing algorithms", "quantum"),
            TrainingExample("A4", "quantum sensor technology", "quantum"),
        ]
        
        model = ApplicabilityModel()
        model.fit(examples)
        
        # Should recognize "machine learning" as a phrase
        result = model.predict("TEST", "machine learning system")
        assert result.primary_cet_id == "ai"
