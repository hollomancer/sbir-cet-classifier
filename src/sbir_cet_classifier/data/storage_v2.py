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


__all__ = [
    "ParquetStorage",
    "ParquetSchemaManager",
    "StorageFactory",
    "EnrichedDataManager",
]
