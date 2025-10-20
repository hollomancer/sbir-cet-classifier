"""Tests for enrichment data models."""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

from src.sbir_cet_classifier.data.enrichment.models import (
    AwardeeProfile,
    AwardeeMatchResult,
    AwardeeEnrichmentService,
)


class TestAwardeeProfile:
    """Test AwardeeProfile entity model."""
    
    def test_create_awardee_profile(self):
        """Test creating awardee profile with all fields."""
        profile = AwardeeProfile(
            uei="ABC123DEF456",
            legal_name="Tech Innovations LLC",
            total_awards=15,
            total_funding=Decimal("5000000.00"),
            success_rate=0.85,
            avg_award_amount=Decimal("333333.33"),
            first_award_date=datetime(2018, 1, 1),
            last_award_date=datetime(2024, 1, 1),
            primary_agencies=["NSF", "DOD"],
            technology_areas=["AI", "Cybersecurity"]
        )
        
        assert profile.uei == "ABC123DEF456"
        assert profile.legal_name == "Tech Innovations LLC"
        assert profile.total_awards == 15
        assert profile.total_funding == Decimal("5000000.00")
        assert profile.success_rate == 0.85
        assert len(profile.primary_agencies) == 2
        assert len(profile.technology_areas) == 2
    
    def test_awardee_profile_validation(self):
        """Test awardee profile field validation."""
        # Test negative total awards
        with pytest.raises(ValueError):
            AwardeeProfile(
                uei="ABC123DEF456",
                legal_name="Test Company",
                total_awards=-1,  # Invalid
                total_funding=Decimal("1000000.00"),
                success_rate=0.85,
                avg_award_amount=Decimal("100000.00"),
                first_award_date=datetime(2020, 1, 1),
                last_award_date=datetime(2024, 1, 1),
                primary_agencies=["NSF"],
                technology_areas=["AI"]
            )
    
    def test_awardee_profile_success_rate_bounds(self):
        """Test success rate validation bounds."""
        # Test success rate > 1.0
        with pytest.raises(ValueError):
            AwardeeProfile(
                uei="ABC123DEF456",
                legal_name="Test Company",
                total_awards=10,
                total_funding=Decimal("1000000.00"),
                success_rate=1.5,  # Invalid
                avg_award_amount=Decimal("100000.00"),
                first_award_date=datetime(2020, 1, 1),
                last_award_date=datetime(2024, 1, 1),
                primary_agencies=["NSF"],
                technology_areas=["AI"]
            )
    
    def test_awardee_profile_date_consistency(self):
        """Test date field consistency."""
        # Last award date should not be before first award date
        profile = AwardeeProfile(
            uei="ABC123DEF456",
            legal_name="Test Company",
            total_awards=5,
            total_funding=Decimal("500000.00"),
            success_rate=0.8,
            avg_award_amount=Decimal("100000.00"),
            first_award_date=datetime(2024, 1, 1),
            last_award_date=datetime(2020, 1, 1),  # Before first date
            primary_agencies=["NSF"],
            technology_areas=["AI"]
        )
        
        # Should be allowed but might want to add validation later
        assert profile.first_award_date > profile.last_award_date
    
    def test_awardee_profile_calculated_metrics(self):
        """Test calculated metrics consistency."""
        profile = AwardeeProfile(
            uei="ABC123DEF456",
            legal_name="Test Company",
            total_awards=10,
            total_funding=Decimal("2000000.00"),
            success_rate=0.8,
            avg_award_amount=Decimal("200000.00"),
            first_award_date=datetime(2020, 1, 1),
            last_award_date=datetime(2024, 1, 1),
            primary_agencies=["NSF"],
            technology_areas=["AI"]
        )
        
        # Verify average calculation
        expected_avg = profile.total_funding / profile.total_awards
        assert abs(profile.avg_award_amount - expected_avg) < Decimal("0.01")
    
    def test_awardee_profile_serialization(self):
        """Test awardee profile serialization."""
        profile = AwardeeProfile(
            uei="ABC123DEF456",
            legal_name="Test Company",
            total_awards=5,
            total_funding=Decimal("1000000.00"),
            success_rate=0.9,
            avg_award_amount=Decimal("200000.00"),
            first_award_date=datetime(2020, 1, 1),
            last_award_date=datetime(2024, 1, 1),
            primary_agencies=["NSF", "DOD"],
            technology_areas=["AI", "Robotics"]
        )
        
        # Test dict conversion
        profile_dict = profile.model_dump()
        assert profile_dict["uei"] == "ABC123DEF456"
        assert profile_dict["total_awards"] == 5
        assert len(profile_dict["primary_agencies"]) == 2
        
        # Test reconstruction from dict
        new_profile = AwardeeProfile(**profile_dict)
        assert new_profile.uei == profile.uei
        assert new_profile.total_awards == profile.total_awards


class TestAwardeeMatchResult:
    """Test AwardeeMatchResult model."""
    
    def test_create_match_result(self):
        """Test creating awardee match result."""
        result = AwardeeMatchResult(
            award_id="AWARD-001",
            matched_uei="ABC123DEF456",
            confidence_score=0.95,
            match_method="exact_uei",
            match_details={
                "uei_match": True,
                "name_similarity": 0.98,
                "award_number_match": True
            }
        )
        
        assert result.award_id == "AWARD-001"
        assert result.matched_uei == "ABC123DEF456"
        assert result.confidence_score == 0.95
        assert result.match_method == "exact_uei"
        assert result.match_details["uei_match"] is True
    
    def test_match_result_confidence_validation(self):
        """Test confidence score validation."""
        # Test confidence score > 1.0
        with pytest.raises(ValueError):
            AwardeeMatchResult(
                award_id="AWARD-001",
                matched_uei="ABC123DEF456",
                confidence_score=1.5,  # Invalid
                match_method="fuzzy_name",
                match_details={}
            )
    
    def test_match_result_comparison(self):
        """Test comparing match results by confidence."""
        result1 = AwardeeMatchResult(
            award_id="AWARD-001",
            matched_uei="ABC123DEF456",
            confidence_score=0.95,
            match_method="exact_uei",
            match_details={}
        )
        
        result2 = AwardeeMatchResult(
            award_id="AWARD-001",
            matched_uei="XYZ789GHI012",
            confidence_score=0.85,
            match_method="fuzzy_name",
            match_details={}
        )
        
        # Should be able to compare by confidence
        assert result1.confidence_score > result2.confidence_score


class TestAwardeeEnrichmentService:
    """Test AwardeeEnrichmentService functionality."""
    
    @pytest.fixture
    def mock_sam_client(self):
        """Mock SAM.gov API client."""
        return Mock()
    
    @pytest.fixture
    def enrichment_service(self, mock_sam_client):
        """Create enrichment service with mocked dependencies."""
        return AwardeeEnrichmentService(sam_client=mock_sam_client)
    
    def test_find_awardee_by_uei(self, enrichment_service, mock_sam_client):
        """Test finding awardee by UEI."""
        # Mock SAM.gov API response
        mock_sam_client.get_entity_by_uei.return_value = {
            "ueiSAM": "ABC123DEF456",
            "legalBusinessName": "Tech Innovations LLC",
            "entityStatus": "Active"
        }
        
        result = enrichment_service.find_awardee_by_uei("ABC123DEF456")
        
        assert result is not None
        assert result["ueiSAM"] == "ABC123DEF456"
        mock_sam_client.get_entity_by_uei.assert_called_once_with("ABC123DEF456")
    
    def test_find_awardee_by_name(self, enrichment_service, mock_sam_client):
        """Test finding awardee by name with fuzzy matching."""
        # Mock SAM.gov API response
        mock_sam_client.search_entities.return_value = {
            "entities": [
                {
                    "ueiSAM": "ABC123DEF456",
                    "legalBusinessName": "Tech Innovations LLC",
                    "entityStatus": "Active"
                }
            ]
        }
        
        results = enrichment_service.find_awardee_by_name("Tech Innovations")
        
        assert len(results) == 1
        assert results[0]["ueiSAM"] == "ABC123DEF456"
        mock_sam_client.search_entities.assert_called_once()
    
    def test_match_award_to_awardee(self, enrichment_service, mock_sam_client):
        """Test matching award to awardee with confidence scoring."""
        # Mock award data
        award_data = {
            "award_id": "AWARD-001",
            "awardee_name": "Tech Innovations LLC",
            "awardee_uei": "ABC123DEF456"
        }
        
        # Mock SAM.gov response
        mock_sam_client.get_entity_by_uei.return_value = {
            "ueiSAM": "ABC123DEF456",
            "legalBusinessName": "Tech Innovations LLC",
            "entityStatus": "Active"
        }
        
        match_result = enrichment_service.match_award_to_awardee(award_data)
        
        assert match_result is not None
        assert match_result.award_id == "AWARD-001"
        assert match_result.matched_uei == "ABC123DEF456"
        assert match_result.confidence_score > 0.9  # High confidence for exact UEI match
    
    def test_enrich_awardee_profile(self, enrichment_service, mock_sam_client):
        """Test enriching awardee profile with historical data."""
        # Mock SAM.gov responses
        mock_sam_client.get_entity_by_uei.return_value = {
            "ueiSAM": "ABC123DEF456",
            "legalBusinessName": "Tech Innovations LLC",
            "entityStatus": "Active"
        }
        
        mock_sam_client.get_awards_by_uei.return_value = {
            "awards": [
                {
                    "awardId": "AWARD-001",
                    "awardAmount": 250000.00,
                    "startDate": "2020-01-01",
                    "fundingAgency": "NSF"
                },
                {
                    "awardId": "AWARD-002", 
                    "awardAmount": 500000.00,
                    "startDate": "2022-01-01",
                    "fundingAgency": "DOD"
                }
            ]
        }
        
        profile = enrichment_service.enrich_awardee_profile("ABC123DEF456")
        
        assert profile is not None
        assert profile.uei == "ABC123DEF456"
        assert profile.legal_name == "Tech Innovations LLC"
        assert profile.total_awards == 2
        assert profile.total_funding == Decimal("750000.00")
        assert "NSF" in profile.primary_agencies
        assert "DOD" in profile.primary_agencies
    
    def test_calculate_confidence_score(self, enrichment_service):
        """Test confidence score calculation."""
        # Test exact UEI match
        match_data = {
            "uei_match": True,
            "name_similarity": 1.0,
            "award_number_match": True
        }
        
        confidence = enrichment_service.calculate_confidence_score(match_data)
        assert confidence >= 0.95
        
        # Test fuzzy name match only
        match_data = {
            "uei_match": False,
            "name_similarity": 0.8,
            "award_number_match": False
        }
        
        confidence = enrichment_service.calculate_confidence_score(match_data)
        assert 0.5 <= confidence <= 0.8
    
    def test_handle_no_match_found(self, enrichment_service, mock_sam_client):
        """Test handling when no awardee match is found."""
        # Mock no results from SAM.gov
        mock_sam_client.get_entity_by_uei.return_value = None
        mock_sam_client.search_entities.return_value = {"entities": []}
        
        award_data = {
            "award_id": "AWARD-001",
            "awardee_name": "Unknown Company",
            "awardee_uei": None
        }
        
        match_result = enrichment_service.match_award_to_awardee(award_data)
        
        # Should return None or low confidence result
        assert match_result is None or match_result.confidence_score < 0.5
    
    def test_batch_enrichment(self, enrichment_service, mock_sam_client):
        """Test batch enrichment of multiple awards."""
        awards = [
            {"award_id": "AWARD-001", "awardee_uei": "ABC123DEF456"},
            {"award_id": "AWARD-002", "awardee_uei": "XYZ789GHI012"}
        ]
        
        # Mock responses for both UEIs
        def mock_get_entity(uei):
            if uei == "ABC123DEF456":
                return {"ueiSAM": uei, "legalBusinessName": "Company A"}
            elif uei == "XYZ789GHI012":
                return {"ueiSAM": uei, "legalBusinessName": "Company B"}
            return None
        
        mock_sam_client.get_entity_by_uei.side_effect = mock_get_entity
        
        results = enrichment_service.batch_enrich_awards(awards)
        
        assert len(results) == 2
        assert all(result.confidence_score > 0.8 for result in results)
        assert mock_sam_client.get_entity_by_uei.call_count == 2


class TestSolicitation:
    """Test Solicitation entity model."""
    
    def test_create_solicitation(self):
        """Test creating solicitation with all fields."""
        from sbir_cet_classifier.data.enrichment.schemas import Solicitation
        
        solicitation = Solicitation(
            solicitation_id="SOL-2024-001",
            title="Advanced AI Research Solicitation",
            full_text="This solicitation seeks proposals for advanced AI research...",
            technical_requirements=["Machine Learning", "Neural Networks"],
            evaluation_criteria=["Technical Merit", "Commercial Potential"],
            topic_areas=["AI", "Data Science"],
            funding_range_min=Decimal("100000.00"),
            funding_range_max=Decimal("500000.00"),
            submission_deadline=datetime(2024, 3, 15)
        )
        
        assert solicitation.solicitation_id == "SOL-2024-001"
        assert solicitation.title == "Advanced AI Research Solicitation"
        assert len(solicitation.technical_requirements) == 2
        assert len(solicitation.evaluation_criteria) == 2
        assert len(solicitation.topic_areas) == 2
        assert solicitation.funding_range_min == Decimal("100000.00")
        assert solicitation.funding_range_max == Decimal("500000.00")
    
    def test_solicitation_validation(self):
        """Test solicitation field validation."""
        from sbir_cet_classifier.data.enrichment.schemas import Solicitation
        
        # Test funding range validation
        with pytest.raises(ValueError):
            Solicitation(
                solicitation_id="SOL-2024-001",
                title="Test Solicitation",
                full_text="Test text",
                technical_requirements=[],
                evaluation_criteria=[],
                topic_areas=[],
                funding_range_min=Decimal("500000.00"),
                funding_range_max=Decimal("100000.00"),  # Max < Min
                submission_deadline=datetime(2024, 3, 15)
            )
    
    def test_solicitation_optional_fields(self):
        """Test solicitation with optional fields."""
        from sbir_cet_classifier.data.enrichment.schemas import Solicitation
        
        solicitation = Solicitation(
            solicitation_id="SOL-2024-001",
            title="Test Solicitation",
            full_text="Test text",
            technical_requirements=[],
            evaluation_criteria=[],
            topic_areas=[],
            funding_range_min=None,  # Optional
            funding_range_max=None,  # Optional
            submission_deadline=datetime(2024, 3, 15)
        )
        
        assert solicitation.funding_range_min is None
        assert solicitation.funding_range_max is None
