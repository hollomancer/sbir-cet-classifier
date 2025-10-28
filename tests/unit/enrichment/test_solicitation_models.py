"""Tests for Solicitation entity model."""

import pytest
from datetime import date, datetime
from decimal import Decimal
from pydantic import ValidationError

from sbir_cet_classifier.data.enrichment.models import Solicitation


class TestSolicitation:
    """Test Solicitation entity model."""

    def test_solicitation_creation_valid(self):
        """Test creating a valid Solicitation."""
        solicitation = Solicitation(
            solicitation_id="SOL-2024-001",
            solicitation_number="N00014-24-S-B001",
            title="Advanced Materials Research",
            agency_code="DON",
            program_office_id="ONR-001",
            solicitation_type="SBIR Phase I",
            topic_number="N241-001",
            full_text="Complete solicitation text here...",
            technical_requirements="Technical requirements text...",
            evaluation_criteria="Evaluation criteria text...",
            funding_range_min=Decimal("100000.00"),
            funding_range_max=Decimal("300000.00"),
            proposal_deadline=date(2024, 6, 15),
            award_start_date=date(2024, 9, 1),
            performance_period=12,
            keywords=["materials", "nanotechnology", "composites"],
            cet_relevance_scores={"advanced_materials": 0.95, "quantum": 0.1},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert solicitation.solicitation_id == "SOL-2024-001"
        assert solicitation.funding_range_min == Decimal("100000.00")
        assert len(solicitation.keywords) == 3

    def test_solicitation_funding_range_validation(self):
        """Test funding range validation."""
        with pytest.raises(ValidationError) as exc_info:
            Solicitation(
                solicitation_id="SOL-2024-001",
                solicitation_number="N00014-24-S-B001",
                title="Test Solicitation",
                agency_code="DON",
                program_office_id="ONR-001",
                solicitation_type="SBIR Phase I",
                full_text="Text",
                technical_requirements="Requirements",
                evaluation_criteria="Criteria",
                funding_range_min=Decimal("300000.00"),  # Higher than max
                funding_range_max=Decimal("100000.00"),  # Lower than min
                proposal_deadline=date(2024, 6, 15),
                performance_period=12,
                keywords=[],
                cet_relevance_scores={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

        assert "funding_range_min must be <= funding_range_max" in str(exc_info.value)

    def test_solicitation_performance_period_validation(self):
        """Test performance period must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            Solicitation(
                solicitation_id="SOL-2024-001",
                solicitation_number="N00014-24-S-B001",
                title="Test Solicitation",
                agency_code="DON",
                program_office_id="ONR-001",
                solicitation_type="SBIR Phase I",
                full_text="Text",
                technical_requirements="Requirements",
                evaluation_criteria="Criteria",
                funding_range_min=Decimal("100000.00"),
                funding_range_max=Decimal("300000.00"),
                proposal_deadline=date(2024, 6, 15),
                performance_period=0,  # Invalid: must be positive
                keywords=[],
                cet_relevance_scores={},
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

        assert "Input should be greater than 0" in str(exc_info.value)

    def test_solicitation_cet_relevance_scores_validation(self):
        """Test CET relevance scores must be valid JSON with numeric values."""
        # Valid scores
        solicitation = Solicitation(
            solicitation_id="SOL-2024-001",
            solicitation_number="N00014-24-S-B001",
            title="Test Solicitation",
            agency_code="DON",
            program_office_id="ONR-001",
            solicitation_type="SBIR Phase I",
            full_text="Text",
            technical_requirements="Requirements",
            evaluation_criteria="Criteria",
            funding_range_min=Decimal("100000.00"),
            funding_range_max=Decimal("300000.00"),
            proposal_deadline=date(2024, 6, 15),
            performance_period=12,
            keywords=[],
            cet_relevance_scores={"ai": 0.8, "quantum": 0.3},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert solicitation.cet_relevance_scores["ai"] == 0.8

    def test_solicitation_optional_fields(self):
        """Test solicitation with minimal required fields."""
        solicitation = Solicitation(
            solicitation_id="SOL-2024-001",
            solicitation_number="N00014-24-S-B001",
            title="Test Solicitation",
            agency_code="DON",
            program_office_id="ONR-001",
            solicitation_type="SBIR Phase I",
            full_text="Text",
            technical_requirements="Requirements",
            evaluation_criteria="Criteria",
            funding_range_min=Decimal("100000.00"),
            funding_range_max=Decimal("300000.00"),
            proposal_deadline=date(2024, 6, 15),
            performance_period=12,
            keywords=[],
            cet_relevance_scores={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert solicitation.topic_number is None
        assert solicitation.award_start_date is None
        assert len(solicitation.keywords) == 0

    def test_solicitation_serialization(self):
        """Test solicitation can be serialized to dict."""
        solicitation = Solicitation(
            solicitation_id="SOL-2024-001",
            solicitation_number="N00014-24-S-B001",
            title="Test Solicitation",
            agency_code="DON",
            program_office_id="ONR-001",
            solicitation_type="SBIR Phase I",
            full_text="Text",
            technical_requirements="Requirements",
            evaluation_criteria="Criteria",
            funding_range_min=Decimal("100000.00"),
            funding_range_max=Decimal("300000.00"),
            proposal_deadline=date(2024, 6, 15),
            performance_period=12,
            keywords=["test"],
            cet_relevance_scores={"ai": 0.5},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        data = solicitation.model_dump()
        assert data["solicitation_id"] == "SOL-2024-001"
        assert data["keywords"] == ["test"]
        assert data["cet_relevance_scores"] == {"ai": 0.5}
