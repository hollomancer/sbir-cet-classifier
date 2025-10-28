"""Tests for awardee profile data validation."""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

from sbir_cet_classifier.data.enrichment.awardee_validation import (
    AwardeeProfileValidator,
    ValidationResult,
    ValidationError,
)
from sbir_cet_classifier.data.enrichment.models import AwardeeProfile


class TestAwardeeProfileValidator:
    """Test awardee profile data validation."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return AwardeeProfileValidator()

    def test_validate_complete_profile(self, validator):
        """Test validation of complete awardee profile."""
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
            technology_areas=["AI", "Cybersecurity"],
        )

        result = validator.validate_profile(profile)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validate_uei_format(self, validator):
        """Test UEI format validation."""
        # Valid UEI (12 alphanumeric characters)
        result = validator.validate_uei("ABC123DEF456")
        assert result.is_valid is True

        # Invalid UEI - too short
        result = validator.validate_uei("ABC123")
        assert result.is_valid is False
        assert "UEI must be 12 characters" in result.errors[0].message

        # Invalid UEI - contains special characters
        result = validator.validate_uei("ABC123-DEF456")
        assert result.is_valid is False
        assert "UEI must contain only alphanumeric characters" in result.errors[0].message

    def test_validate_funding_consistency(self, validator):
        """Test funding amount consistency validation."""
        profile = AwardeeProfile(
            uei="ABC123DEF456",
            legal_name="Tech Innovations LLC",
            total_awards=10,
            total_funding=Decimal("1000000.00"),
            success_rate=0.8,
            avg_award_amount=Decimal("200000.00"),  # Inconsistent with total/count
            first_award_date=datetime(2020, 1, 1),
            last_award_date=datetime(2024, 1, 1),
            primary_agencies=["NSF"],
            technology_areas=["AI"],
        )

        result = validator.validate_profile(profile)

        # Should have warning about funding inconsistency
        assert any(
            ("funding consistency" in warning.message.lower())
            or (
                "average award amount" in warning.message.lower()
                and "calculated average" in warning.message.lower()
            )
            for warning in result.warnings
        )

    def test_validate_date_consistency(self, validator):
        """Test date consistency validation."""
        profile = AwardeeProfile(
            uei="ABC123DEF456",
            legal_name="Tech Innovations LLC",
            total_awards=5,
            total_funding=Decimal("1000000.00"),
            success_rate=0.8,
            avg_award_amount=Decimal("200000.00"),
            first_award_date=datetime(2024, 1, 1),  # After last award date
            last_award_date=datetime(2020, 1, 1),
            primary_agencies=["NSF"],
            technology_areas=["AI"],
        )

        result = validator.validate_profile(profile)

        assert result.is_valid is False
        assert any("first award date" in error.message.lower() for error in result.errors)

    def test_validate_success_rate_bounds(self, validator):
        """Test success rate bounds validation."""
        # Success rate > 1.0
        with pytest.raises(ValueError):
            AwardeeProfile(
                uei="ABC123DEF456",
                legal_name="Tech Innovations LLC",
                total_awards=5,
                total_funding=Decimal("1000000.00"),
                success_rate=1.5,  # Invalid
                avg_award_amount=Decimal("200000.00"),
                first_award_date=datetime(2020, 1, 1),
                last_award_date=datetime(2024, 1, 1),
                primary_agencies=["NSF"],
                technology_areas=["AI"],
            )

    def test_validate_business_name_format(self, validator):
        """Test business name format validation."""
        # Valid business names
        valid_names = [
            "Tech Innovations LLC",
            "ABC Corporation",
            "Research Solutions Inc.",
            "University of Technology",
        ]

        for name in valid_names:
            result = validator.validate_business_name(name)
            assert result.is_valid is True

        # Invalid business names
        invalid_names = [
            "",  # Empty
            "A",  # Too short
            "X" * 200,  # Too long
        ]

        for name in invalid_names:
            result = validator.validate_business_name(name)
            assert result.is_valid is False

    def test_validate_agency_codes(self, validator):
        """Test agency code validation."""
        # Valid agency codes
        valid_agencies = ["NSF", "DOD", "NIH", "NASA", "DOE"]

        for agency in valid_agencies:
            result = validator.validate_agency_code(agency)
            assert result.is_valid is True

        # Invalid agency codes
        invalid_agencies = ["INVALID", "XYZ", ""]

        for agency in invalid_agencies:
            result = validator.validate_agency_code(agency)
            assert result.is_valid is False

    def test_validate_technology_areas(self, validator):
        """Test technology area validation."""
        # Valid technology areas
        valid_areas = ["AI", "Cybersecurity", "Robotics", "Biotech"]

        result = validator.validate_technology_areas(valid_areas)
        assert result.is_valid is True

        # Too many technology areas
        too_many_areas = ["AI"] * 20
        result = validator.validate_technology_areas(too_many_areas)
        assert result.is_valid is False
        assert "too many technology areas" in result.errors[0].message.lower()

    def test_cross_field_validation(self, validator):
        """Test cross-field validation rules."""
        # High success rate with low funding should generate warning
        profile = AwardeeProfile(
            uei="ABC123DEF456",
            legal_name="Tech Innovations LLC",
            total_awards=100,  # Many awards
            total_funding=Decimal("50000.00"),  # Low funding
            success_rate=0.95,  # High success rate
            avg_award_amount=Decimal("500.00"),  # Very low average
            first_award_date=datetime(2020, 1, 1),
            last_award_date=datetime(2024, 1, 1),
            primary_agencies=["NSF"],
            technology_areas=["AI"],
        )

        result = validator.validate_profile(profile)

        # Should have warnings about unusual patterns
        assert len(result.warnings) > 0

    def test_validate_profile_completeness(self, validator):
        """Test profile completeness validation."""
        # Minimal profile
        profile = AwardeeProfile(
            uei="ABC123DEF456",
            legal_name="Tech Innovations LLC",
            total_awards=1,
            total_funding=Decimal("100000.00"),
            success_rate=1.0,
            avg_award_amount=Decimal("100000.00"),
            first_award_date=datetime(2024, 1, 1),
            last_award_date=datetime(2024, 1, 1),
            primary_agencies=[],  # Empty
            technology_areas=[],  # Empty
        )

        result = validator.validate_profile(profile)

        # Should have warnings about missing data
        assert any("primary agencies" in warning.message.lower() for warning in result.warnings)
        assert any("technology areas" in warning.message.lower() for warning in result.warnings)


class TestValidationResult:
    """Test ValidationResult model."""

    def test_create_validation_result(self):
        """Test creating validation result."""
        errors = [ValidationError("field1", "Error message 1")]
        warnings = [ValidationError("field2", "Warning message 1")]

        result = ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert result.errors[0].field == "field1"
        assert result.warnings[0].field == "field2"

    def test_add_error(self):
        """Test adding error to validation result."""
        result = ValidationResult()

        result.add_error("test_field", "Test error message")

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "test_field"
        assert result.errors[0].message == "Test error message"

    def test_add_warning(self):
        """Test adding warning to validation result."""
        result = ValidationResult()

        result.add_warning("test_field", "Test warning message")

        assert result.is_valid is True  # Warnings don't affect validity
        assert len(result.warnings) == 1
        assert result.warnings[0].field == "test_field"

    def test_merge_results(self):
        """Test merging validation results."""
        result1 = ValidationResult()
        result1.add_error("field1", "Error 1")
        result1.add_warning("field1", "Warning 1")

        result2 = ValidationResult()
        result2.add_error("field2", "Error 2")
        result2.add_warning("field2", "Warning 2")

        merged = result1.merge(result2)

        assert merged.is_valid is False
        assert len(merged.errors) == 2
        assert len(merged.warnings) == 2


class TestValidationError:
    """Test ValidationError model."""

    def test_create_validation_error(self):
        """Test creating validation error."""
        error = ValidationError("test_field", "Test error message")

        assert error.field == "test_field"
        assert error.message == "Test error message"
        assert error.severity == "error"

    def test_create_validation_warning(self):
        """Test creating validation warning."""
        warning = ValidationError("test_field", "Test warning message", severity="warning")

        assert warning.field == "test_field"
        assert warning.message == "Test warning message"
        assert warning.severity == "warning"

    def test_error_string_representation(self):
        """Test error string representation."""
        error = ValidationError("test_field", "Test error message")

        error_str = str(error)
        assert "test_field" in error_str
        assert "Test error message" in error_str
