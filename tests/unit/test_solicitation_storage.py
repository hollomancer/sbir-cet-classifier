"""Tests for solicitation Parquet storage."""

import pytest
import pandas as pd
import pyarrow as pa
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from sbir_cet_classifier.data.storage import SolicitationStorage
from sbir_cet_classifier.data.enrichment.models import Solicitation


class TestSolicitationStorage:
    """Test SolicitationStorage."""

    @pytest.fixture
    def temp_storage_path(self, tmp_path):
        """Create temporary storage path."""
        return tmp_path / "solicitations.parquet"

    @pytest.fixture
    def storage(self, temp_storage_path):
        """Create SolicitationStorage with temp path."""
        return SolicitationStorage(file_path=temp_storage_path)

    @pytest.fixture
    def sample_solicitations(self):
        """Create sample solicitation data."""
        return [
            Solicitation(
                solicitation_id="SOL-2024-001",
                solicitation_number="N00014-24-S-B001",
                title="Advanced Materials Research",
                agency_code="DON",
                program_office_id="ONR-001",
                solicitation_type="SBIR Phase I",
                topic_number="N241-001",
                full_text="Complete solicitation text for materials research...",
                technical_requirements="Technical requirements for materials...",
                evaluation_criteria="Evaluation criteria for proposals...",
                funding_range_min=Decimal("100000.00"),
                funding_range_max=Decimal("300000.00"),
                proposal_deadline=date(2024, 6, 15),
                award_start_date=date(2024, 9, 1),
                performance_period=12,
                keywords=["materials", "nanotechnology", "composites"],
                cet_relevance_scores={"advanced_materials": 0.95, "nanotechnology": 0.8},
                created_at=datetime(2024, 1, 1, 12, 0, 0),
                updated_at=datetime(2024, 1, 1, 12, 0, 0)
            ),
            Solicitation(
                solicitation_id="SOL-2024-002",
                solicitation_number="W911NF-24-S-0001",
                title="Artificial Intelligence Applications",
                agency_code="DOD",
                program_office_id="ARO-001",
                solicitation_type="SBIR Phase II",
                topic_number="A241-001",
                full_text="Complete solicitation text for AI research...",
                technical_requirements="Technical requirements for AI...",
                evaluation_criteria="Evaluation criteria for AI proposals...",
                funding_range_min=Decimal("500000.00"),
                funding_range_max=Decimal("1000000.00"),
                proposal_deadline=date(2024, 7, 15),
                award_start_date=date(2024, 10, 1),
                performance_period=24,
                keywords=["artificial intelligence", "machine learning", "neural networks"],
                cet_relevance_scores={"artificial_intelligence": 0.98, "machine_learning": 0.9},
                created_at=datetime(2024, 1, 2, 12, 0, 0),
                updated_at=datetime(2024, 1, 2, 12, 0, 0)
            )
        ]

    def test_parquet_schema_definition(self, storage):
        """Test Parquet schema for solicitations."""
        schema = storage.get_parquet_schema()
        
        expected_fields = [
            "solicitation_id", "solicitation_number", "title", "agency_code",
            "program_office_id", "solicitation_type", "topic_number", "full_text",
            "technical_requirements", "evaluation_criteria", "funding_range_min",
            "funding_range_max", "proposal_deadline", "award_start_date",
            "performance_period", "keywords", "cet_relevance_scores",
            "created_at", "updated_at"
        ]
        
        schema_fields = [field.name for field in schema]
        for field in expected_fields:
            assert field in schema_fields

    def test_save_solicitations(self, storage, sample_solicitations, temp_storage_path):
        """Test saving solicitations to Parquet."""
        storage.save_solicitations(sample_solicitations)
        
        assert temp_storage_path.exists()
        
        # Verify data can be read back
        df = pd.read_parquet(temp_storage_path)
        assert len(df) == 2
        assert "SOL-2024-001" in df["solicitation_id"].values
        assert "SOL-2024-002" in df["solicitation_id"].values

    def test_load_solicitations(self, storage, sample_solicitations, temp_storage_path):
        """Test loading solicitations from Parquet."""
        # First save data
        storage.save_solicitations(sample_solicitations)
        
        # Then load it back
        loaded_solicitations = storage.load_solicitations()
        
        assert len(loaded_solicitations) == 2
        assert all(isinstance(sol, Solicitation) for sol in loaded_solicitations)
        
        # Verify data integrity
        sol1 = next(sol for sol in loaded_solicitations if sol.solicitation_id == "SOL-2024-001")
        assert sol1.title == "Advanced Materials Research"
        assert sol1.funding_range_min == Decimal("100000.00")
        assert len(sol1.keywords) == 3

    def test_load_solicitations_empty_file(self, storage):
        """Test loading from non-existent file."""
        solicitations = storage.load_solicitations()
        assert solicitations == []

    def test_append_solicitations(self, storage, sample_solicitations, temp_storage_path):
        """Test appending solicitations to existing file."""
        # Save initial data
        storage.save_solicitations([sample_solicitations[0]])
        
        # Append new data
        new_solicitation = Solicitation(
            solicitation_id="SOL-2024-003",
            solicitation_number="FA8750-24-S-0001",
            title="Cybersecurity Research",
            agency_code="USAF",
            program_office_id="AFRL-001",
            solicitation_type="SBIR Phase I",
            full_text="Cybersecurity solicitation text...",
            technical_requirements="Cybersecurity requirements...",
            evaluation_criteria="Cybersecurity evaluation...",
            funding_range_min=Decimal("150000.00"),
            funding_range_max=Decimal("350000.00"),
            proposal_deadline=date(2024, 8, 15),
            performance_period=12,
            keywords=["cybersecurity", "encryption"],
            cet_relevance_scores={"cybersecurity": 0.95},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        storage.append_solicitations([new_solicitation])
        
        # Verify all data is present
        all_solicitations = storage.load_solicitations()
        assert len(all_solicitations) == 2
        
        solicitation_ids = [sol.solicitation_id for sol in all_solicitations]
        assert "SOL-2024-001" in solicitation_ids
        assert "SOL-2024-003" in solicitation_ids

    def test_find_solicitation_by_id(self, storage, sample_solicitations):
        """Test finding solicitation by ID."""
        storage.save_solicitations(sample_solicitations)
        
        found = storage.find_solicitation_by_id("SOL-2024-001")
        assert found is not None
        assert found.title == "Advanced Materials Research"
        
        not_found = storage.find_solicitation_by_id("NONEXISTENT")
        assert not_found is None

    def test_find_solicitations_by_agency(self, storage, sample_solicitations):
        """Test finding solicitations by agency."""
        storage.save_solicitations(sample_solicitations)
        
        don_solicitations = storage.find_solicitations_by_agency("DON")
        assert len(don_solicitations) == 1
        assert don_solicitations[0].agency_code == "DON"
        
        dod_solicitations = storage.find_solicitations_by_agency("DOD")
        assert len(dod_solicitations) == 1
        assert dod_solicitations[0].agency_code == "DOD"

    def test_data_type_preservation(self, storage, sample_solicitations, temp_storage_path):
        """Test that data types are preserved during save/load."""
        storage.save_solicitations(sample_solicitations)
        loaded = storage.load_solicitations()
        
        sol = loaded[0]
        
        # Test decimal preservation
        assert isinstance(sol.funding_range_min, Decimal)
        assert sol.funding_range_min == Decimal("100000.00")
        
        # Test date preservation
        assert isinstance(sol.proposal_deadline, date)
        assert sol.proposal_deadline == date(2024, 6, 15)
        
        # Test datetime preservation
        assert isinstance(sol.created_at, datetime)
        
        # Test list preservation
        assert isinstance(sol.keywords, list)
        assert len(sol.keywords) == 3
        
        # Test dict preservation
        assert isinstance(sol.cet_relevance_scores, dict)
        assert sol.cet_relevance_scores["advanced_materials"] == 0.95

    def test_large_text_handling(self, storage, temp_storage_path):
        """Test handling of large text fields."""
        large_text = "A" * 10000  # 10KB text
        
        solicitation = Solicitation(
            solicitation_id="SOL-LARGE-001",
            solicitation_number="LARGE-001",
            title="Large Text Test",
            agency_code="TEST",
            program_office_id="TEST-001",
            solicitation_type="SBIR Phase I",
            full_text=large_text,
            technical_requirements=large_text,
            evaluation_criteria=large_text,
            funding_range_min=Decimal("100000.00"),
            funding_range_max=Decimal("300000.00"),
            proposal_deadline=date(2024, 6, 15),
            performance_period=12,
            keywords=[],
            cet_relevance_scores={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        storage.save_solicitations([solicitation])
        loaded = storage.load_solicitations()
        
        assert len(loaded[0].full_text) == 10000
        assert loaded[0].full_text == large_text

    def test_unicode_text_handling(self, storage, temp_storage_path):
        """Test handling of Unicode text."""
        unicode_text = "Research in naïve Bayesian algorithms and Schrödinger's quantum mechanics"
        
        solicitation = Solicitation(
            solicitation_id="SOL-UNICODE-001",
            solicitation_number="UNICODE-001",
            title=unicode_text,
            agency_code="TEST",
            program_office_id="TEST-001",
            solicitation_type="SBIR Phase I",
            full_text=unicode_text,
            technical_requirements=unicode_text,
            evaluation_criteria=unicode_text,
            funding_range_min=Decimal("100000.00"),
            funding_range_max=Decimal("300000.00"),
            proposal_deadline=date(2024, 6, 15),
            performance_period=12,
            keywords=["naïve", "Schrödinger"],
            cet_relevance_scores={},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        storage.save_solicitations([solicitation])
        loaded = storage.load_solicitations()
        
        assert loaded[0].title == unicode_text
        assert "naïve" in loaded[0].keywords
        assert "Schrödinger" in loaded[0].keywords

    def test_storage_error_handling(self, storage, sample_solicitations):
        """Test storage error handling."""
        # Test with invalid path
        invalid_storage = SolicitationStorage(file_path="/invalid/path/solicitations.parquet")
        
        with pytest.raises(Exception):
            invalid_storage.save_solicitations(sample_solicitations)

    def test_concurrent_access_safety(self, storage, sample_solicitations, temp_storage_path):
        """Test thread-safe storage operations."""
        import threading
        import time
        
        def save_data(solicitations, delay=0):
            time.sleep(delay)
            storage.save_solicitations(solicitations)
        
        # Start concurrent save operations
        thread1 = threading.Thread(target=save_data, args=([sample_solicitations[0]], 0.1))
        thread2 = threading.Thread(target=save_data, args=([sample_solicitations[1]], 0.1))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Verify file exists and is readable
        assert temp_storage_path.exists()
        loaded = storage.load_solicitations()
        assert len(loaded) >= 1  # At least one should have been saved
