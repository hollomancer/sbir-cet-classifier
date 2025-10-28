"""Tests for confidence scoring in awardee matches."""

import pytest
from unittest.mock import Mock

from sbir_cet_classifier.data.enrichment.confidence_scoring import (
    ConfidenceScorer,
    MatchFactor,
    ScoreWeights,
)


class TestConfidenceScorer:
    """Test confidence scoring functionality."""

    @pytest.fixture
    def scorer(self):
        """Create confidence scorer instance."""
        return ConfidenceScorer()

    def test_perfect_match_score(self, scorer):
        """Test perfect match confidence score."""
        match_factors = {
            MatchFactor.UEI_EXACT: True,
            MatchFactor.NAME_EXACT: True,
            MatchFactor.AWARD_NUMBER_EXACT: True,
            MatchFactor.ADDRESS_SIMILARITY: 1.0,
        }

        score = scorer.calculate_score(match_factors)

        assert score == 1.0

    def test_uei_only_match_score(self, scorer):
        """Test UEI-only match confidence score."""
        match_factors = {
            MatchFactor.UEI_EXACT: True,
            MatchFactor.NAME_EXACT: False,
            MatchFactor.AWARD_NUMBER_EXACT: False,
            MatchFactor.NAME_SIMILARITY: 0.3,
        }

        score = scorer.calculate_score(match_factors)

        # UEI match should yield medium confidence with default weights
        assert 0.5 <= score < 0.8

    def test_name_only_match_score(self, scorer):
        """Test name-only match confidence score."""
        match_factors = {
            MatchFactor.UEI_EXACT: False,
            MatchFactor.NAME_EXACT: True,
            MatchFactor.AWARD_NUMBER_EXACT: False,
        }

        score = scorer.calculate_score(match_factors)

        # Name-only match should have moderate confidence
        assert score == 0.3

    def test_fuzzy_name_match_score(self, scorer):
        """Test fuzzy name match confidence score."""
        match_factors = {
            MatchFactor.UEI_EXACT: False,
            MatchFactor.NAME_EXACT: False,
            MatchFactor.NAME_SIMILARITY: 0.85,
            MatchFactor.AWARD_NUMBER_EXACT: False,
        }

        score = scorer.calculate_score(match_factors)

        # High name similarity should give decent confidence
        assert 0.5 <= score <= 0.8

    def test_low_similarity_score(self, scorer):
        """Test low similarity confidence score."""
        match_factors = {
            MatchFactor.UEI_EXACT: False,
            MatchFactor.NAME_EXACT: False,
            MatchFactor.NAME_SIMILARITY: 0.3,
            MatchFactor.AWARD_NUMBER_EXACT: False,
            MatchFactor.ADDRESS_SIMILARITY: 0.2,
        }

        score = scorer.calculate_score(match_factors)

        # Low similarities should result in low confidence
        assert score <= 0.5

    def test_award_number_boost(self, scorer):
        """Test award number match boosting confidence."""
        # Base match without award number
        base_factors = {
            MatchFactor.UEI_EXACT: False,
            MatchFactor.NAME_SIMILARITY: 0.7,
            MatchFactor.AWARD_NUMBER_EXACT: False,
        }

        base_score = scorer.calculate_score(base_factors)

        # Same match with award number
        boosted_factors = base_factors.copy()
        boosted_factors[MatchFactor.AWARD_NUMBER_EXACT] = True

        boosted_score = scorer.calculate_score(boosted_factors)

        # Award number should boost confidence
        assert boosted_score > base_score
        assert boosted_score - base_score >= 0.1  # Significant boost

    def test_address_similarity_contribution(self, scorer):
        """Test address similarity contribution to confidence."""
        base_factors = {
            MatchFactor.UEI_EXACT: False,
            MatchFactor.NAME_SIMILARITY: 0.6,
            MatchFactor.ADDRESS_SIMILARITY: 0.0,
        }

        base_score = scorer.calculate_score(base_factors)

        # Add high address similarity
        enhanced_factors = base_factors.copy()
        enhanced_factors[MatchFactor.ADDRESS_SIMILARITY] = 0.9

        enhanced_score = scorer.calculate_score(enhanced_factors)

        # Address similarity should contribute to confidence
        assert enhanced_score > base_score

    def test_custom_weights(self, scorer):
        """Test custom scoring weights."""
        # Create scorer with custom weights
        custom_weights = ScoreWeights(
            uei_exact=0.8,
            name_exact=0.6,
            name_similarity=0.4,
            award_number_exact=0.3,
            address_similarity=0.2,
        )

        custom_scorer = ConfidenceScorer(weights=custom_weights)

        match_factors = {
            MatchFactor.UEI_EXACT: True,
            MatchFactor.NAME_EXACT: False,
            MatchFactor.NAME_SIMILARITY: 0.5,
        }

        default_score = scorer.calculate_score(match_factors)
        custom_score = custom_scorer.calculate_score(match_factors)

        # Scores should be different due to different weights
        assert default_score != custom_score

    def test_score_normalization(self, scorer):
        """Test that scores are properly normalized."""
        # Test various combinations to ensure scores stay within bounds
        test_cases = [
            {
                MatchFactor.UEI_EXACT: True,
                MatchFactor.NAME_EXACT: True,
                MatchFactor.AWARD_NUMBER_EXACT: True,
            },
            {MatchFactor.NAME_SIMILARITY: 1.0, MatchFactor.ADDRESS_SIMILARITY: 1.0},
            {MatchFactor.UEI_EXACT: False, MatchFactor.NAME_SIMILARITY: 0.0},
        ]

        for factors in test_cases:
            score = scorer.calculate_score(factors)
            assert 0.0 <= score <= 1.0

    def test_missing_factors_handling(self, scorer):
        """Test handling of missing match factors."""
        # Empty factors
        score = scorer.calculate_score({})
        assert score == 0.0

        # Partial factors
        partial_factors = {MatchFactor.NAME_SIMILARITY: 0.7}
        score = scorer.calculate_score(partial_factors)
        assert 0.0 < score < 1.0

    def test_confidence_thresholds(self, scorer):
        """Test confidence threshold classifications."""
        # High confidence threshold
        high_confidence_factors = {MatchFactor.UEI_EXACT: True, MatchFactor.NAME_SIMILARITY: 0.9}

        score = scorer.calculate_score(high_confidence_factors)
        confidence_level = scorer.get_confidence_level(score)

        assert confidence_level == "high"

        # Medium confidence threshold
        medium_confidence_factors = {
            MatchFactor.NAME_SIMILARITY: 0.7,
            MatchFactor.ADDRESS_SIMILARITY: 0.6,
        }

        score = scorer.calculate_score(medium_confidence_factors)
        confidence_level = scorer.get_confidence_level(score)

        assert confidence_level == "medium"

        # Low confidence threshold
        low_confidence_factors = {MatchFactor.NAME_SIMILARITY: 0.4}

        score = scorer.calculate_score(low_confidence_factors)
        confidence_level = scorer.get_confidence_level(score)

        assert confidence_level == "low"


class TestMatchFactor:
    """Test MatchFactor enum."""

    def test_match_factor_values(self):
        """Test match factor enum values."""
        assert MatchFactor.UEI_EXACT.value == "uei_exact"
        assert MatchFactor.NAME_EXACT.value == "name_exact"
        assert MatchFactor.NAME_SIMILARITY.value == "name_similarity"
        assert MatchFactor.AWARD_NUMBER_EXACT.value == "award_number_exact"
        assert MatchFactor.ADDRESS_SIMILARITY.value == "address_similarity"

    def test_match_factor_from_string(self):
        """Test creating match factor from string."""
        assert MatchFactor("uei_exact") == MatchFactor.UEI_EXACT
        assert MatchFactor("name_similarity") == MatchFactor.NAME_SIMILARITY


class TestScoreWeights:
    """Test ScoreWeights configuration."""

    def test_default_weights(self):
        """Test default weight values."""
        weights = ScoreWeights()

        assert weights.uei_exact == 0.5
        assert weights.name_exact == 0.3
        assert weights.name_similarity == 0.2
        assert weights.award_number_exact == 0.2
        assert weights.address_similarity == 0.1

    def test_custom_weights(self):
        """Test custom weight values."""
        weights = ScoreWeights(
            uei_exact=0.6,
            name_exact=0.4,
            name_similarity=0.3,
            award_number_exact=0.25,
            address_similarity=0.15,
        )

        assert weights.uei_exact == 0.6
        assert weights.name_exact == 0.4
        assert weights.name_similarity == 0.3
        assert weights.award_number_exact == 0.25
        assert weights.address_similarity == 0.15

    def test_weight_validation(self):
        """Test weight validation."""
        # Negative weights should raise error
        with pytest.raises(ValueError):
            ScoreWeights(uei_exact=-0.1)

        # Weights > 1.0 should raise error
        with pytest.raises(ValueError):
            ScoreWeights(name_exact=1.5)


class TestConfidenceScoringIntegration:
    """Test confidence scoring integration scenarios."""

    @pytest.fixture
    def scorer(self):
        """Create confidence scorer instance."""
        return ConfidenceScorer()

    def test_real_world_scenario_high_confidence(self, scorer):
        """Test real-world high confidence scenario."""
        # Scenario: UEI match + high name similarity + award number match
        match_factors = {
            MatchFactor.UEI_EXACT: True,
            MatchFactor.NAME_SIMILARITY: 0.95,
            MatchFactor.AWARD_NUMBER_EXACT: True,
            MatchFactor.ADDRESS_SIMILARITY: 0.8,
        }

        score = scorer.calculate_score(match_factors)
        confidence_level = scorer.get_confidence_level(score)

        assert confidence_level == "high"
        assert score >= 0.9

    def test_real_world_scenario_medium_confidence(self, scorer):
        """Test real-world medium confidence scenario."""
        # Scenario: Good name similarity + some address match, no UEI
        match_factors = {
            MatchFactor.UEI_EXACT: False,
            MatchFactor.NAME_SIMILARITY: 0.8,
            MatchFactor.ADDRESS_SIMILARITY: 0.7,
            MatchFactor.AWARD_NUMBER_EXACT: False,
        }

        score = scorer.calculate_score(match_factors)
        confidence_level = scorer.get_confidence_level(score)

        assert confidence_level in ["medium", "high"]
        assert 0.5 <= score <= 0.9

    def test_real_world_scenario_low_confidence(self, scorer):
        """Test real-world low confidence scenario."""
        # Scenario: Only weak name similarity
        match_factors = {
            MatchFactor.UEI_EXACT: False,
            MatchFactor.NAME_SIMILARITY: 0.5,
            MatchFactor.ADDRESS_SIMILARITY: 0.3,
            MatchFactor.AWARD_NUMBER_EXACT: False,
        }

        score = scorer.calculate_score(match_factors)
        confidence_level = scorer.get_confidence_level(score)

        assert confidence_level in ["low", "medium"]
        assert score <= 0.7

    def test_batch_scoring_performance(self, scorer):
        """Test batch scoring performance."""
        # Create multiple match scenarios
        batch_factors = []
        for i in range(1000):
            factors = {
                MatchFactor.UEI_EXACT: i % 2 == 0,
                MatchFactor.NAME_SIMILARITY: (i % 100) / 100.0,
                MatchFactor.AWARD_NUMBER_EXACT: i % 3 == 0,
            }
            batch_factors.append(factors)

        # Time the batch scoring
        import time

        start_time = time.time()

        scores = [scorer.calculate_score(factors) for factors in batch_factors]

        end_time = time.time()

        # Should complete quickly
        assert end_time - start_time < 1.0  # Less than 1 second
        assert len(scores) == 1000
        assert all(0.0 <= score <= 1.0 for score in scores)
