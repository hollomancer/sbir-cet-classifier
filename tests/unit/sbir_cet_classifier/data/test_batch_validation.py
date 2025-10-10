"""Tests for batch validation utilities."""

import pandas as pd
import pytest

from sbir_cet_classifier.data.batch_validation import (
    normalize_agencies_batch,
    optimize_dtypes,
    prevalidate_batch,
)


class TestPrevalidateBatch:
    """Test batch pre-validation."""

    def test_filters_missing_text(self):
        """Test filtering records without abstract or keywords."""
        df = pd.DataFrame({
            "award_id": ["A1", "A2", "A3"],
            "agency": ["NASA", "DOD", "NSF"],
            "abstract": ["Valid text", "", None],
            "keywords": ["", "Valid keywords", ""],
            "award_amount": [100000, 200000, 300000],
            "award_date": ["2023-01-01", "2023-02-01", "2023-03-01"],
        })
        
        valid, invalid = prevalidate_batch(df)
        
        assert len(valid) == 2  # A1 has abstract, A2 has keywords
        assert len(invalid) == 1  # A3 has neither

    def test_filters_negative_amounts(self):
        """Test filtering negative award amounts."""
        df = pd.DataFrame({
            "award_id": ["A1", "A2"],
            "agency": ["NASA", "DOD"],
            "abstract": ["Text", "Text"],
            "award_amount": [100000, -50000],
            "award_date": ["2023-01-01", "2023-02-01"],
        })
        
        valid, invalid = prevalidate_batch(df)
        
        assert len(valid) == 1
        assert valid.iloc[0]["award_id"] == "A1"

    def test_filters_missing_dates(self):
        """Test filtering missing award dates."""
        df = pd.DataFrame({
            "award_id": ["A1", "A2"],
            "agency": ["NASA", "DOD"],
            "abstract": ["Text", "Text"],
            "award_amount": [100000, 200000],
            "award_date": ["2023-01-01", None],
        })
        
        valid, invalid = prevalidate_batch(df)
        
        assert len(valid) == 1
        assert valid.iloc[0]["award_id"] == "A1"

    def test_all_valid(self):
        """Test batch with all valid records."""
        df = pd.DataFrame({
            "award_id": ["A1", "A2"],
            "agency": ["NASA", "DOD"],
            "abstract": ["Text 1", "Text 2"],
            "award_amount": [100000, 200000],
            "award_date": ["2023-01-01", "2023-02-01"],
        })
        
        valid, invalid = prevalidate_batch(df)
        
        assert len(valid) == 2
        assert len(invalid) == 0


class TestNormalizeAgenciesBatch:
    """Test batch agency normalization."""

    def test_normalizes_agencies(self):
        """Test agency names are normalized in batch."""
        df = pd.DataFrame({
            "agency": [
                "National Aeronautics and Space Administration",
                "Department of Defense",
                "NASA",
            ]
        })
        
        result = normalize_agencies_batch(df)
        
        assert result["agency"].tolist() == ["NASA", "DOD", "NASA"]

    def test_handles_missing_column(self):
        """Test handles DataFrame without agency column."""
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        
        result = normalize_agencies_batch(df)
        
        assert "agency" not in result.columns


class TestOptimizeDtypes:
    """Test dtype optimization."""

    def test_converts_to_categorical(self):
        """Test categorical columns are converted."""
        df = pd.DataFrame({
            "agency": ["NASA", "DOD", "NASA", "DOD"],
            "phase": ["I", "II", "I", "II"],
            "firm_state": ["CA", "TX", "CA", "TX"],
        })
        
        result = optimize_dtypes(df)
        
        assert result["agency"].dtype.name == "category"
        assert result["phase"].dtype.name == "category"
        assert result["firm_state"].dtype.name == "category"

    def test_converts_to_string(self):
        """Test string columns are converted."""
        df = pd.DataFrame({
            "award_id": ["A1", "A2"],
            "abstract": ["Text 1", "Text 2"],
        })
        
        result = optimize_dtypes(df)
        
        assert result["award_id"].dtype.name == "string"
        assert result["abstract"].dtype.name == "string"

    def test_converts_numeric(self):
        """Test numeric conversions."""
        df = pd.DataFrame({
            "award_amount": ["100000", "200000"],
            "solicitation_year": ["2023", "2024"],
        })
        
        result = optimize_dtypes(df)
        
        assert pd.api.types.is_numeric_dtype(result["award_amount"])
        assert result["solicitation_year"].dtype.name == "Int16"
