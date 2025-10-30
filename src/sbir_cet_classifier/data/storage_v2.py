"""Generic Parquet storage layer with type safety.

This module provides a unified, type-safe storage interface for Parquet files.
It replaces the previous pattern of multiple specialized writer/reader classes
with a single generic implementation.

Example:
    >>> from sbir_cet_classifier.data.storage_v2 import ParquetStorage, StorageFactory
    >>>
    >>> # Create type-safe storage
    >>> storage = StorageFactory.create_awardee_storage(data_dir)
    >>>
    >>> # Write data
    >>> storage.write([profile1, profile2])
    >>>
    >>> # Read data
    >>> profiles = storage.read()
    >>>
    >>> # Update specific records
    >>> storage.update([updated_profile], key_field='uei')
"""

from __future__ import annotations

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import TypeVar, Generic, List, Optional, Dict, Any, Type, Callable
from datetime import datetime, date
from decimal import Decimal

from pydantic import BaseModel

# Import enrichment models
from .enrichment.models import (
    AwardeeProfile,
    Solicitation,
    ProgramOffice,
    AwardModification,
)

# Type variable for generic storage
T = TypeVar("T", bound=BaseModel)


class ParquetSchemaManager:
    """Central registry for all Parquet schemas.
    
    This class manages PyArrow schemas for different data types and provides
    a unified interface for schema access and validation.
    """

    # Central schema registry
    _schemas: Dict[str, pa.Schema] = {}

    @classmethod
    def _initialize_schemas(cls) -> None:
        """Initialize all schemas in the registry."""
        if cls._schemas:
            return  # Already initialized

        cls._schemas = {
            'awardee_profiles': pa.schema([
                pa.field("uei", pa.string()),
                pa.field("legal_name", pa.string()),
                pa.field("total_awards", pa.int64()),
                pa.field("total_funding", pa.float64()),
                pa.field("success_rate", pa.float64()),
                pa.field("avg_award_amount", pa.float64()),
                pa.field("first_award_date", pa.timestamp("ns")),
                pa.field("last_award_date", pa.timestamp("ns")),
                pa.field("primary_agencies", pa.list_(pa.string())),
                pa.field("technology_areas", pa.list_(pa.string())),
            ]),
            'program_offices': pa.schema([
                pa.field("office_id", pa.string()),
                pa.field("agency_code", pa.string()),
                pa.field("agency_name", pa.string()),
                pa.field("office_name", pa.string()),
                pa.field("office_description", pa.string()),
                pa.field("contact_email", pa.string()),
                pa.field("contact_phone", pa.string()),
                pa.field("website_url", pa.string()),
                pa.field("strategic_focus_areas", pa.list_(pa.string())),
                pa.field("annual_budget", pa.float64()),
                pa.field("active_solicitations_count", pa.int64()),
                pa.field("total_awards_managed", pa.int64()),
                pa.field("created_at", pa.timestamp("ns")),
                pa.field("updated_at", pa.timestamp("ns")),
            ]),
            'solicitations': pa.schema([
                pa.field("solicitation_id", pa.string()),
                pa.field("solicitation_number", pa.string()),
                pa.field("title", pa.string()),
                pa.field("agency_code", pa.string()),
                pa.field("program_office_id", pa.string()),
                pa.field("solicitation_type", pa.string()),
                pa.field("topic_number", pa.string()),
                pa.field("full_text", pa.string()),
                pa.field("technical_requirements", pa.string()),
                pa.field("evaluation_criteria", pa.string()),
                pa.field("funding_range_min", pa.float64()),
                pa.field("funding_range_max", pa.float64()),
                pa.field("proposal_deadline", pa.date32()),
                pa.field("award_start_date", pa.date32()),
                pa.field("performance_period", pa.int64()),
                pa.field("keywords", pa.list_(pa.string())),
                pa.field("cet_relevance_scores", pa.string()),  # JSON string
                pa.field("created_at", pa.timestamp("ns")),
                pa.field("updated_at", pa.timestamp("ns")),
            ]),
            'award_modifications': pa.schema([
                pa.field("modification_id", pa.string()),
                pa.field("award_id", pa.string()),
                pa.field("modification_number", pa.string()),
                pa.field("modification_type", pa.string()),
                pa.field("modification_date", pa.date32()),
                pa.field("description", pa.string()),
                pa.field("funding_change", pa.float64()),
                pa.field("new_end_date", pa.date32()),
                pa.field("scope_changes", pa.string()),
                pa.field("justification", pa.string()),
                pa.field("approving_official", pa.string()),
                pa.field("created_at", pa.timestamp("ns")),
            ])
        }

    @classmethod
    def get_schema(cls, data_type: str) -> pa.Schema:
        """Get schema by data type name.
        
        Args:
            data_type: Data type name (e.g., 'awardee_profiles', 'solicitations')
            
        Returns:
            PyArrow schema for the data type
            
        Raises:
            KeyError: If data type is not found
        """
        cls._initialize_schemas()
        if data_type not in cls._schemas:
            available = list(cls._schemas.keys())
            raise KeyError(f"Unknown data type '{data_type}'. Available: {available}")
        return cls._schemas[data_type]

    @classmethod
    def validate_data(cls, data_type: str, df: pd.DataFrame) -> None:
        """Validate DataFrame against schema.
        
        Args:
            data_type: Data type name
            df: DataFrame to validate
            
        Raises:
            ValueError: If validation fails
        """
        schema = cls.get_schema(data_type)
        try:
            pa.Table.from_pandas(df, schema=schema)
        except Exception as e:
            raise ValueError(f"Schema validation failed for {data_type}: {e}")

    @classmethod
    def list_data_types(cls) -> List[str]:
        """List all available data types.
        
        Returns:
            List of data type names
        """
        cls._initialize_schemas()
        return list(cls._schemas.keys())

    # Backward compatibility methods
    @staticmethod
    def get_awardee_profile_schema() -> pa.Schema:
        """Get awardee profile Parquet schema."""
        return ParquetSchemaManager.get_schema('awardee_profiles')

    @staticmethod
    def get_program_office_schema() -> pa.Schema:
        """Get program office Parquet schema."""
        return ParquetSchemaManager.get_schema('program_offices')

    @staticmethod
    def get_solicitation_schema() -> pa.Schema:
        """Get solicitation Parquet schema."""
        return ParquetSchemaManager.get_schema('solicitations')

    @staticmethod
    def get_award_modification_schema() -> pa.Schema:
        """Get award modification Parquet schema."""
        return ParquetSchemaManager.get_schema('award_modifications')


class ParquetStorage(Generic[T]):
    """Generic type-safe Parquet storage for Pydantic models.

    This class provides a unified interface for storing and retrieving
    Pydantic models in Parquet format with schema validation.

    Type Parameters:
        T: Pydantic model type (must inherit from BaseModel)

    Example:
        >>> storage = ParquetStorage(
        ...     file_path=Path("data/profiles.parquet"),
        ...     model_class=AwardeeProfile,
        ...     schema=ParquetSchemaManager.get_awardee_profile_schema()
        ... )
        >>> storage.write([profile1, profile2])
        >>> profiles = storage.read()
    """

    def __init__(
        self,
        file_path: Path,
        model_class: Type[T],
        schema: pa.Schema,
        key_field: str = "id",
    ):
        """Initialize storage.

        Args:
            file_path: Path to Parquet file
            model_class: Pydantic model class for type safety
            schema: PyArrow schema for validation
            key_field: Primary key field name for updates (default: "id")
        """
        self.file_path = Path(file_path)
        self.model_class = model_class
        self.schema = schema
        self.key_field = key_field

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, records: List[T]) -> None:
        """Write records to Parquet file (overwrites existing).

        Args:
            records: List of Pydantic model instances

        Example:
            >>> storage.write([profile1, profile2])
        """
        if not records:
            return

        df = self._to_dataframe(records)
        table = pa.Table.from_pandas(df, schema=self.schema)
        pq.write_table(
            table,
            self.file_path,
            compression="snappy",
            row_group_size=50000,
        )

    def append(self, records: List[T]) -> None:
        """Append records to existing file.

        Args:
            records: List of Pydantic model instances to append

        Example:
            >>> storage.append([new_profile])
        """
        if not records:
            return

        new_df = self._to_dataframe(records)

        if self.file_path.exists():
            existing_df = pd.read_parquet(self.file_path, engine="pyarrow")
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        table = pa.Table.from_pandas(combined_df, schema=self.schema)
        pq.write_table(table, self.file_path, compression="snappy")

    def update(self, records: List[T], key_field: str | None = None) -> None:
        """Update existing records by key field.

        Removes existing records with matching keys and adds updated records.

        Args:
            records: List of updated Pydantic model instances
            key_field: Field to use as key (defaults to self.key_field)

        Example:
            >>> storage.update([updated_profile], key_field='uei')
        """
        if not records:
            return

        key = key_field or self.key_field
        new_df = self._to_dataframe(records)

        if self.file_path.exists():
            existing_df = pd.read_parquet(self.file_path, engine="pyarrow")

            # Remove records with matching keys
            update_keys = new_df[key].tolist()
            existing_df = existing_df[~existing_df[key].isin(update_keys)]

            # Combine
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        table = pa.Table.from_pandas(combined_df, schema=self.schema)
        pq.write_table(table, self.file_path, compression="snappy")

    def read(
        self,
        filters: Dict[str, Any] | None = None,
        columns: List[str] | None = None,
    ) -> List[T]:
        """Read records from Parquet file.

        Args:
            filters: Optional dict of column->value filters
            columns: Optional list of columns to read

        Returns:
            List of Pydantic model instances

        Example:
            >>> # Read all
            >>> profiles = storage.read()
            >>>
            >>> # Read with filter
            >>> ca_profiles = storage.read(filters={'state': 'CA'})
            >>>
            >>> # Read specific columns
            >>> names = storage.read(columns=['uei', 'legal_name'])
        """
        if not self.file_path.exists():
            return []

        df = pd.read_parquet(
            self.file_path,
            columns=columns,
            engine="pyarrow",
        )

        # Apply filters
        if filters:
            for col, value in filters.items():
                if col in df.columns:
                    df = df[df[col] == value]

        return self._from_dataframe(df)

    def read_one(self, key_value: Any, key_field: str | None = None) -> T | None:
        """Read a single record by key.

        Args:
            key_value: Value of the key field to search for
            key_field: Field to search (defaults to self.key_field)

        Returns:
            Single model instance or None if not found

        Example:
            >>> profile = storage.read_one('ABC123', key_field='uei')
        """
        key = key_field or self.key_field
        results = self.read(filters={key: key_value})
        return results[0] if results else None

    def exists(self) -> bool:
        """Check if storage file exists.

        Returns:
            True if file exists
        """
        return self.file_path.exists()

    def count(self) -> int:
        """Count total records in storage.

        Returns:
            Number of records
        """
        if not self.file_path.exists():
            return 0

        # Read just metadata for efficiency
        parquet_file = pq.ParquetFile(self.file_path)
        return parquet_file.metadata.num_rows

    def delete(self, key_values: List[Any], key_field: str | None = None) -> int:
        """Delete records by key values.

        Args:
            key_values: List of key values to delete
            key_field: Field to match (defaults to self.key_field)

        Returns:
            Number of records deleted

        Example:
            >>> deleted = storage.delete(['ABC123', 'DEF456'], key_field='uei')
        """
        if not self.file_path.exists():
            return 0

        key = key_field or self.key_field
        df = pd.read_parquet(self.file_path, engine="pyarrow")

        initial_count = len(df)
        df = df[~df[key].isin(key_values)]
        final_count = len(df)

        if final_count > 0:
            table = pa.Table.from_pandas(df, schema=self.schema)
            pq.write_table(table, self.file_path, compression="snappy")
        else:
            # Delete file if no records remain
            self.file_path.unlink()

        return initial_count - final_count

    def _to_dataframe(self, records: List[T]) -> pd.DataFrame:
        """Convert Pydantic models to DataFrame.

        Handles type conversions for Parquet compatibility:
        - Decimal -> float
        - datetime with tz -> naive datetime
        - dict fields -> JSON strings
        """
        if not records:
            return pd.DataFrame()

        data = []
        for record in records:
            # Get dict representation
            if hasattr(record, "model_dump"):
                row = record.model_dump(mode="python")
            elif hasattr(record, "dict"):
                row = record.dict()
            else:
                row = dict(record)

            # Type conversions
            for key, value in row.items():
                if isinstance(value, Decimal):
                    row[key] = float(value)
                elif isinstance(value, datetime):
                    # Remove timezone for Parquet
                    row[key] = value.replace(tzinfo=None)
                elif isinstance(value, dict):
                    # Convert dicts to JSON strings
                    import json

                    row[key] = json.dumps(value)

            data.append(row)

        return pd.DataFrame(data)

    def _from_dataframe(self, df: pd.DataFrame) -> List[T]:
        """Convert DataFrame to Pydantic models.

        Handles reverse type conversions:
        - JSON strings -> dicts
        """
        if df.empty:
            return []

        records = []
        for _, row in df.iterrows():
            # Convert row to dict
            row_dict = row.to_dict()

            # Handle JSON string fields
            for key, value in row_dict.items():
                if isinstance(value, str) and value.startswith("{"):
                    try:
                        import json

                        row_dict[key] = json.loads(value)
                    except (json.JSONDecodeError, ValueError):
                        pass  # Keep as string

            # Create model instance
            try:
                records.append(self.model_class(**row_dict))
            except Exception as e:
                # Log warning but continue
                import logging

                logging.warning(f"Failed to create {self.model_class.__name__} from row: {e}")

        return records


class StorageFactory:
    """Factory for creating typed storage instances.

    Provides convenient methods for creating storage instances
    with correct schemas and key fields.

    Example:
        >>> data_dir = Path("data/processed")
        >>> storage = StorageFactory.create_awardee_storage(data_dir)
    """

    @staticmethod
    def create_awardee_storage(data_dir: Path) -> ParquetStorage[AwardeeProfile]:
        """Create storage for awardee profiles.

        Args:
            data_dir: Directory for storage files

        Returns:
            Typed storage instance
        """
        return ParquetStorage(
            file_path=data_dir / "awardee_profiles.parquet",
            model_class=AwardeeProfile,
            schema=ParquetSchemaManager.get_awardee_profile_schema(),
            key_field="uei",
        )

    @staticmethod
    def create_program_office_storage(data_dir: Path) -> ParquetStorage[ProgramOffice]:
        """Create storage for program offices.

        Args:
            data_dir: Directory for storage files

        Returns:
            Typed storage instance
        """
        return ParquetStorage(
            file_path=data_dir / "program_offices.parquet",
            model_class=ProgramOffice,
            schema=ParquetSchemaManager.get_program_office_schema(),
            key_field="office_id",
        )

    @staticmethod
    def create_solicitation_storage(data_dir: Path) -> ParquetStorage[Solicitation]:
        """Create storage for solicitations.

        Args:
            data_dir: Directory for storage files

        Returns:
            Typed storage instance
        """
        return ParquetStorage(
            file_path=data_dir / "solicitations.parquet",
            model_class=Solicitation,
            schema=ParquetSchemaManager.get_solicitation_schema(),
            key_field="solicitation_id",
        )

    @staticmethod
    def create_modification_storage(data_dir: Path) -> ParquetStorage[AwardModification]:
        """Create storage for award modifications.

        Args:
            data_dir: Directory for storage files

        Returns:
            Typed storage instance
        """
        return ParquetStorage(
            file_path=data_dir / "award_modifications.parquet",
            model_class=AwardModification,
            schema=ParquetSchemaManager.get_award_modification_schema(),
            key_field="modification_id",
        )


class EnrichedDataManager:
    """Unified manager for all enriched data storage.

    Provides a single interface for managing all enriched data types.
    Replaces the previous EnrichedDataWriter/Reader pattern.

    Example:
        >>> manager = EnrichedDataManager(data_dir)
        >>>
        >>> # Write data
        >>> manager.awardee_profiles.write([profile1, profile2])
        >>>
        >>> # Read data
        >>> profiles = manager.awardee_profiles.read()
        >>>
        >>> # Get summary
        >>> summary = manager.get_summary()
    """

    def __init__(self, data_dir: Path):
        """Initialize manager with storage directory.

        Args:
            data_dir: Directory for all enriched data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Create storage instances
        self.awardee_profiles = StorageFactory.create_awardee_storage(self.data_dir)
        self.program_offices = StorageFactory.create_program_office_storage(self.data_dir)
        self.solicitations = StorageFactory.create_solicitation_storage(self.data_dir)
        self.modifications = StorageFactory.create_modification_storage(self.data_dir)

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all enriched data.

        Returns:
            Dictionary with counts and metadata for each data type
        """
        return {
            "awardee_profiles": {
                "count": self.awardee_profiles.count(),
                "exists": self.awardee_profiles.exists(),
            },
            "program_offices": {
                "count": self.program_offices.count(),
                "exists": self.program_offices.exists(),
            },
            "solicitations": {
                "count": self.solicitations.count(),
                "exists": self.solicitations.exists(),
            },
            "award_modifications": {
                "count": self.modifications.count(),
                "exists": self.modifications.exists(),
            },
        }

    def get_file_paths(self) -> Dict[str, Path]:
        """Get file paths for all storage files.

        Returns:
            Dictionary mapping data type to file path
        """
        return {
            "awardee_profiles": self.awardee_profiles.file_path,
            "program_offices": self.program_offices.file_path,
            "solicitations": self.solicitations.file_path,
            "award_modifications": self.modifications.file_path,
        }


class StorageMigrationUtility:
    """Utility for migrating storage files between schema versions.
    
    Provides functions for validating data integrity, migrating legacy formats,
    and rollback capabilities for failed migrations.
    
    Example:
        >>> migrator = StorageMigrationUtility()
        >>> result = migrator.validate_file_integrity(file_path)
        >>> if result.needs_migration:
        ...     migrator.migrate_file(file_path, backup_dir)
    """
    
    def __init__(self):
        """Initialize migration utility."""
        pass
    
    def validate_file_integrity(self, file_path: Path) -> Dict[str, Any]:
        """Validate integrity of a storage file.
        
        Args:
            file_path: Path to the storage file to validate
            
        Returns:
            Dictionary with validation results including:
            - is_valid: Boolean indicating if file is valid
            - schema_version: Detected schema version
            - needs_migration: Boolean indicating if migration is needed
            - errors: List of validation errors if any
        """
        result = {
            "is_valid": False,
            "schema_version": "unknown",
            "needs_migration": False,
            "errors": [],
            "file_path": str(file_path)
        }
        
        try:
            if not file_path.exists():
                result["errors"].append("File does not exist")
                return result
            
            # Try to read the file with PyArrow
            import pandas as pd
            df = pd.read_parquet(file_path, engine="pyarrow")
            
            # Detect data type based on columns
            columns = set(df.columns)
            data_type = self._detect_data_type(columns)
            
            if data_type:
                # Validate against current schema
                try:
                    ParquetSchemaManager.validate_data(data_type, df)
                    result["is_valid"] = True
                    result["schema_version"] = "current"
                except Exception as e:
                    result["errors"].append(f"Schema validation failed: {str(e)}")
                    result["needs_migration"] = True
            else:
                result["errors"].append("Could not detect data type from columns")
            
        except Exception as e:
            result["errors"].append(f"Failed to read file: {str(e)}")
        
        return result
    
    def _detect_data_type(self, columns: set) -> Optional[str]:
        """Detect data type based on column names.
        
        Args:
            columns: Set of column names
            
        Returns:
            Data type name or None if not detected
        """
        # Define column signatures for each data type
        signatures = {
            "awardee_profiles": {"uei", "legal_name", "total_awards"},
            "program_offices": {"office_id", "agency_code", "office_name"},
            "solicitations": {"solicitation_id", "title", "agency_code"},
            "award_modifications": {"modification_id", "award_id", "modification_type"}
        }
        
        for data_type, required_cols in signatures.items():
            if required_cols.issubset(columns):
                return data_type
        
        return None
    
    def migrate_file(self, file_path: Path, backup_dir: Optional[Path] = None) -> Dict[str, Any]:
        """Migrate a storage file to the current schema version.
        
        Args:
            file_path: Path to the file to migrate
            backup_dir: Optional directory to store backup before migration
            
        Returns:
            Dictionary with migration results including:
            - success: Boolean indicating if migration succeeded
            - backup_path: Path to backup file if created
            - errors: List of errors if any
        """
        result = {
            "success": False,
            "backup_path": None,
            "errors": [],
            "file_path": str(file_path)
        }
        
        try:
            # Validate file first
            validation = self.validate_file_integrity(file_path)
            if not validation["needs_migration"]:
                result["success"] = True
                result["errors"].append("File does not need migration")
                return result
            
            # Create backup if requested
            if backup_dir:
                backup_dir = Path(backup_dir)
                backup_dir.mkdir(parents=True, exist_ok=True)
                backup_path = backup_dir / f"{file_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.parquet"
                
                import shutil
                shutil.copy2(file_path, backup_path)
                result["backup_path"] = str(backup_path)
            
            # For now, migration is a no-op since we haven't changed schemas
            # In the future, this would contain actual migration logic
            result["success"] = True
            
        except Exception as e:
            result["errors"].append(f"Migration failed: {str(e)}")
        
        return result
    
    def rollback_migration(self, file_path: Path, backup_path: Path) -> Dict[str, Any]:
        """Rollback a failed migration using backup file.
        
        Args:
            file_path: Path to the current file
            backup_path: Path to the backup file
            
        Returns:
            Dictionary with rollback results
        """
        result = {
            "success": False,
            "errors": []
        }
        
        try:
            if not Path(backup_path).exists():
                result["errors"].append("Backup file does not exist")
                return result
            
            import shutil
            shutil.copy2(backup_path, file_path)
            result["success"] = True
            
        except Exception as e:
            result["errors"].append(f"Rollback failed: {str(e)}")
        
        return result
    
    def batch_validate_directory(self, data_dir: Path) -> Dict[str, Dict[str, Any]]:
        """Validate all storage files in a directory.
        
        Args:
            data_dir: Directory containing storage files
            
        Returns:
            Dictionary mapping file names to validation results
        """
        results = {}
        data_dir = Path(data_dir)
        
        if not data_dir.exists():
            return results
        
        # Look for parquet files
        for file_path in data_dir.glob("*.parquet"):
            results[file_path.name] = self.validate_file_integrity(file_path)
        
        return results


class UnifiedStorageManager:
    """Unified storage manager that provides type-safe access to all storage types.
    
    This class wraps all storage types and provides a single interface for
    managing different data types with type safety and convenience methods.
    
    Example:
        >>> manager = UnifiedStorageManager(data_dir)
        >>>
        >>> # Type-safe access to specific storage
        >>> profiles = manager.awardee_profiles.read()
        >>> manager.solicitations.write([solicitation])
        >>>
        >>> # Convenience methods
        >>> summary = manager.get_storage_summary()
        >>> manager.backup_all_data(backup_dir)
    """
    
    def __init__(self, data_dir: Path):
        """Initialize unified storage manager.
        
        Args:
            data_dir: Directory for all storage files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Create type-safe storage instances
        self._awardee_profiles = StorageFactory.create_awardee_storage(self.data_dir)
        self._program_offices = StorageFactory.create_program_office_storage(self.data_dir)
        self._solicitations = StorageFactory.create_solicitation_storage(self.data_dir)
        self._modifications = StorageFactory.create_modification_storage(self.data_dir)
    
    @property
    def awardee_profiles(self) -> ParquetStorage[AwardeeProfile]:
        """Get type-safe awardee profiles storage."""
        return self._awardee_profiles
    
    @property
    def program_offices(self) -> ParquetStorage[ProgramOffice]:
        """Get type-safe program offices storage."""
        return self._program_offices
    
    @property
    def solicitations(self) -> ParquetStorage[Solicitation]:
        """Get type-safe solicitations storage."""
        return self._solicitations
    
    @property
    def modifications(self) -> ParquetStorage[AwardModification]:
        """Get type-safe award modifications storage."""
        return self._modifications
    
    def get_storage_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get summary of all storage instances.
        
        Returns:
            Dictionary with counts and metadata for each storage type
        """
        return {
            "awardee_profiles": {
                "count": self._awardee_profiles.count(),
                "exists": self._awardee_profiles.exists(),
                "file_path": str(self._awardee_profiles.file_path),
            },
            "program_offices": {
                "count": self._program_offices.count(),
                "exists": self._program_offices.exists(),
                "file_path": str(self._program_offices.file_path),
            },
            "solicitations": {
                "count": self._solicitations.count(),
                "exists": self._solicitations.exists(),
                "file_path": str(self._solicitations.file_path),
            },
            "award_modifications": {
                "count": self._modifications.count(),
                "exists": self._modifications.exists(),
                "file_path": str(self._modifications.file_path),
            },
        }
    
    def backup_all_data(self, backup_dir: Path) -> Dict[str, bool]:
        """Backup all storage files to a backup directory.
        
        Args:
            backup_dir: Directory to store backup files
            
        Returns:
            Dictionary mapping storage type to backup success status
        """
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        storage_map = {
            "awardee_profiles": self._awardee_profiles,
            "program_offices": self._program_offices,
            "solicitations": self._solicitations,
            "award_modifications": self._modifications,
        }
        
        for storage_name, storage in storage_map.items():
            try:
                if storage.exists():
                    import shutil
                    backup_path = backup_dir / storage.file_path.name
                    shutil.copy2(storage.file_path, backup_path)
                    results[storage_name] = True
                else:
                    results[storage_name] = False  # No file to backup
            except Exception:
                results[storage_name] = False
        
        return results
    
    def restore_from_backup(self, backup_dir: Path) -> Dict[str, bool]:
        """Restore all storage files from a backup directory.
        
        Args:
            backup_dir: Directory containing backup files
            
        Returns:
            Dictionary mapping storage type to restore success status
        """
        backup_dir = Path(backup_dir)
        if not backup_dir.exists():
            return {name: False for name in ["awardee_profiles", "program_offices", "solicitations", "award_modifications"]}
        
        results = {}
        storage_map = {
            "awardee_profiles": self._awardee_profiles,
            "program_offices": self._program_offices,
            "solicitations": self._solicitations,
            "award_modifications": self._modifications,
        }
        
        for storage_name, storage in storage_map.items():
            try:
                backup_path = backup_dir / storage.file_path.name
                if backup_path.exists():
                    import shutil
                    shutil.copy2(backup_path, storage.file_path)
                    results[storage_name] = True
                else:
                    results[storage_name] = False  # No backup file found
            except Exception:
                results[storage_name] = False
        
        return results
    
    def clear_all_data(self) -> Dict[str, bool]:
        """Clear all storage files.
        
        Returns:
            Dictionary mapping storage type to clear success status
        """
        results = {}
        storage_map = {
            "awardee_profiles": self._awardee_profiles,
            "program_offices": self._program_offices,
            "solicitations": self._solicitations,
            "award_modifications": self._modifications,
        }
        
        for storage_name, storage in storage_map.items():
            try:
                if storage.exists():
                    storage.file_path.unlink()
                results[storage_name] = True
            except Exception:
                results[storage_name] = False
        
        return results
    
    def validate_all_schemas(self) -> Dict[str, bool]:
        """Validate all existing storage files against their schemas.
        
        Returns:
            Dictionary mapping storage type to validation success status
        """
        results = {}
        
        # Map storage types to their schema names
        schema_map = {
            "awardee_profiles": ("awardee_profiles", self._awardee_profiles),
            "program_offices": ("program_offices", self._program_offices),
            "solicitations": ("solicitations", self._solicitations),
            "award_modifications": ("award_modifications", self._modifications),
        }
        
        for storage_name, (schema_name, storage) in schema_map.items():
            try:
                if storage.exists():
                    # Read the file and validate against schema
                    import pandas as pd
                    df = pd.read_parquet(storage.file_path, engine="pyarrow")
                    ParquetSchemaManager.validate_data(schema_name, df)
                    results[storage_name] = True
                else:
                    results[storage_name] = True  # No file to validate
            except Exception:
                results[storage_name] = False
        
        return results
    
    def get_file_paths(self) -> Dict[str, Path]:
        """Get file paths for all storage files.
        
        Returns:
            Dictionary mapping storage type to file path
        """
        return {
            "awardee_profiles": self._awardee_profiles.file_path,
            "program_offices": self._program_offices.file_path,
            "solicitations": self._solicitations.file_path,
            "award_modifications": self._modifications.file_path,
        }


__all__ = [
    "ParquetStorage",
    "ParquetSchemaManager",
    "StorageFactory",
    "EnrichedDataManager",
    "UnifiedStorageManager",
    "StorageMigrationUtility",
]
