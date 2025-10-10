"""Unit tests for bootstrap CSV loader."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from sbir_cet_classifier.data.bootstrap import (
    BOOTSTRAP_REQUIRED_COLUMNS,
    BootstrapCSVError,
    BootstrapResult,
    _apply_column_mappings,
    _parse_amount,
    _parse_award_date,
    _prepare_award_dict,
    _validate_required_columns,
    load_bootstrap_csv,
)


class TestLoadBootstrapCSV:
    """Tests for load_bootstrap_csv main entry point."""

    def test_load_valid_csv(self, tmp_path: Path) -> None:
        """Should successfully load valid bootstrap CSV."""
        csv_path = tmp_path / "awards.csv"
        csv_path.write_text(
            "award_id,agency,abstract,award_amount,phase,firm_name\n"
            "ABC-001,DOD,Advanced materials research,150000,I,TechCorp\n"
            "ABC-002,NASA,Satellite navigation,250000,II,SpaceInc\n"
        )

        result = load_bootstrap_csv(csv_path)

        assert isinstance(result, BootstrapResult)
        assert result.total_rows == 2
        assert result.loaded_count == 2
        assert result.skipped_count == 0
        assert len(result.awards) == 2
        assert result.awards[0].award_id == "ABC-001"
        assert result.awards[0].agency == "DOD"
        assert result.awards[0].abstract == "Advanced materials research"
        assert result.awards[0].award_amount == 150000.0
        assert result.awards[0].source_version == "bootstrap_csv"

    def test_load_csv_with_missing_file(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError for missing CSV."""
        csv_path = tmp_path / "nonexistent.csv"

        with pytest.raises(FileNotFoundError, match="Bootstrap CSV not found"):
            load_bootstrap_csv(csv_path)

    def test_load_csv_with_missing_required_columns(self, tmp_path: Path) -> None:
        """Should raise BootstrapCSVError when required columns missing."""
        csv_path = tmp_path / "awards.csv"
        csv_path.write_text("award_id,agency\nABC-001,DOD\n")  # Missing abstract, award_amount

        with pytest.raises(BootstrapCSVError, match="missing required columns"):
            load_bootstrap_csv(csv_path)

    def test_load_empty_csv(self, tmp_path: Path) -> None:
        """Should raise BootstrapCSVError for empty CSV."""
        csv_path = tmp_path / "awards.csv"
        csv_path.write_text("award_id,agency,abstract,award_amount\n")  # Header only

        with pytest.raises(BootstrapCSVError, match="Bootstrap CSV is empty"):
            load_bootstrap_csv(csv_path)

    def test_load_csv_with_column_mappings(self, tmp_path: Path) -> None:
        """Should apply column mappings and load data correctly."""
        csv_path = tmp_path / "awards.csv"
        csv_path.write_text(
            "award_id,agency_code,abstract,amount,firm,state\n"
            "ABC-001,DOD,Research project,100000,TechCorp,CA\n"
        )

        result = load_bootstrap_csv(csv_path)

        assert result.loaded_count == 1
        assert "agency_code" in result.field_mappings
        assert result.field_mappings["agency_code"] == "agency"
        assert "amount" in result.field_mappings
        assert result.field_mappings["amount"] == "award_amount"
        assert result.awards[0].agency == "DOD"
        assert result.awards[0].award_amount == 100000.0
        assert result.awards[0].firm_name == "TechCorp"
        assert result.awards[0].firm_state == "CA"

    def test_load_csv_with_validation_errors(self, tmp_path: Path) -> None:
        """Should skip invalid rows and report skipped count."""
        csv_path = tmp_path / "awards.csv"
        csv_path.write_text(
            "award_id,agency,abstract,award_amount\n"
            "ABC-001,DOD,Valid abstract,150000\n"
            ",NASA,Missing award_id,250000\n"  # Invalid: missing award_id
            "ABC-003,NSF,Valid abstract,invalid_amount\n"  # Invalid: bad amount
            "ABC-004,NIH,Another valid,75000\n"
        )

        result = load_bootstrap_csv(csv_path)

        assert result.total_rows == 4
        assert result.loaded_count == 2
        assert result.skipped_count == 2
        assert len(result.awards) == 2
        assert result.awards[0].award_id == "ABC-001"
        assert result.awards[1].award_id == "ABC-004"

    def test_load_csv_with_all_optional_fields(self, tmp_path: Path) -> None:
        """Should load CSV with all optional fields present."""
        csv_path = tmp_path / "awards.csv"
        csv_path.write_text(
            "award_id,agency,abstract,award_amount,sub_agency,topic_code,keywords,"
            "phase,firm_name,firm_city,firm_state,award_date,program,solicitation_id,solicitation_year\n"
            "ABC-001,DOD,Research,150000,DARPA,TOPIC-123,AI;ML;robotics,"
            "I,TechCorp,Boston,MA,2023-06-15,SBIR,SOL-2023-001,2023\n"
        )

        result = load_bootstrap_csv(csv_path)

        assert result.loaded_count == 1
        award = result.awards[0]
        assert award.sub_agency == "DARPA"
        assert award.topic_code == "TOPIC-123"
        assert award.keywords == ["AI;ML;robotics"]
        assert award.phase == "I"
        assert award.firm_name == "TechCorp"
        assert award.firm_city == "Boston"
        assert award.firm_state == "MA"
        assert award.program == "SBIR"
        assert award.solicitation_id == "SOL-2023-001"
        assert award.solicitation_year == 2023


class TestColumnMappings:
    """Tests for column mapping logic."""

    def test_apply_column_mappings_with_known_mappings(self) -> None:
        """Should apply known column mappings."""
        df = pd.DataFrame({"award_id": ["A1"], "agency_code": ["DOD"], "firm": ["TechCorp"]})

        mappings = _apply_column_mappings(df)

        assert "agency_code" in mappings
        assert mappings["agency_code"] == "agency"
        assert "firm" in mappings
        assert mappings["firm"] == "firm_name"
        assert "agency" in df.columns
        assert "firm_name" in df.columns
        assert "agency_code" not in df.columns

    def test_apply_column_mappings_with_no_mappings_needed(self) -> None:
        """Should return empty dict when no mappings needed."""
        df = pd.DataFrame({"award_id": ["A1"], "agency": ["DOD"], "firm_name": ["TechCorp"]})

        mappings = _apply_column_mappings(df)

        assert mappings == {}
        assert list(df.columns) == ["award_id", "agency", "firm_name"]

    def test_apply_column_mappings_case_insensitive(self) -> None:
        """Should apply mappings case-insensitively."""
        df = pd.DataFrame({"AGENCY_CODE": ["DOD"], "Agency_Code": ["NASA"]})

        mappings = _apply_column_mappings(df)

        # Should map both columns to agency
        assert "AGENCY_CODE" in mappings or "Agency_Code" in mappings
        assert "agency" in df.columns

    def test_apply_column_mappings_preserves_canonical(self) -> None:
        """Should not overwrite existing canonical columns."""
        df = pd.DataFrame({"agency": ["DOD"], "agency_code": ["NASA"]})

        mappings = _apply_column_mappings(df)

        # Should not map agency_code if agency already exists
        assert "agency_code" not in mappings
        assert df["agency"].iloc[0] == "DOD"  # Original preserved


class TestValidateRequiredColumns:
    """Tests for required column validation."""

    def test_validate_with_all_required_columns(self) -> None:
        """Should pass validation with all required columns."""
        df = pd.DataFrame(columns=list(BOOTSTRAP_REQUIRED_COLUMNS))

        # Should not raise
        _validate_required_columns(df)

    def test_validate_with_missing_columns(self) -> None:
        """Should raise error with missing columns."""
        df = pd.DataFrame(columns=["award_id", "agency"])  # Missing abstract, award_amount

        with pytest.raises(BootstrapCSVError, match="missing required columns.*abstract.*award_amount"):
            _validate_required_columns(df)

    def test_validate_with_extra_columns(self) -> None:
        """Should pass validation with extra optional columns."""
        df = pd.DataFrame(columns=[*BOOTSTRAP_REQUIRED_COLUMNS, "extra_col_1", "extra_col_2"])

        # Should not raise
        _validate_required_columns(df)


class TestPrepareAwardDict:
    """Tests for award dictionary preparation."""

    def test_prepare_award_dict_minimal(self) -> None:
        """Should prepare award dict with only required fields."""
        row = pd.Series(
            {
                "award_id": "ABC-001",
                "agency": "DOD",
                "abstract": "Research project",
                "award_amount": "150000",
            }
        )
        ingested_at = datetime(2025, 10, 9, 12, 0, 0)

        result = _prepare_award_dict(row, ingested_at)

        assert result["award_id"] == "ABC-001"
        assert result["agency"] == "DOD"
        assert result["abstract"] == "Research project"
        assert result["award_amount"] == 150000.0
        assert result["ingested_at"] == ingested_at
        assert result["source_version"] == "bootstrap_csv"
        assert result["topic_code"] == "UNKNOWN"  # Default placeholder
        assert result["phase"] == "Other"  # Default

    def test_prepare_award_dict_with_optional_fields(self) -> None:
        """Should include optional fields when present."""
        row = pd.Series(
            {
                "award_id": "ABC-001",
                "agency": "DOD",
                "abstract": "Research",
                "award_amount": "150000",
                "sub_agency": "DARPA",
                "topic_code": "TOPIC-123",
                "keywords": "AI, ML, robotics",
                "phase": "I",
                "firm_name": "TechCorp",
                "firm_city": "Boston",
                "firm_state": "ma",
                "award_date": "2023",
                "program": "SBIR",
            }
        )
        ingested_at = datetime(2025, 10, 9, 12, 0, 0)

        result = _prepare_award_dict(row, ingested_at)

        assert result["sub_agency"] == "DARPA"
        assert result["topic_code"] == "TOPIC-123"
        assert result["keywords"] == ["AI", "ML", "robotics"]
        assert result["phase"] == "I"
        assert result["firm_name"] == "TechCorp"
        assert result["firm_city"] == "Boston"
        assert result["firm_state"] == "MA"  # Uppercased
        assert result["award_date"] == "2023"
        assert result["program"] == "SBIR"

    def test_prepare_award_dict_phase_normalization(self) -> None:
        """Should normalize phase values to canonical format."""
        test_cases = [
            ("I", "I"),
            ("1", "I"),
            ("ONE", "I"),
            ("II", "II"),
            ("2", "II"),
            ("TWO", "II"),
            ("III", "III"),
            ("3", "III"),
            ("THREE", "III"),
            ("IV", "Other"),
            ("Unknown", "Other"),
        ]

        for input_phase, expected_phase in test_cases:
            row = pd.Series(
                {
                    "award_id": "ABC-001",
                    "agency": "DOD",
                    "abstract": "Research",
                    "award_amount": "150000",
                    "phase": input_phase,
                }
            )
            result = _prepare_award_dict(row, datetime.now())
            assert result["phase"] == expected_phase, f"Phase '{input_phase}' should map to '{expected_phase}'"


class TestParseAmount:
    """Tests for amount parsing."""

    def test_parse_simple_amount(self) -> None:
        """Should parse simple numeric amount."""
        assert _parse_amount("150000") == 150000.0
        assert _parse_amount("150000.50") == 150000.5

    def test_parse_amount_with_currency_symbol(self) -> None:
        """Should strip currency symbols."""
        assert _parse_amount("$150000") == 150000.0
        assert _parse_amount("$150,000.00") == 150000.0

    def test_parse_amount_with_commas(self) -> None:
        """Should strip commas."""
        assert _parse_amount("150,000") == 150000.0
        assert _parse_amount("1,500,000.00") == 1500000.0

    def test_parse_amount_with_whitespace(self) -> None:
        """Should strip whitespace."""
        assert _parse_amount("  150000  ") == 150000.0
        assert _parse_amount(" $ 150,000 ") == 150000.0

    def test_parse_invalid_amount(self) -> None:
        """Should raise ValueError for invalid amounts."""
        with pytest.raises(ValueError, match="Invalid award amount"):
            _parse_amount("not_a_number")

        with pytest.raises(ValueError, match="Invalid award amount"):
            _parse_amount("")


class TestParseAwardDate:
    """Tests for award date parsing."""

    def test_parse_year_only(self) -> None:
        """Should preserve year-only dates."""
        assert _parse_award_date("2023") == "2023"
        assert _parse_award_date("2020") == "2020"

    def test_parse_iso_date(self) -> None:
        """Should normalize ISO dates."""
        assert _parse_award_date("2023-06-15") == "2023-06-15"

    def test_parse_various_date_formats(self) -> None:
        """Should parse various date formats to ISO."""
        # pandas can parse many formats
        result = _parse_award_date("06/15/2023")
        assert "2023" in result
        assert "06" in result
        assert "15" in result

    def test_parse_invalid_date(self) -> None:
        """Should return original string for unparseable dates."""
        assert _parse_award_date("invalid") == "invalid"
        assert _parse_award_date("??/??/????") == "??/??/????"
