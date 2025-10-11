"""Tests for base enrichment service interface."""

from unittest.mock import Mock

import pytest

from sbir_cet_classifier.data.enrichment.enrichers import (
    EnrichmentError,
    EnrichmentResult,
    EnrichmentService,
    EnrichmentType,
)


class TestEnrichmentResult:
    """Test cases for enrichment result data structure."""
    
    def test_enrichment_result_creation(self):
        """Test enrichment result can be created with required fields."""
        result = EnrichmentResult(
            award_id="AWARD123",
            enrichment_type=EnrichmentType.AWARDEE,
            success=True,
            confidence=0.85,
            data={"organization": "Test Corp"},
            processing_time_ms=150
        )
        
        assert result.award_id == "AWARD123"
        assert result.enrichment_type == EnrichmentType.AWARDEE
        assert result.success is True
        assert result.confidence == 0.85
        assert result.data["organization"] == "Test Corp"
        assert result.processing_time_ms == 150
    
    def test_enrichment_result_with_error(self):
        """Test enrichment result can capture error information."""
        result = EnrichmentResult(
            award_id="AWARD123",
            enrichment_type=EnrichmentType.AWARDEE,
            success=False,
            confidence=0.0,
            error_message="API timeout",
            processing_time_ms=30000
        )
        
        assert result.success is False
        assert result.error_message == "API timeout"
        assert result.data is None


class TestEnrichmentService:
    """Test cases for base enrichment service."""
    
    @pytest.fixture
    def mock_sam_client(self):
        """Mock SAM.gov API client."""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_sam_client):
        """Test enrichment service instance."""
        return EnrichmentService(sam_client=mock_sam_client)
    
    def test_service_initialization(self, mock_sam_client):
        """Test service initializes with SAM client."""
        service = EnrichmentService(sam_client=mock_sam_client)
        assert service.sam_client == mock_sam_client
    
    def test_enrich_award_success(self, service, mock_sam_client):
        """Test successful award enrichment."""
        # Mock SAM client response
        mock_sam_client.get_award.return_value = {
            "awardId": "AWARD123",
            "recipientName": "Test Corp",
            "recipientUEI": "UEI123456789"
        }
        
        result = service.enrich_award(
            award_id="AWARD123",
            enrichment_types=[EnrichmentType.AWARDEE]
        )
        
        assert result.success is True
        assert result.award_id == "AWARD123"
        assert result.confidence > 0
    
    def test_enrich_award_not_found(self, service, mock_sam_client):
        """Test award enrichment when award not found."""
        from sbir_cet_classifier.data.enrichment.sam_client import SAMAPIError
        
        mock_sam_client.get_award.side_effect = SAMAPIError("Award not found", 404)
        
        result = service.enrich_award(
            award_id="NONEXISTENT",
            enrichment_types=[EnrichmentType.AWARDEE]
        )
        
        assert result.success is False
        assert "not found" in result.error_message.lower()
    
    def test_enrich_multiple_awards(self, service, mock_sam_client):
        """Test batch enrichment of multiple awards."""
        mock_sam_client.get_award.return_value = {
            "awardId": "AWARD123",
            "recipientName": "Test Corp"
        }
        
        results = service.enrich_awards(
            award_ids=["AWARD1", "AWARD2", "AWARD3"],
            enrichment_types=[EnrichmentType.AWARDEE]
        )
        
        assert len(results) == 3
        assert all(result.success for result in results)
    
    def test_confidence_scoring(self, service):
        """Test confidence scoring for enrichment results."""
        # Test high confidence scenario
        high_confidence_data = {
            "recipientUEI": "UEI123456789",
            "recipientName": "Exact Match Corp",
            "awardAmount": 100000
        }
        
        confidence = service.calculate_confidence(high_confidence_data)
        assert confidence >= 0.8
        
        # Test low confidence scenario
        low_confidence_data = {
            "recipientName": "Partial Match"
        }
        
        confidence = service.calculate_confidence(low_confidence_data)
        assert confidence < 0.5
    
    def test_enrichment_validation(self, service):
        """Test validation of enrichment data."""
        valid_data = {
            "recipientUEI": "UEI123456789",
            "recipientName": "Test Corp",
            "awardAmount": 100000
        }
        
        assert service.validate_enrichment_data(valid_data) is True
        
        invalid_data = {
            "recipientName": "",  # Empty name
            "awardAmount": -1000  # Negative amount
        }
        
        assert service.validate_enrichment_data(invalid_data) is False


class TestEnrichmentType:
    """Test cases for enrichment type enumeration."""
    
    def test_enrichment_types_exist(self):
        """Test all expected enrichment types are defined."""
        assert EnrichmentType.AWARDEE
        assert EnrichmentType.PROGRAM_OFFICE
        assert EnrichmentType.SOLICITATION
        assert EnrichmentType.MODIFICATIONS
    
    def test_enrichment_type_string_representation(self):
        """Test enrichment types have proper string representation."""
        assert str(EnrichmentType.AWARDEE) == "awardee"
        assert str(EnrichmentType.PROGRAM_OFFICE) == "program_office"


class TestEnrichmentError:
    """Test cases for enrichment error handling."""
    
    def test_enrichment_error_creation(self):
        """Test enrichment error can be created with context."""
        error = EnrichmentError(
            message="API timeout",
            award_id="AWARD123",
            enrichment_type=EnrichmentType.AWARDEE,
            context={"timeout_seconds": 30}
        )
        
        assert str(error) == "API timeout"
        assert error.award_id == "AWARD123"
        assert error.enrichment_type == EnrichmentType.AWARDEE
        assert error.context["timeout_seconds"] == 30
