"""Tests for awardee data matching logic."""

import pytest
from unittest.mock import Mock, patch
from decimal import Decimal

from sbir_cet_classifier.data.enrichment.awardee_matching import (
    AwardeeDataMatcher,
    MatchStrategy,
    MatchResult,
    FuzzyNameMatcher,
    UEIMatcher,
    AwardNumberMatcher,
)


class TestUEIMatcher:
    """Test UEI-based matching."""

    @pytest.fixture
    def uei_matcher(self):
        """Create UEI matcher instance."""
        return UEIMatcher()

    def test_exact_uei_match(self, uei_matcher):
        """Test exact UEI matching."""
        award_data = {"award_id": "AWARD-001", "awardee_uei": "ABC123DEF456"}

        sam_entity = {"ueiSAM": "ABC123DEF456", "legalBusinessName": "Tech Innovations LLC"}

        result = uei_matcher.match(award_data, sam_entity)

        assert result.is_match is True
        assert result.confidence_score == 1.0
        assert result.match_method == "exact_uei"

    def test_uei_mismatch(self, uei_matcher):
        """Test UEI mismatch."""
        award_data = {"award_id": "AWARD-001", "awardee_uei": "ABC123DEF456"}

        sam_entity = {"ueiSAM": "XYZ789GHI012", "legalBusinessName": "Different Company"}

        result = uei_matcher.match(award_data, sam_entity)

        assert result.is_match is False
        assert result.confidence_score == 0.0

    def test_missing_uei_in_award(self, uei_matcher):
        """Test handling missing UEI in award data."""
        award_data = {"award_id": "AWARD-001", "awardee_uei": None}

        sam_entity = {"ueiSAM": "ABC123DEF456", "legalBusinessName": "Tech Innovations LLC"}

        result = uei_matcher.match(award_data, sam_entity)

        assert result.is_match is False
        assert result.confidence_score == 0.0

    def test_missing_uei_in_sam_entity(self, uei_matcher):
        """Test handling missing UEI in SAM entity."""
        award_data = {"award_id": "AWARD-001", "awardee_uei": "ABC123DEF456"}

        sam_entity = {
            "legalBusinessName": "Tech Innovations LLC"
            # Missing ueiSAM field
        }

        result = uei_matcher.match(award_data, sam_entity)

        assert result.is_match is False
        assert result.confidence_score == 0.0


class TestFuzzyNameMatcher:
    """Test fuzzy name matching."""

    @pytest.fixture
    def name_matcher(self):
        """Create fuzzy name matcher instance."""
        return FuzzyNameMatcher(threshold=0.8)

    def test_exact_name_match(self, name_matcher):
        """Test exact name matching."""
        award_data = {"award_id": "AWARD-001", "awardee_name": "Tech Innovations LLC"}

        sam_entity = {"ueiSAM": "ABC123DEF456", "legalBusinessName": "Tech Innovations LLC"}

        result = name_matcher.match(award_data, sam_entity)

        assert result.is_match is True
        assert result.confidence_score == 1.0
        assert result.match_method == "exact_name"

    def test_fuzzy_name_match(self, name_matcher):
        """Test fuzzy name matching with high similarity."""
        award_data = {
            "award_id": "AWARD-001",
            "awardee_name": "Tech Innovations LLC",
        }

        sam_entity = {
            "ueiSAM": "ABC123DEF456",
            "legalBusinessName": "Tech Innovations, LLC",  # Slight difference (comma, space)
        }

        result = name_matcher.match(award_data, sam_entity)

        assert result.is_match is True
        assert result.confidence_score > 0.8
        # After normalization, these may be exact matches or fuzzy matches
        assert result.match_method in ["exact_name", "fuzzy_name"]

    def test_name_mismatch_below_threshold(self, name_matcher):
        """Test name mismatch below threshold."""
        award_data = {"award_id": "AWARD-001", "awardee_name": "Tech Innovations LLC"}

        sam_entity = {
            "ueiSAM": "ABC123DEF456",
            "legalBusinessName": "Completely Different Company Inc",
        }

        result = name_matcher.match(award_data, sam_entity)

        assert result.is_match is False
        assert result.confidence_score < 0.8

    def test_name_normalization(self, name_matcher):
        """Test name normalization for matching."""
        award_data = {"award_id": "AWARD-001", "awardee_name": "TECH INNOVATIONS, INC."}

        sam_entity = {"ueiSAM": "ABC123DEF456", "legalBusinessName": "Tech Innovations Inc"}

        result = name_matcher.match(award_data, sam_entity)

        # Should match after normalization
        assert result.is_match is True
        assert result.confidence_score > 0.9

    def test_handle_missing_names(self, name_matcher):
        """Test handling missing name fields."""
        award_data = {"award_id": "AWARD-001", "awardee_name": None}

        sam_entity = {"ueiSAM": "ABC123DEF456", "legalBusinessName": "Tech Innovations LLC"}

        result = name_matcher.match(award_data, sam_entity)

        assert result.is_match is False
        assert result.confidence_score == 0.0


class TestAwardNumberMatcher:
    """Test award number matching."""

    @pytest.fixture
    def award_matcher(self):
        """Create award number matcher instance."""
        return AwardNumberMatcher()

    def test_exact_award_number_match(self, award_matcher):
        """Test exact award number matching."""
        award_data = {"award_id": "AWARD-001", "award_number": "1234567890"}

        sam_award = {"awardNumber": "1234567890", "awardAmount": 250000.00}

        result = award_matcher.match(award_data, sam_award)

        assert result.is_match is True
        assert result.confidence_score == 1.0
        assert result.match_method == "exact_award_number"

    def test_award_number_mismatch(self, award_matcher):
        """Test award number mismatch."""
        award_data = {"award_id": "AWARD-001", "award_number": "1234567890"}

        sam_award = {"awardNumber": "0987654321", "awardAmount": 250000.00}

        result = award_matcher.match(award_data, sam_award)

        assert result.is_match is False
        assert result.confidence_score == 0.0


class TestAwardeeDataMatcher:
    """Test comprehensive awardee data matching."""

    @pytest.fixture
    def mock_sam_client(self):
        """Mock SAM.gov API client."""
        return Mock()

    @pytest.fixture
    def data_matcher(self, mock_sam_client):
        """Create awardee data matcher instance."""
        return AwardeeDataMatcher(sam_client=mock_sam_client)

    def test_match_with_uei_strategy(self, data_matcher, mock_sam_client):
        """Test matching using UEI strategy."""
        award_data = {
            "award_id": "AWARD-001",
            "awardee_name": "Tech Innovations LLC",
            "awardee_uei": "ABC123DEF456",
        }

        # Mock SAM.gov response
        mock_sam_client.get_entity_by_uei.return_value = {
            "ueiSAM": "ABC123DEF456",
            "legalBusinessName": "Tech Innovations LLC",
            "entityStatus": "Active",
        }

        result = data_matcher.match_awardee(award_data, strategy=MatchStrategy.UEI_FIRST)

        assert result.is_match is True
        assert result.confidence_score >= 0.95
        assert result.matched_uei == "ABC123DEF456"
        mock_sam_client.get_entity_by_uei.assert_called_once_with("ABC123DEF456")

    def test_fallback_to_name_matching(self, data_matcher, mock_sam_client):
        """Test fallback to name matching when UEI fails."""
        award_data = {
            "award_id": "AWARD-001",
            "awardee_name": "Tech Innovations LLC",
            "awardee_uei": "INVALID_UEI",
        }

        # Mock SAM.gov responses
        mock_sam_client.get_entity_by_uei.return_value = None  # UEI not found
        mock_sam_client.search_entities.return_value = {
            "entities": [
                {
                    "ueiSAM": "ABC123DEF456",
                    "legalBusinessName": "Tech Innovations LLC",
                    "entityStatus": "Active",
                }
            ]
        }

        result = data_matcher.match_awardee(award_data, strategy=MatchStrategy.UEI_FIRST)

        assert result.is_match is True
        assert result.matched_uei == "ABC123DEF456"
        # Name matching succeeded (exact or fuzzy both indicate successful fallback)
        assert result.match_method in ["exact_name", "fuzzy_name"]
        mock_sam_client.search_entities.assert_called_once()

    def test_name_only_strategy(self, data_matcher, mock_sam_client):
        """Test name-only matching strategy."""
        award_data = {"award_id": "AWARD-001", "awardee_name": "Tech Innovations LLC"}

        # Mock SAM.gov response
        mock_sam_client.search_entities.return_value = {
            "entities": [
                {
                    "ueiSAM": "ABC123DEF456",
                    "legalBusinessName": "Tech Innovations LLC",
                    "entityStatus": "Active",
                }
            ]
        }

        result = data_matcher.match_awardee(award_data, strategy=MatchStrategy.NAME_ONLY)

        assert result.is_match is True
        assert result.matched_uei == "ABC123DEF456"
        mock_sam_client.search_entities.assert_called_once()
        # Should not call UEI search
        mock_sam_client.get_entity_by_uei.assert_not_called()

    def test_comprehensive_strategy(self, data_matcher, mock_sam_client):
        """Test comprehensive matching strategy."""
        award_data = {
            "award_id": "AWARD-001",
            "awardee_name": "Tech Innovations LLC",
            "awardee_uei": "ABC123DEF456",
            "award_number": "1234567890",
        }

        # Mock SAM.gov responses
        mock_sam_client.get_entity_by_uei.return_value = {
            "ueiSAM": "ABC123DEF456",
            "legalBusinessName": "Tech Innovations LLC",
            "entityStatus": "Active",
        }

        mock_sam_client.get_awards_by_uei.return_value = {
            "awards": [{"awardNumber": "1234567890", "awardAmount": 250000.00}]
        }

        result = data_matcher.match_awardee(award_data, strategy=MatchStrategy.COMPREHENSIVE)

        assert result.is_match is True
        assert result.confidence_score >= 0.98  # High confidence with multiple matches
        assert result.match_details["uei_match"] is True
        assert result.match_details["name_match"] is True
        assert result.match_details["award_number_match"] is True

    def test_no_match_found(self, data_matcher, mock_sam_client):
        """Test handling when no match is found."""
        award_data = {
            "award_id": "AWARD-001",
            "awardee_name": "Unknown Company",
            "awardee_uei": "UNKNOWN_UEI",
        }

        # Mock no results from SAM.gov
        mock_sam_client.get_entity_by_uei.return_value = None
        mock_sam_client.search_entities.return_value = {"entities": []}

        result = data_matcher.match_awardee(award_data, strategy=MatchStrategy.COMPREHENSIVE)

        assert result.is_match is False
        assert result.confidence_score == 0.0
        assert result.matched_uei is None

    def test_confidence_score_calculation(self, data_matcher):
        """Test confidence score calculation with multiple factors."""
        match_details = {
            "uei_match": True,
            "name_similarity": 0.95,
            "award_number_match": True,
            "address_similarity": 0.8,
        }

        confidence = data_matcher.calculate_confidence_score(match_details)

        # Should be high confidence with multiple strong matches
        assert confidence >= 0.95

        # Test with weaker matches
        match_details = {
            "uei_match": False,
            "name_similarity": 0.7,
            "award_number_match": False,
            "address_similarity": 0.6,
        }

        confidence = data_matcher.calculate_confidence_score(match_details)

        # Should be lower confidence
        assert 0.5 <= confidence <= 0.8

    def test_batch_matching(self, data_matcher, mock_sam_client):
        """Test batch matching of multiple awards."""
        awards = [
            {"award_id": "AWARD-001", "awardee_name": "Company A", "awardee_uei": "ABC123DEF456"},
            {"award_id": "AWARD-002", "awardee_name": "Company B", "awardee_uei": "XYZ789GHI012"},
        ]

        # Mock responses for both entities
        def mock_get_entity(uei):
            if uei == "ABC123DEF456":
                return {"ueiSAM": uei, "legalBusinessName": "Company A"}
            elif uei == "XYZ789GHI012":
                return {"ueiSAM": uei, "legalBusinessName": "Company B"}
            return None

        mock_sam_client.get_entity_by_uei.side_effect = mock_get_entity

        results = data_matcher.batch_match_awardees(awards)

        assert len(results) == 2
        assert all(result.is_match for result in results)
        assert results[0].matched_uei == "ABC123DEF456"
        assert results[1].matched_uei == "XYZ789GHI012"

    def test_match_result_serialization(self, data_matcher):
        """Test match result serialization."""
        result = MatchResult(
            award_id="AWARD-001",
            is_match=True,
            confidence_score=0.95,
            matched_uei="ABC123DEF456",
            match_method="comprehensive",
            match_details={"uei_match": True, "name_similarity": 0.98},
        )

        # Test dict conversion
        result_dict = result.to_dict()
        assert result_dict["award_id"] == "AWARD-001"
        assert result_dict["confidence_score"] == 0.95

        # Test reconstruction
        new_result = MatchResult.from_dict(result_dict)
        assert new_result.award_id == result.award_id
        assert new_result.confidence_score == result.confidence_score
