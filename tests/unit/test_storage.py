"""Tests for Parquet schema extensions and enriched data storage."""

import pytest
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

from sbir_cet_classifier.data.storage import (
    EnrichedDataWriter,
    ParquetSchemaManager,
    AwardeeProfileWriter,
    ProgramOfficeWriter,
    SolicitationWriter,
    AwardModificationWriter,
)
from sbir_cet_classifier.data.enrichment.schemas import (
    AwardeeProfile,
    ProgramOffice,
    Solicitation,
    AwardModification,
)


class TestParquetSchemaManager:
    """Test Parquet schema management for enriched data."""
    
    def test_awardee_profile_schema(self):
        """Test awardee profile Parquet schema definition."""
        schema = ParquetSchemaManager.get_awardee_profile_schema()
        
        expected_fields = [
            "uei", "legal_name", "total_awards", "total_funding",
            "success_rate", "avg_award_amount", "first_award_date",
            "last_award_date", "primary_agencies", "technology_areas"
        ]
        
        schema_fields = [field.name for field in schema]
        for field in expected_fields:
            assert field in schema_fields
            
        # Check specific field types
        uei_field = next(f for f in schema if f.name == "uei")
        assert uei_field.type == pa.string()
        
        total_awards_field = next(f for f in schema if f.name == "total_awards")
        assert total_awards_field.type == pa.int64()
        
        success_rate_field = next(f for f in schema if f.name == "success_rate")
        assert success_rate_field.type == pa.float64()
        
    def test_program_office_schema(self):
        """Test program office Parquet schema definition."""
        schema = ParquetSchemaManager.get_program_office_schema()
        
        expected_fields = [
            "agency", "office_name", "office_code", "contact_email",
            "strategic_focus", "annual_budget", "active_programs"
        ]
        
        schema_fields = [field.name for field in schema]
        for field in expected_fields:
            assert field in schema_fields
            
    def test_solicitation_schema(self):
        """Test solicitation Parquet schema definition."""
        schema = ParquetSchemaManager.get_solicitation_schema()
        
        expected_fields = [
            "solicitation_id", "title", "full_text", "technical_requirements",
            "evaluation_criteria", "topic_areas", "funding_range_min",
            "funding_range_max", "submission_deadline"
        ]
        
        schema_fields = [field.name for field in schema]
        for field in expected_fields:
            assert field in schema_fields
            
    def test_award_modification_schema(self):
        """Test award modification Parquet schema definition."""
        schema = ParquetSchemaManager.get_award_modification_schema()
        
        expected_fields = [
            "modification_id", "award_id", "modification_type",
            "modification_date", "funding_change", "scope_change",
            "new_end_date", "justification"
        ]
        
        schema_fields = [field.name for field in schema]
        for field in expected_fields:
            assert field in schema_fields
            
    def test_schema_compatibility(self):
        """Test schema compatibility with existing data."""
        # Test that new schemas are compatible with existing award schema
        existing_schema = ParquetSchemaManager.get_existing_award_schema()
        awardee_schema = ParquetSchemaManager.get_awardee_profile_schema()
        
        # Should not have conflicting field names with different types
        existing_fields = {f.name: f.type for f in existing_schema}
        awardee_fields = {f.name: f.type for f in awardee_schema}
        
        # Check for any overlapping field names
        overlapping_fields = set(existing_fields.keys()) & set(awardee_fields.keys())
        
        # If there are overlapping fields, they should have compatible types
        for field_name in overlapping_fields:
            existing_type = existing_fields[field_name]
            awardee_type = awardee_fields[field_name]
            # Types should be the same or compatible
            assert existing_type == awardee_type or self._types_compatible(existing_type, awardee_type)
            
    def _types_compatible(self, type1, type2):
        """Check if two PyArrow types are compatible."""
        # Simple compatibility check - can be extended
        if type1 == type2:
            return True
        # String types are generally compatible
        if pa.types.is_string(type1) and pa.types.is_string(type2):
            return True
        return False


class TestAwardeeProfileWriter:
    """Test awardee profile data writer."""
    
    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create temporary parquet file path."""
        return tmp_path / "awardee_profiles.parquet"
    
    @pytest.fixture
    def sample_profiles(self):
        """Create sample awardee profiles for testing."""
        return [
            AwardeeProfile(
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
            ),
            AwardeeProfile(
                uei="XYZ789GHI012",
                legal_name="Research Solutions Inc",
                total_awards=8,
                total_funding=Decimal("2000000.00"),
                success_rate=0.75,
                avg_award_amount=Decimal("250000.00"),
                first_award_date=datetime(2020, 6, 15),
                last_award_date=datetime(2024, 3, 1),
                primary_agencies=["NIH", "NSF"],
                technology_areas=["Biotech", "Medical Devices"]
            )
        ]
    
    def test_write_awardee_profiles(self, temp_file, sample_profiles):
        """Test writing awardee profiles to Parquet."""
        writer = AwardeeProfileWriter(temp_file)
        writer.write(sample_profiles)
        
        # Verify file was created
        assert temp_file.exists()
        
        # Read back and verify data
        df = pd.read_parquet(temp_file)
        assert len(df) == 2
        assert df.iloc[0]["uei"] == "ABC123DEF456"
        assert df.iloc[1]["legal_name"] == "Research Solutions Inc"
        
    def test_append_awardee_profiles(self, temp_file, sample_profiles):
        """Test appending to existing awardee profiles file."""
        writer = AwardeeProfileWriter(temp_file)
        
        # Write initial profiles
        writer.write(sample_profiles[:1])
        
        # Append additional profile
        writer.append(sample_profiles[1:])
        
        # Verify combined data
        df = pd.read_parquet(temp_file)
        assert len(df) == 2
        
    def test_update_existing_profile(self, temp_file, sample_profiles):
        """Test updating existing awardee profile."""
        writer = AwardeeProfileWriter(temp_file)
        
        # Write initial profile
        writer.write(sample_profiles[:1])
        
        # Update the profile
        updated_profile = sample_profiles[0]
        updated_profile.total_awards = 20  # Increase award count
        updated_profile.total_funding = Decimal("6000000.00")
        
        writer.update([updated_profile])
        
        # Verify update
        df = pd.read_parquet(temp_file)
        assert len(df) == 1  # Should still be one record
        assert df.iloc[0]["total_awards"] == 20
        
    def test_data_type_preservation(self, temp_file, sample_profiles):
        """Test that data types are preserved in Parquet."""
        writer = AwardeeProfileWriter(temp_file)
        writer.write(sample_profiles)
        
        # Read back with PyArrow to check types
        table = pq.read_table(temp_file)
        
        # Check that decimal fields are preserved as appropriate types
        funding_column = table.column("total_funding")
        assert pa.types.is_decimal(funding_column.type) or pa.types.is_float(funding_column.type)
        
        # Check that list fields are preserved
        agencies_column = table.column("primary_agencies")
        assert pa.types.is_list(agencies_column.type)


class TestProgramOfficeWriter:
    """Test program office data writer."""
    
    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create temporary parquet file path."""
        return tmp_path / "program_offices.parquet"
    
    @pytest.fixture
    def sample_offices(self):
        """Create sample program offices for testing."""
        return [
            ProgramOffice(
                agency="NSF",
                office_name="Computer and Information Science and Engineering",
                office_code="CISE",
                contact_email="cise@nsf.gov",
                strategic_focus=["AI", "Cybersecurity", "Quantum Computing"],
                annual_budget=Decimal("500000000.00"),
                active_programs=25
            ),
            ProgramOffice(
                agency="DOD",
                office_name="Defense Advanced Research Projects Agency",
                office_code="DARPA",
                contact_email="info@darpa.mil",
                strategic_focus=["Advanced Materials", "Hypersonics", "AI"],
                annual_budget=Decimal("3500000000.00"),
                active_programs=50
            )
        ]
    
    def test_write_program_offices(self, temp_file, sample_offices):
        """Test writing program offices to Parquet."""
        writer = ProgramOfficeWriter(temp_file)
        writer.write(sample_offices)
        
        # Verify file was created
        assert temp_file.exists()
        
        # Read back and verify data
        df = pd.read_parquet(temp_file)
        assert len(df) == 2
        assert df.iloc[0]["agency"] == "NSF"
        assert df.iloc[1]["office_code"] == "DARPA"


class TestSolicitationWriter:
    """Test solicitation data writer."""
    
    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create temporary parquet file path."""
        return tmp_path / "solicitations.parquet"
    
    @pytest.fixture
    def sample_solicitations(self):
        """Create sample solicitations for testing."""
        return [
            Solicitation(
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
        ]
    
    def test_write_solicitations(self, temp_file, sample_solicitations):
        """Test writing solicitations to Parquet."""
        writer = SolicitationWriter(temp_file)
        writer.write(sample_solicitations)
        
        # Verify file was created
        assert temp_file.exists()
        
        # Read back and verify data
        df = pd.read_parquet(temp_file)
        assert len(df) == 1
        assert df.iloc[0]["solicitation_id"] == "SOL-2024-001"


class TestAwardModificationWriter:
    """Test award modification data writer."""
    
    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create temporary parquet file path."""
        return tmp_path / "award_modifications.parquet"
    
    @pytest.fixture
    def sample_modifications(self):
        """Create sample award modifications for testing."""
        return [
            AwardModification(
                modification_id="MOD-001",
                award_id="AWARD-2024-001",
                modification_type="Funding Increase",
                modification_date=datetime(2024, 6, 15),
                funding_change=Decimal("50000.00"),
                scope_change="Added Phase II option",
                new_end_date=datetime(2025, 12, 31),
                justification="Successful Phase I completion"
            )
        ]
    
    def test_write_modifications(self, temp_file, sample_modifications):
        """Test writing award modifications to Parquet."""
        writer = AwardModificationWriter(temp_file)
        writer.write(sample_modifications)
        
        # Verify file was created
        assert temp_file.exists()
        
        # Read back and verify data
        df = pd.read_parquet(temp_file)
        assert len(df) == 1
        assert df.iloc[0]["modification_id"] == "MOD-001"


class TestEnrichedDataWriter:
    """Test unified enriched data writer."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for enriched data."""
        return tmp_path / "enriched_data"
    
    def test_write_all_enrichment_types(self, temp_dir, sample_profiles, sample_offices, 
                                       sample_solicitations, sample_modifications):
        """Test writing all enrichment data types."""
        writer = EnrichedDataWriter(temp_dir)
        
        # Write all data types
        writer.write_awardee_profiles(sample_profiles)
        writer.write_program_offices(sample_offices)
        writer.write_solicitations(sample_solicitations)
        writer.write_award_modifications(sample_modifications)
        
        # Verify all files were created
        assert (temp_dir / "awardee_profiles.parquet").exists()
        assert (temp_dir / "program_offices.parquet").exists()
        assert (temp_dir / "solicitations.parquet").exists()
        assert (temp_dir / "award_modifications.parquet").exists()
        
    def test_batch_write_performance(self, temp_dir):
        """Test performance of batch writing large datasets."""
        # Create large dataset for performance testing
        large_profiles = []
        for i in range(1000):
            profile = AwardeeProfile(
                uei=f"UEI{i:06d}",
                legal_name=f"Company {i}",
                total_awards=i % 50 + 1,
                total_funding=Decimal(str((i % 50 + 1) * 100000)),
                success_rate=0.5 + (i % 50) / 100,
                avg_award_amount=Decimal("100000.00"),
                first_award_date=datetime(2020, 1, 1),
                last_award_date=datetime(2024, 1, 1),
                primary_agencies=["NSF"],
                technology_areas=["AI"]
            )
            large_profiles.append(profile)
        
        writer = EnrichedDataWriter(temp_dir)
        
        # Time the write operation
        import time
        start_time = time.time()
        writer.write_awardee_profiles(large_profiles)
        end_time = time.time()
        
        # Should complete within reasonable time (adjust threshold as needed)
        write_time = end_time - start_time
        assert write_time < 5.0  # Should complete within 5 seconds
        
        # Verify data integrity
        df = pd.read_parquet(temp_dir / "awardee_profiles.parquet")
        assert len(df) == 1000
        
    def test_concurrent_writes(self, temp_dir):
        """Test concurrent writing to different files."""
        import threading
        
        writer = EnrichedDataWriter(temp_dir)
        
        def write_profiles():
            profiles = [AwardeeProfile(
                uei="TEST001",
                legal_name="Test Company",
                total_awards=1,
                total_funding=Decimal("100000.00"),
                success_rate=1.0,
                avg_award_amount=Decimal("100000.00"),
                first_award_date=datetime(2024, 1, 1),
                last_award_date=datetime(2024, 1, 1),
                primary_agencies=["NSF"],
                technology_areas=["AI"]
            )]
            writer.write_awardee_profiles(profiles)
        
        def write_offices():
            offices = [ProgramOffice(
                agency="NSF",
                office_name="Test Office",
                office_code="TEST",
                strategic_focus=["AI"],
                annual_budget=Decimal("1000000.00"),
                active_programs=1
            )]
            writer.write_program_offices(offices)
        
        # Start concurrent writes
        thread1 = threading.Thread(target=write_profiles)
        thread2 = threading.Thread(target=write_offices)
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Verify both files were created successfully
        assert (temp_dir / "awardee_profiles.parquet").exists()
        assert (temp_dir / "program_offices.parquet").exists()


class TestSchemaEvolution:
    """Test schema evolution and backward compatibility."""
    
    def test_schema_version_compatibility(self, tmp_path):
        """Test that new schema versions are backward compatible."""
        # This test would verify that new schema versions can read old data
        # Implementation depends on specific versioning strategy
        pass
        
    def test_missing_optional_fields(self, tmp_path):
        """Test handling of missing optional fields in existing data."""
        # Create data with minimal required fields
        minimal_data = pd.DataFrame([{
            "uei": "TEST001",
            "legal_name": "Test Company",
            "total_awards": 1,
            "total_funding": 100000.0,
            "success_rate": 1.0,
            "avg_award_amount": 100000.0,
            "first_award_date": datetime(2024, 1, 1),
            "last_award_date": datetime(2024, 1, 1),
            # Missing optional fields: primary_agencies, technology_areas
        }])
        
        file_path = tmp_path / "minimal_profiles.parquet"
        minimal_data.to_parquet(file_path)
        
        # Should be able to read back without errors
        df = pd.read_parquet(file_path)
        assert len(df) == 1
        assert df.iloc[0]["uei"] == "TEST001"
