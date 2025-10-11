"""Tests for ProgramOffice entity model."""

import pytest
from datetime import datetime
from decimal import Decimal
from pydantic import ValidationError

from src.sbir_cet_classifier.data.enrichment.models import ProgramOffice


class TestProgramOffice:
    """Test ProgramOffice entity model."""

    def test_program_office_creation_valid(self):
        """Test creating a valid ProgramOffice."""
        office = ProgramOffice(
            office_id="ONR-001",
            agency_code="DON",
            agency_name="Department of the Navy",
            office_name="Office of Naval Research",
            office_description="Advanced research for naval applications",
            contact_email="contact@onr.navy.mil",
            contact_phone="703-696-5031",
            website_url="https://www.onr.navy.mil",
            strategic_focus_areas=["quantum computing", "artificial intelligence", "materials"],
            annual_budget=Decimal("2500000000.00"),
            active_solicitations_count=25,
            total_awards_managed=1500,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert office.office_id == "ONR-001"
        assert office.agency_code == "DON"
        assert office.annual_budget == Decimal("2500000000.00")
        assert len(office.strategic_focus_areas) == 3

    def test_program_office_required_fields_only(self):
        """Test creating ProgramOffice with only required fields."""
        office = ProgramOffice(
            office_id="AFRL-001",
            agency_code="USAF",
            agency_name="United States Air Force",
            office_name="Air Force Research Laboratory",
            office_description="Advanced research for air force applications",
            strategic_focus_areas=["hypersonics", "space technology"],
            active_solicitations_count=15,
            total_awards_managed=800,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert office.contact_email is None
        assert office.contact_phone is None
        assert office.website_url is None
        assert office.annual_budget is None

    def test_program_office_email_validation(self):
        """Test email validation."""
        with pytest.raises(ValidationError) as exc_info:
            ProgramOffice(
                office_id="TEST-001",
                agency_code="TEST",
                agency_name="Test Agency",
                office_name="Test Office",
                office_description="Test description",
                contact_email="invalid-email",  # Invalid email format
                strategic_focus_areas=["test"],
                active_solicitations_count=1,
                total_awards_managed=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        
        assert "value is not a valid email address" in str(exc_info.value)

    def test_program_office_negative_counts_validation(self):
        """Test validation of non-negative counts."""
        with pytest.raises(ValidationError) as exc_info:
            ProgramOffice(
                office_id="TEST-001",
                agency_code="TEST",
                agency_name="Test Agency",
                office_name="Test Office",
                office_description="Test description",
                strategic_focus_areas=["test"],
                active_solicitations_count=-1,  # Invalid: negative
                total_awards_managed=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        
        assert "ensure this value is greater than or equal to 0" in str(exc_info.value)

    def test_program_office_negative_budget_validation(self):
        """Test validation of non-negative budget."""
        with pytest.raises(ValidationError) as exc_info:
            ProgramOffice(
                office_id="TEST-001",
                agency_code="TEST",
                agency_name="Test Agency",
                office_name="Test Office",
                office_description="Test description",
                annual_budget=Decimal("-1000000.00"),  # Invalid: negative
                strategic_focus_areas=["test"],
                active_solicitations_count=1,
                total_awards_managed=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        
        assert "ensure this value is greater than or equal to 0" in str(exc_info.value)

    def test_program_office_url_validation(self):
        """Test URL validation."""
        # Valid URL should work
        office = ProgramOffice(
            office_id="TEST-001",
            agency_code="TEST",
            agency_name="Test Agency",
            office_name="Test Office",
            office_description="Test description",
            website_url="https://www.example.com",
            strategic_focus_areas=["test"],
            active_solicitations_count=1,
            total_awards_managed=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert office.website_url == "https://www.example.com"

    def test_program_office_strategic_focus_areas_list(self):
        """Test strategic focus areas as list."""
        focus_areas = ["quantum computing", "AI", "cybersecurity", "materials science"]
        
        office = ProgramOffice(
            office_id="TEST-001",
            agency_code="TEST",
            agency_name="Test Agency",
            office_name="Test Office",
            office_description="Test description",
            strategic_focus_areas=focus_areas,
            active_solicitations_count=1,
            total_awards_managed=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert office.strategic_focus_areas == focus_areas
        assert len(office.strategic_focus_areas) == 4

    def test_program_office_serialization(self):
        """Test program office serialization to dict."""
        office = ProgramOffice(
            office_id="ONR-001",
            agency_code="DON",
            agency_name="Department of the Navy",
            office_name="Office of Naval Research",
            office_description="Naval research office",
            contact_email="contact@onr.navy.mil",
            strategic_focus_areas=["quantum", "AI"],
            annual_budget=Decimal("1000000000.00"),
            active_solicitations_count=20,
            total_awards_managed=1000,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        data = office.model_dump()
        
        assert data["office_id"] == "ONR-001"
        assert data["agency_code"] == "DON"
        assert data["strategic_focus_areas"] == ["quantum", "AI"]
        assert isinstance(data["annual_budget"], Decimal)

    def test_program_office_empty_strategic_focus_areas(self):
        """Test program office with empty strategic focus areas."""
        office = ProgramOffice(
            office_id="TEST-001",
            agency_code="TEST",
            agency_name="Test Agency",
            office_name="Test Office",
            office_description="Test description",
            strategic_focus_areas=[],  # Empty list
            active_solicitations_count=0,
            total_awards_managed=0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert office.strategic_focus_areas == []
        assert len(office.strategic_focus_areas) == 0

    def test_program_office_large_numbers(self):
        """Test program office with large budget and counts."""
        office = ProgramOffice(
            office_id="DARPA-001",
            agency_code="DOD",
            agency_name="Department of Defense",
            office_name="Defense Advanced Research Projects Agency",
            office_description="Advanced defense research",
            annual_budget=Decimal("10000000000.00"),  # $10B
            active_solicitations_count=500,
            total_awards_managed=10000,
            strategic_focus_areas=["emerging technologies"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert office.annual_budget == Decimal("10000000000.00")
        assert office.active_solicitations_count == 500
        assert office.total_awards_managed == 10000

    def test_program_office_phone_format(self):
        """Test various phone number formats."""
        valid_phones = [
            "703-696-5031",
            "(703) 696-5031",
            "703.696.5031",
            "7036965031",
            "+1-703-696-5031"
        ]
        
        for phone in valid_phones:
            office = ProgramOffice(
                office_id="TEST-001",
                agency_code="TEST",
                agency_name="Test Agency",
                office_name="Test Office",
                office_description="Test description",
                contact_phone=phone,
                strategic_focus_areas=["test"],
                active_solicitations_count=1,
                total_awards_managed=1,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            assert office.contact_phone == phone
