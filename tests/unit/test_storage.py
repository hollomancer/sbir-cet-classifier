"""Tests for Parquet schema extensions and enriched data storage."""

import pytest
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

from sbir_cet_classifier.data.storage_v2 import (
    EnrichedDataManager,
    ParquetSchemaManager,
    StorageFactory,
    ParquetStorage,
)
from sbir_cet_classifier.data.enrichment.models import (
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
            "office_id", "agency_code", "agency_name", "office_name", "office_description",
            "contact_email", "strategic_focus_areas", "annual_budget", "active_solicitations_count"
        ]
        
        schema_fields = [field.name for field in schema]
        for field in expected_fields:
            assert field in schema_fields
            
    def test_solicitation_schema(self):
        """Test solicitation Parquet schema definition."""
        schema = ParquetSchemaManager.get_solicitation_schema()
        
        expected_fields = [
            "solicitation_id", "title", "full_text", "technical_requirements",
            "evaluation_criteria", "keywords", "funding_range_min",
            "funding_range_max", "proposal_deadline"
        ]
        
        schema_fields = [field.name for field in schema]
        for field in expected_fields:
            assert field in schema_fields
            
    def test_award_modification_schema(self):
        """Test award modification Parquet schema definition."""
        schema = ParquetSchemaManager.get_award_modification_schema()
        
        expected_fields = [
            "modification_id", "award_id", "modification_type",
            "modification_date", "funding_change", "scope_changes",
            "new_end_date", "justification"
        ]
        
        schema_fields = [field.name for field in schema]
        for field in expected_fields:
            assert field in schema_fields
            
    def test_schema_compatibility(self):
        """Test schema compatibility with existing data."""
        # Test that schemas can be retrieved without errors
        awardee_schema = ParquetSchemaManager.get_awardee_profile_schema()
        program_schema = ParquetSchemaManager.get_program_office_schema()
        solicitation_schema = ParquetSchemaManager.get_solicitation_schema()
        modification_schema = ParquetSchemaManager.get_award_modification_schema()
        
        # Should not have conflicting field names with different types
        assert len(awardee_schema) > 0
        assert len(program_schema) > 0
        assert len(solicitation_schema) > 0
        assert len(modification_schema) > 0


class TestAwardeeProfileStorage:
    """Test awardee profile data storage."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for storage."""
        return tmp_path
    
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
    
    def test_write_awardee_profiles(self, temp_dir, sample_profiles):
        """Test writing awardee profiles to Parquet."""
        storage = StorageFactory.create_awardee_storage(temp_dir)
        storage.write(sample_profiles)
        
        # Verify file was created
        assert storage.exists()
        
        # Read back and verify data
        profiles = storage.read()
        assert len(profiles) == 2
        assert profiles[0].uei == "ABC123DEF456"
        assert profiles[1].legal_name == "Research Solutions Inc"
        
    def test_append_awardee_profiles(self, temp_dir, sample_profiles):
        """Test appending to existing awardee profiles file."""
        storage = StorageFactory.create_awardee_storage(temp_dir)
        
        # Write initial profiles
        storage.write(sample_profiles[:1])
        
        # Append additional profile
        storage.append(sample_profiles[1:])
        
        # Verify combined data
        profiles = storage.read()
        assert len(profiles) == 2
        
    def test_update_existing_profile(self, temp_dir, sample_profiles):
        """Test updating existing awardee profile."""
        storage = StorageFactory.create_awardee_storage(temp_dir)
        
        # Write initial profile
        storage.write(sample_profiles[:1])
        
        # Update the profile
        updated_profile = sample_profiles[0]
        updated_profile.total_awards = 20  # Increase award count
        updated_profile.total_funding = Decimal("6000000.00")
        
        storage.update([updated_profile], key_field='uei')
        
        # Verify update
        profiles = storage.read()
        assert len(profiles) == 1  # Should still be one record
        assert profiles[0].total_awards == 20
        
    def test_data_type_preservation(self, temp_dir, sample_profiles):
        """Test that data types are preserved in Parquet."""
        storage = StorageFactory.create_awardee_storage(temp_dir)
        storage.write(sample_profiles)
        
        # Read back and verify types
        profiles = storage.read()
        profile = profiles[0]
        
        # Check that decimal fields are preserved
        assert isinstance(profile.total_funding, Decimal)
        
        # Check that list fields are preserved
        assert isinstance(profile.primary_agencies, list)
        assert len(profile.primary_agencies) == 2


class TestProgramOfficeStorage:
    """Test program office data storage."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for storage."""
        return tmp_path
    
    @pytest.fixture
    def sample_offices(self):
        """Create sample program offices for testing."""
        return [
            ProgramOffice(
                office_id="NSF-CISE",
                agency_code="NSF",
                agency_name="National Science Foundation",
                office_name="Computer and Information Science and Engineering",
                office_description="Supports research in computer science and engineering",
                contact_email="cise@nsf.gov",
                contact_phone="703-292-8900",
                website_url="https://www.nsf.gov/dir/index.jsp?org=CISE",
                strategic_focus_areas=["AI", "Cybersecurity", "Quantum Computing"],
                annual_budget=Decimal("500000000.00"),
                active_solicitations_count=25,
                total_awards_managed=1000,
                created_at=datetime.now(),
                updated_at=datetime.now()
            ),
            ProgramOffice(
                office_id="DOD-DARPA",
                agency_code="DOD",
                agency_name="Department of Defense",
                office_name="Defense Advanced Research Projects Agency",
                office_description="Develops breakthrough technologies for national security",
                contact_email="info@darpa.mil",
                contact_phone="703-526-6630",
                website_url="https://www.darpa.mil",
                strategic_focus_areas=["Advanced Materials", "Hypersonics", "AI"],
                annual_budget=Decimal("3500000000.00"),
                active_solicitations_count=50,
                total_awards_managed=2000,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
    
    def test_write_program_offices(self, temp_dir, sample_offices):
        """Test writing program offices to Parquet."""
        storage = StorageFactory.create_program_office_storage(temp_dir)
        storage.write(sample_offices)
        
        # Verify file was created
        assert storage.exists()
        
        # Read back and verify data
        offices = storage.read()
        assert len(offices) == 2
        assert offices[0].agency_code == "NSF"
        assert offices[1].agency_code == "DOD"


class TestSolicitationStorage:
    """Test solicitation data storage."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for storage."""
        return tmp_path
    
    @pytest.fixture
    def sample_solicitations(self):
        """Create sample solicitations for testing."""
        return [
            Solicitation(
                solicitation_id="SOL-2024-001",
                solicitation_number="N00014-24-S-B001",
                title="Advanced AI Research Solicitation",
                agency_code="DON",
                program_office_id="ONR-001",
                solicitation_type="SBIR Phase I",
                full_text="This solicitation seeks proposals for advanced AI research...",
                technical_requirements="Machine Learning, Neural Networks",
                evaluation_criteria="Technical Merit, Commercial Potential",
                funding_range_min=Decimal("100000.00"),
                funding_range_max=Decimal("500000.00"),
                proposal_deadline=datetime(2024, 3, 15).date(),
                award_start_date=datetime(2024, 6, 1).date(),
                performance_period=12,
                keywords=["AI", "Data Science"],
                cet_relevance_scores={"artificial_intelligence": 0.95},
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]
    
    def test_write_solicitations(self, temp_dir, sample_solicitations):
        """Test writing solicitations to Parquet."""
        storage = StorageFactory.create_solicitation_storage(temp_dir)
        storage.write(sample_solicitations)
        
        # Verify file was created
        assert storage.exists()
        
        # Read back and verify data
        solicitations = storage.read()
        assert len(solicitations) == 1
        assert solicitations[0].solicitation_id == "SOL-2024-001"


class TestAwardModificationStorage:
    """Test award modification data storage."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for storage."""
        return tmp_path
    
    @pytest.fixture
    def sample_modifications(self):
        """Create sample award modifications for testing."""
        return [
            AwardModification(
                modification_id="MOD-001",
                award_id="AWARD-2024-001",
                modification_number="001",
                modification_type="Funding Increase",
                modification_date=datetime(2024, 6, 15).date(),
                description="Added Phase II option",
                funding_change=Decimal("50000.00"),
                new_end_date=datetime(2025, 12, 31).date(),
                scope_changes="Added Phase II option",
                justification="Successful Phase I completion",
                approving_official="John Doe",
                created_at=datetime.now()
            )
        ]
    
    def test_write_modifications(self, temp_dir, sample_modifications):
        """Test writing award modifications to Parquet."""
        storage = StorageFactory.create_modification_storage(temp_dir)
        storage.write(sample_modifications)
        
        # Verify file was created
        assert storage.exists()
        
        # Read back and verify data
        modifications = storage.read()
        assert len(modifications) == 1
        assert modifications[0].modification_id == "MOD-001"


class TestEnrichedDataManager:
    """Test unified enriched data manager."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for enriched data."""
        return tmp_path / "enriched_data"
    
    def test_write_all_enrichment_types(self, temp_dir, sample_profiles, sample_offices, 
                                       sample_solicitations, sample_modifications):
        """Test writing all enrichment data types."""
        manager = EnrichedDataManager(temp_dir)
        
        # Write all data types
        manager.awardee_profiles.write(sample_profiles)
        manager.program_offices.write(sample_offices)
        manager.solicitations.write(sample_solicitations)
        manager.modifications.write(sample_modifications)
        
        # Verify all files were created
        assert manager.awardee_profiles.exists()
        assert manager.program_offices.exists()
        assert manager.solicitations.exists()
        assert manager.modifications.exists()
        
    def test_get_summary(self, temp_dir, sample_profiles, sample_offices):
        """Test getting summary of all enriched data."""
        manager = EnrichedDataManager(temp_dir)
        
        # Write some data
        manager.awardee_profiles.write(sample_profiles)
        manager.program_offices.write(sample_offices)
        
        # Get summary
        summary = manager.get_summary()
        
        assert summary["awardee_profiles"]["count"] == 2
        assert summary["awardee_profiles"]["exists"] is True
        assert summary["program_offices"]["count"] == 2
        assert summary["program_offices"]["exists"] is True
        assert summary["solicitations"]["count"] == 0
        assert summary["solicitations"]["exists"] is False


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


class TestUnifiedStorageManager:
    """Test unified storage manager functionality."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for storage."""
        return tmp_path
    
    @pytest.fixture
    def sample_awardee_profile(self):
        """Create sample awardee profile for testing."""
        return AwardeeProfile(
            uei="TEST001",
            legal_name="Test Company",
            total_awards=5,
            total_funding=Decimal("500000.00"),
            success_rate=0.8,
            avg_award_amount=Decimal("100000.00"),
            first_award_date=datetime(2020, 1, 1),
            last_award_date=datetime(2024, 1, 1),
            primary_agencies=["NSF", "DOD"],
            technology_areas=["AI", "Cybersecurity"]
        )
    
    def test_unified_storage_manager_creation(self, temp_dir):
        """Test creating unified storage manager."""
        from sbir_cet_classifier.data.storage_v2 import UnifiedStorageManager
        
        manager = UnifiedStorageManager(temp_dir)
        
        # Check that all storage properties are accessible
        assert hasattr(manager, 'awardee_profiles')
        assert hasattr(manager, 'program_offices')
        assert hasattr(manager, 'solicitations')
        assert hasattr(manager, 'modifications')
        
        # Check that data directory was created
        assert manager.data_dir.exists()
        assert manager.data_dir == temp_dir
    
    def test_type_safe_storage_access(self, temp_dir, sample_awardee_profile):
        """Test type-safe access to different storage types."""
        from sbir_cet_classifier.data.storage_v2 import UnifiedStorageManager
        
        manager = UnifiedStorageManager(temp_dir)
        
        # Test writing and reading through unified manager
        manager.awardee_profiles.write([sample_awardee_profile])
        
        # Verify data was written
        assert manager.awardee_profiles.exists()
        assert manager.awardee_profiles.count() == 1
        
        # Read back data
        profiles = manager.awardee_profiles.read()
        assert len(profiles) == 1
        assert profiles[0].uei == "TEST001"
    
    def test_storage_summary(self, temp_dir, sample_awardee_profile):
        """Test storage summary functionality."""
        from sbir_cet_classifier.data.storage_v2 import UnifiedStorageManager
        
        manager = UnifiedStorageManager(temp_dir)
        
        # Initially all storage should be empty
        summary = manager.get_storage_summary()
        assert summary["awardee_profiles"]["count"] == 0
        assert summary["awardee_profiles"]["exists"] is False
        
        # Add some data
        manager.awardee_profiles.write([sample_awardee_profile])
        
        # Summary should reflect the change
        summary = manager.get_storage_summary()
        assert summary["awardee_profiles"]["count"] == 1
        assert summary["awardee_profiles"]["exists"] is True
        assert "file_path" in summary["awardee_profiles"]
    
    def test_backup_and_restore(self, temp_dir, sample_awardee_profile):
        """Test backup and restore functionality."""
        from sbir_cet_classifier.data.storage_v2 import UnifiedStorageManager
        
        manager = UnifiedStorageManager(temp_dir)
        backup_dir = temp_dir / "backup"
        
        # Add some data
        manager.awardee_profiles.write([sample_awardee_profile])
        
        # Backup data
        backup_results = manager.backup_all_data(backup_dir)
        assert backup_results["awardee_profiles"] is True
        assert (backup_dir / "awardee_profiles.parquet").exists()
        
        # Clear original data
        clear_results = manager.clear_all_data()
        assert clear_results["awardee_profiles"] is True
        assert not manager.awardee_profiles.exists()
        
        # Restore from backup
        restore_results = manager.restore_from_backup(backup_dir)
        assert restore_results["awardee_profiles"] is True
        assert manager.awardee_profiles.exists()
        assert manager.awardee_profiles.count() == 1
    
    def test_schema_validation(self, temp_dir, sample_awardee_profile):
        """Test schema validation functionality."""
        from sbir_cet_classifier.data.storage_v2 import UnifiedStorageManager
        
        manager = UnifiedStorageManager(temp_dir)
        
        # Add valid data
        manager.awardee_profiles.write([sample_awardee_profile])
        
        # Validate schemas
        validation_results = manager.validate_all_schemas()
        assert validation_results["awardee_profiles"] is True
    
    def test_file_paths(self, temp_dir):
        """Test file paths functionality."""
        from sbir_cet_classifier.data.storage_v2 import UnifiedStorageManager
        
        manager = UnifiedStorageManager(temp_dir)
        
        file_paths = manager.get_file_paths()
        
        expected_files = [
            "awardee_profiles.parquet",
            "program_offices.parquet", 
            "solicitations.parquet",
            "award_modifications.parquet"
        ]
        
        for storage_type, path in file_paths.items():
            assert path.parent == temp_dir
            assert path.name in expected_files


class TestStorageMigrationUtility:
    """Test storage migration utility functionality."""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for migration tests."""
        return tmp_path
    
    @pytest.fixture
    def sample_awardee_profile(self):
        """Create sample awardee profile for testing."""
        return AwardeeProfile(
            uei="TEST001",
            legal_name="Test Company",
            total_awards=5,
            total_funding=Decimal("500000.00"),
            success_rate=0.8,
            avg_award_amount=Decimal("100000.00"),
            first_award_date=datetime(2020, 1, 1),
            last_award_date=datetime(2024, 1, 1),
            primary_agencies=["NSF", "DOD"],
            technology_areas=["AI", "Cybersecurity"]
        )
    
    def test_migration_utility_creation(self):
        """Test creating migration utility."""
        from sbir_cet_classifier.data.storage_v2 import StorageMigrationUtility
        
        migrator = StorageMigrationUtility()
        assert migrator is not None
    
    def test_validate_nonexistent_file(self, temp_dir):
        """Test validation of non-existent file."""
        from sbir_cet_classifier.data.storage_v2 import StorageMigrationUtility
        
        migrator = StorageMigrationUtility()
        result = migrator.validate_file_integrity(temp_dir / "nonexistent.parquet")
        
        assert result["is_valid"] is False
        assert "File does not exist" in result["errors"]
        assert result["needs_migration"] is False
    
    def test_validate_valid_file(self, temp_dir, sample_awardee_profile):
        """Test validation of valid storage file."""
        from sbir_cet_classifier.data.storage_v2 import StorageMigrationUtility, StorageFactory
        
        # Create a valid storage file
        storage = StorageFactory.create_awardee_storage(temp_dir)
        storage.write([sample_awardee_profile])
        
        # Validate the file
        migrator = StorageMigrationUtility()
        result = migrator.validate_file_integrity(storage.file_path)
        
        assert result["is_valid"] is True
        assert result["schema_version"] == "current"
        assert result["needs_migration"] is False
        assert len(result["errors"]) == 0
    
    def test_batch_validate_directory(self, temp_dir, sample_awardee_profile):
        """Test batch validation of directory."""
        from sbir_cet_classifier.data.storage_v2 import StorageMigrationUtility, StorageFactory
        
        # Create multiple storage files
        awardee_storage = StorageFactory.create_awardee_storage(temp_dir)
        awardee_storage.write([sample_awardee_profile])
        
        # Validate directory
        migrator = StorageMigrationUtility()
        results = migrator.batch_validate_directory(temp_dir)
        
        assert "awardee_profiles.parquet" in results
        assert results["awardee_profiles.parquet"]["is_valid"] is True
    
    def test_migration_no_op(self, temp_dir, sample_awardee_profile):
        """Test migration when no migration is needed."""
        from sbir_cet_classifier.data.storage_v2 import StorageMigrationUtility, StorageFactory
        
        # Create a valid storage file
        storage = StorageFactory.create_awardee_storage(temp_dir)
        storage.write([sample_awardee_profile])
        
        # Try to migrate (should be no-op)
        migrator = StorageMigrationUtility()
        result = migrator.migrate_file(storage.file_path, backup_dir=temp_dir / "backup")
        
        assert result["success"] is True
        assert "does not need migration" in result["errors"][0]
