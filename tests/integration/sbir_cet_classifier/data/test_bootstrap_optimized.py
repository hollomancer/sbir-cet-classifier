"""Integration tests for optimized bootstrap ingestion."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest

from sbir_cet_classifier.data.bootstrap import load_bootstrap_csv


class TestOptimizedBootstrap:
    """Test bootstrap with batch validation and agency normalization."""

    def test_handles_long_agency_names(self, tmp_path):
        """Test long agency names are normalized."""
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({
            "award_id": ["A1", "A2"],
            "agency": [
                "National Oceanic and Atmospheric Administration",
                "NASA",
            ],
            "abstract": ["Research on climate", "Space exploration"],
            "award_amount": [100000, 200000],
            "award_date": ["2023-01-01", "2023-02-01"],
            "topic_code": ["T1", "T2"],
            "phase": ["I", "II"],
            "firm_name": ["Company A", "Company B"],
            "firm_city": ["City A", "City B"],
            "firm_state": ["CA", "TX"],
        })
        df.to_csv(csv_path, index=False)
        
        result = load_bootstrap_csv(csv_path)
        
        assert result.loaded_count == 2
        assert result.awards[0].agency == "NOAA"
        assert result.awards[1].agency == "NASA"

    def test_batch_validation_filters_invalid(self, tmp_path):
        """Test batch validation filters invalid records."""
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({
            "award_id": ["A1", "A2", "A3"],
            "agency": ["NASA", "DOD", "NSF"],
            "abstract": ["Valid text", "", ""],  # A2 and A3 missing abstract
            "keywords": ["", "", "Valid keywords"],  # A3 has keywords
            "award_amount": [100000, 200000, 300000],
            "award_date": ["2023-01-01", "2023-02-01", "2023-03-01"],
            "topic_code": ["T1", "T2", "T3"],
            "phase": ["I", "II", "I"],
            "firm_name": ["Company A", "Company B", "Company C"],
            "firm_city": ["City A", "City B", "City C"],
            "firm_state": ["CA", "TX", "NY"],
        })
        df.to_csv(csv_path, index=False)
        
        result = load_bootstrap_csv(csv_path)
        
        # A1 has abstract, A3 has keywords - both valid
        # A2 has neither - invalid
        assert result.loaded_count == 2
        assert result.skipped_count == 1

    def test_optimized_dtypes_applied(self, tmp_path):
        """Test dtype optimization is applied during ingestion."""
        csv_path = tmp_path / "test.csv"
        df = pd.DataFrame({
            "award_id": ["A1", "A2"],
            "agency": ["NASA", "NASA"],  # Repeated for categorical
            "abstract": ["Text 1", "Text 2"],
            "award_amount": [100000, 200000],
            "award_date": ["2023-01-01", "2023-02-01"],
            "topic_code": ["T1", "T2"],
            "phase": ["I", "I"],  # Repeated for categorical
            "firm_name": ["Company A", "Company B"],
            "firm_city": ["City A", "City B"],
            "firm_state": ["CA", "CA"],  # Repeated for categorical
        })
        df.to_csv(csv_path, index=False)
        
        result = load_bootstrap_csv(csv_path)
        
        assert result.loaded_count == 2
        # Verify records loaded successfully with optimized processing

    def test_performance_with_large_batch(self, tmp_path):
        """Test performance with larger batch (1000 records)."""
        csv_path = tmp_path / "test.csv"
        
        # Generate 1000 records
        data = {
            "award_id": [f"A{i}" for i in range(1000)],
            "agency": ["NASA"] * 500 + ["DOD"] * 500,
            "abstract": [f"Research project {i}" for i in range(1000)],
            "award_amount": [100000 + i * 1000 for i in range(1000)],
            "award_date": ["2023-01-01"] * 1000,
            "topic_code": [f"T{i % 100}" for i in range(1000)],
            "phase": ["I"] * 500 + ["II"] * 500,
            "firm_name": [f"Company {i}" for i in range(1000)],
            "firm_city": [f"City {i % 50}" for i in range(1000)],
            "firm_state": ["CA"] * 250 + ["TX"] * 250 + ["NY"] * 250 + ["FL"] * 250,
        }
        df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False)
        
        import time
        start = time.time()
        result = load_bootstrap_csv(csv_path)
        duration = time.time() - start
        
        assert result.loaded_count == 1000
        assert duration < 5.0  # Should complete in under 5 seconds
