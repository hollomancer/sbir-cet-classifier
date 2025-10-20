"""Tests for SAM.gov API response schemas and validation."""

import pytest
from datetime import datetime
from decimal import Decimal
from pydantic import ValidationError

from sbir_cet_classifier.data.enrichment.schemas import (
    SAMOpportunityResponse,
    SAMAwardResponse,
    SAMEntityResponse,
    AwardeeProfile,
    ProgramOffice,
    Solicitation,
    AwardModification,
    EnrichmentStatus,
    OpportunityData,
    AwardData,
    EntityData,
)


class TestSAMOpportunityResponse:
    """Test SAM.gov opportunities API response schema."""
    
    def test_valid_opportunity_response(self):
        """Test valid opportunity response parsing."""
        data = {
            "opportunityId": "SBIR-2024-001",
            "title": "Advanced AI Research",
            "description": "Research in artificial intelligence",
            "postedDate": "2024-01-15T10:00:00Z",
            "closeDate": "2024-03-15T17:00:00Z",
            "totalEstimatedValue": 1000000.00,
            "awardCeiling": 500000.00,
            "awardFloor": 100000.00,
            "organizationName": "National Science Foundation",
            "officeAddress": {
                "city": "Alexandria",
                "state": "VA",
                "zipcode": "22314"
            }
        }
        
        response = SAMOpportunityResponse(**data)
        assert response.opportunity_id == "SBIR-2024-001"
        assert response.title == "Advanced AI Research"
        assert response.total_estimated_value == Decimal("1000000.00")
        
    def test_missing_required_fields(self):
        """Test validation error for missing required fields."""
        data = {
            "title": "Advanced AI Research"
            # Missing opportunityId
        }
        
        with pytest.raises(ValidationError) as exc_info:
            SAMOpportunityResponse(**data)
        
        assert "opportunityId" in str(exc_info.value)
        
    def test_invalid_date_format(self):
        """Test validation error for invalid date format."""
        data = {
            "opportunityId": "SBIR-2024-001",
            "title": "Advanced AI Research",
            "postedDate": "invalid-date"
        }
        
        with pytest.raises(ValidationError):
            SAMOpportunityResponse(**data)


class TestSAMAwardResponse:
    """Test SAM.gov awards API response schema."""
    
    def test_valid_award_response(self):
        """Test valid award response parsing."""
        data = {
            "awardId": "AWARD-2024-001",
            "awardNumber": "1234567890",
            "title": "AI Research Project",
            "awardAmount": 250000.00,
            "startDate": "2024-01-01T00:00:00Z",
            "endDate": "2024-12-31T23:59:59Z",
            "recipientName": "Tech Innovations LLC",
            "recipientUEI": "ABC123DEF456",
            "fundingAgency": "NSF",
            "programOffice": "Computer and Information Science and Engineering"
        }
        
        response = SAMAwardResponse(**data)
        assert response.award_id == "AWARD-2024-001"
        assert response.award_amount == Decimal("250000.00")
        assert response.recipient_uei == "ABC123DEF456"
        
    def test_optional_fields(self):
        """Test handling of optional fields."""
        data = {
            "awardId": "AWARD-2024-001",
            "awardNumber": "1234567890",
            "title": "AI Research Project",
            "awardAmount": 250000.00,
            "recipientName": "Tech Innovations LLC"
            # Missing optional fields
        }
        
        response = SAMAwardResponse(**data)
        assert response.recipient_uei is None
        assert response.program_office is None


class TestSAMEntityResponse:
    """Test SAM.gov entity information API response schema."""
    
    def test_valid_entity_response(self):
        """Test valid entity response parsing."""
        data = {
            "entityId": "ENTITY-001",
            "legalBusinessName": "Tech Innovations LLC",
            "ueiSAM": "ABC123DEF456",
            "entityStatus": "Active",
            "registrationDate": "2020-01-15T10:00:00Z",
            "lastUpdateDate": "2024-01-15T10:00:00Z",
            "physicalAddress": {
                "addressLine1": "123 Tech Street",
                "city": "Innovation City",
                "stateOrProvinceCode": "CA",
                "zipCode": "90210",
                "countryCode": "USA"
            },
            "businessTypes": ["Small Business", "Woman-Owned"]
        }
        
        response = SAMEntityResponse(**data)
        assert response.entity_id == "ENTITY-001"
        assert response.legal_business_name == "Tech Innovations LLC"
        assert response.uei_sam == "ABC123DEF456"
        assert len(response.business_types) == 2


class TestAwardeeProfile:
    """Test AwardeeProfile entity model."""
    
    def test_valid_awardee_profile(self):
        """Test valid awardee profile creation."""
        data = {
            "uei": "ABC123DEF456",
            "legal_name": "Tech Innovations LLC",
            "total_awards": 15,
            "total_funding": Decimal("5000000.00"),
            "success_rate": 0.85,
            "avg_award_amount": Decimal("333333.33"),
            "first_award_date": datetime(2018, 1, 1),
            "last_award_date": datetime(2024, 1, 1),
            "primary_agencies": ["NSF", "DOD"],
            "technology_areas": ["AI", "Cybersecurity"]
        }
        
        profile = AwardeeProfile(**data)
        assert profile.uei == "ABC123DEF456"
        assert profile.total_awards == 15
        assert profile.success_rate == 0.85
        
    def test_calculated_fields(self):
        """Test calculated fields in awardee profile."""
        data = {
            "uei": "ABC123DEF456",
            "legal_name": "Tech Innovations LLC",
            "total_awards": 10,
            "total_funding": Decimal("2000000.00"),
            "success_rate": 0.80,
            "avg_award_amount": Decimal("200000.00"),
            "first_award_date": datetime(2020, 1, 1),
            "last_award_date": datetime(2024, 1, 1),
            "primary_agencies": ["NSF"],
            "technology_areas": ["AI"]
        }
        
        profile = AwardeeProfile(**data)
        # Test that calculated average matches expected
        expected_avg = profile.total_funding / profile.total_awards
        assert abs(profile.avg_award_amount - expected_avg) < Decimal("0.01")


class TestProgramOffice:
    """Test ProgramOffice entity model."""
    
    def test_valid_program_office(self):
        """Test valid program office creation."""
        data = {
            "agency": "NSF",
            "office_name": "Computer and Information Science and Engineering",
            "office_code": "CISE",
            "contact_email": "cise@nsf.gov",
            "strategic_focus": ["AI", "Cybersecurity", "Quantum Computing"],
            "annual_budget": Decimal("500000000.00"),
            "active_programs": 25
        }
        
        office = ProgramOffice(**data)
        assert office.agency == "NSF"
        assert office.office_code == "CISE"
        assert len(office.strategic_focus) == 3


class TestSolicitation:
    """Test Solicitation entity model."""
    
    def test_valid_solicitation(self):
        """Test valid solicitation creation."""
        data = {
            "solicitation_id": "SOL-2024-001",
            "title": "Advanced AI Research Solicitation",
            "full_text": "This solicitation seeks proposals for advanced AI research...",
            "technical_requirements": ["Machine Learning", "Neural Networks"],
            "evaluation_criteria": ["Technical Merit", "Commercial Potential"],
            "topic_areas": ["AI", "Data Science"],
            "funding_range_min": Decimal("100000.00"),
            "funding_range_max": Decimal("500000.00"),
            "submission_deadline": datetime(2024, 3, 15)
        }
        
        solicitation = Solicitation(**data)
        assert solicitation.solicitation_id == "SOL-2024-001"
        assert len(solicitation.technical_requirements) == 2
        assert solicitation.funding_range_max > solicitation.funding_range_min


class TestAwardModification:
    """Test AwardModification entity model."""
    
    def test_valid_award_modification(self):
        """Test valid award modification creation."""
        data = {
            "modification_id": "MOD-001",
            "award_id": "AWARD-2024-001",
            "modification_type": "Funding Increase",
            "modification_date": datetime(2024, 6, 15),
            "funding_change": Decimal("50000.00"),
            "scope_change": "Added Phase II option",
            "new_end_date": datetime(2025, 12, 31),
            "justification": "Successful Phase I completion"
        }
        
        modification = AwardModification(**data)
        assert modification.modification_id == "MOD-001"
        assert modification.funding_change == Decimal("50000.00")
        assert modification.modification_type == "Funding Increase"


class TestEnrichmentStatus:
    """Test EnrichmentStatus tracking model."""
    
    def test_valid_enrichment_status(self):
        """Test valid enrichment status creation."""
        data = {
            "award_id": "AWARD-2024-001",
            "enrichment_types": ["awardee", "program_office"],
            "status": "completed",
            "confidence_score": 0.95,
            "last_updated": datetime(2024, 1, 15),
            "error_message": None,
            "data_sources": ["SAM.gov API"]
        }
        
        status = EnrichmentStatus(**data)
        assert status.award_id == "AWARD-2024-001"
        assert len(status.enrichment_types) == 2
        assert status.confidence_score == 0.95
        
    def test_failed_enrichment_status(self):
        """Test enrichment status with error."""
        data = {
            "award_id": "AWARD-2024-002",
            "enrichment_types": ["awardee"],
            "status": "failed",
            "confidence_score": 0.0,
            "last_updated": datetime(2024, 1, 15),
            "error_message": "API rate limit exceeded",
            "data_sources": []
        }
        
        status = EnrichmentStatus(**data)
        assert status.status == "failed"
        assert status.error_message == "API rate limit exceeded"
        assert len(status.data_sources) == 0


class TestValidationEdgeCases:
    """Test edge cases and validation scenarios."""
    
    def test_decimal_precision(self):
        """Test decimal field precision handling."""
        data = {
            "uei": "ABC123DEF456",
            "legal_name": "Test Company",
            "total_awards": 1,
            "total_funding": Decimal("123.456789"),  # High precision
            "success_rate": 1.0,
            "avg_award_amount": Decimal("123.456789"),
            "first_award_date": datetime(2024, 1, 1),
            "last_award_date": datetime(2024, 1, 1),
            "primary_agencies": ["NSF"],
            "technology_areas": ["AI"]
        }
        
        profile = AwardeeProfile(**data)
        # Should handle high precision decimals
        assert profile.total_funding == Decimal("123.456789")
        
    def test_empty_lists(self):
        """Test handling of empty list fields."""
        data = {
            "agency": "NSF",
            "office_name": "Test Office",
            "office_code": "TEST",
            "strategic_focus": [],  # Empty list
            "annual_budget": Decimal("1000000.00"),
            "active_programs": 0
        }
        
        office = ProgramOffice(**data)
        assert len(office.strategic_focus) == 0
        
    def test_none_optional_fields(self):
        """Test None values for optional fields."""
        data = {
            "solicitation_id": "SOL-2024-001",
            "title": "Test Solicitation",
            "full_text": "Test text",
            "technical_requirements": [],
            "evaluation_criteria": [],
            "topic_areas": [],
            "funding_range_min": None,  # Optional
            "funding_range_max": None,  # Optional
            "submission_deadline": datetime(2024, 3, 15)
        }
        
        solicitation = Solicitation(**data)
        assert solicitation.funding_range_min is None
        assert solicitation.funding_range_max is None
