"""Extended Parquet schema management and enriched data storage.

DEPRECATED: This module is maintained for backward compatibility only.
New code should use storage_v2.py which provides a unified generic storage interface.

Migration guide:
    Old: writer = AwardeeProfileWriter(path)
         writer.write(profiles)

    New: storage = StorageFactory.create_awardee_storage(data_dir)
         storage.write(profiles)
"""

import warnings
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from decimal import Decimal

from .enrichment.models import (
    AwardeeProfile,
    Solicitation,
    ProgramOffice,
    AwardModification,
)

# Import new storage classes for backward compatibility
from .storage_v2 import (
    ParquetStorage,
    ParquetSchemaManager as SchemaManagerV2,
    StorageFactory,
    EnrichedDataManager,
)

# Issue deprecation warning
warnings.warn(
    "storage.py is deprecated. Use storage_v2.ParquetStorage instead. "
    "See storage_v2.py for migration guide.",
    DeprecationWarning,
    stacklevel=2,
)


class ParquetSchemaManager:
    """Manages Parquet schemas for enriched data storage."""

    @staticmethod
    def get_existing_award_schema() -> pa.Schema:
        """Get existing award schema for compatibility checking."""
        return pa.schema(
            [
                pa.field("award_id", pa.string()),
                pa.field("award_number", pa.string()),
                pa.field("title", pa.string()),
                pa.field("abstract", pa.string()),
                pa.field("award_amount", pa.float64()),  # Use float64 instead of decimal128
                pa.field("start_date", pa.timestamp("ns")),
                pa.field("end_date", pa.timestamp("ns")),
                pa.field("agency", pa.string()),
                pa.field("program", pa.string()),
                pa.field("phase", pa.string()),
                pa.field("awardee_name", pa.string()),
                pa.field("awardee_city", pa.string()),
                pa.field("awardee_state", pa.string()),
            ]
        )

    @staticmethod
    def get_awardee_profile_schema() -> pa.Schema:
        """Get awardee profile Parquet schema."""
        return pa.schema(
            [
                pa.field("uei", pa.string()),
                pa.field("legal_name", pa.string()),
                pa.field("total_awards", pa.int64()),
                pa.field("total_funding", pa.float64()),  # Use float64 instead of decimal128
                pa.field("success_rate", pa.float64()),
                pa.field("avg_award_amount", pa.float64()),  # Use float64 instead of decimal128
                pa.field("first_award_date", pa.timestamp("ns")),
                pa.field("last_award_date", pa.timestamp("ns")),
                pa.field("primary_agencies", pa.list_(pa.string())),
                pa.field("technology_areas", pa.list_(pa.string())),
            ]
        )

    @staticmethod
    def get_program_office_schema() -> pa.Schema:
        """Get program office Parquet schema."""
        return pa.schema(
            [
                pa.field("agency", pa.string()),
                pa.field("office_name", pa.string()),
                pa.field("office_code", pa.string()),
                pa.field("contact_email", pa.string()),
                pa.field("contact_phone", pa.string()),
                pa.field("strategic_focus", pa.list_(pa.string())),
                pa.field("annual_budget", pa.float64()),  # Use float64 instead of decimal128
                pa.field("active_programs", pa.int64()),
            ]
        )

    @staticmethod
    def get_solicitation_schema() -> pa.Schema:
        """Get solicitation Parquet schema."""
        return pa.schema(
            [
                pa.field("solicitation_id", pa.string()),
                pa.field("title", pa.string()),
                pa.field("full_text", pa.string()),
                pa.field("technical_requirements", pa.list_(pa.string())),
                pa.field("evaluation_criteria", pa.list_(pa.string())),
                pa.field("topic_areas", pa.list_(pa.string())),
                pa.field("funding_range_min", pa.float64()),  # Use float64 instead of decimal128
                pa.field("funding_range_max", pa.float64()),  # Use float64 instead of decimal128
                pa.field("submission_deadline", pa.timestamp("ns")),
            ]
        )

    @staticmethod
    def get_award_modification_schema() -> pa.Schema:
        """Get award modification Parquet schema."""
        return pa.schema(
            [
                pa.field("modification_id", pa.string()),
                pa.field("award_id", pa.string()),
                pa.field("modification_type", pa.string()),
                pa.field("modification_date", pa.timestamp("ns")),
                pa.field("funding_change", pa.float64()),  # Use float64 instead of decimal128
                pa.field("scope_change", pa.string()),
                pa.field("new_end_date", pa.timestamp("ns")),
                pa.field("justification", pa.string()),
            ]
        )


class BaseParquetWriter:
    """Base class for Parquet data writers."""

    def __init__(self, file_path: Path):
        """Initialize writer with file path.

        Args:
            file_path: Path to Parquet file
        """
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _convert_to_dataframe(self, data: List[Any]) -> pd.DataFrame:
        """Convert list of Pydantic models to DataFrame.

        Args:
            data: List of Pydantic model instances

        Returns:
            Pandas DataFrame
        """
        if not data:
            return pd.DataFrame()

        # Convert Pydantic models to dictionaries
        records = []
        for item in data:
            if hasattr(item, "dict"):
                record = item.dict()
            else:
                record = item

            # Convert Decimal to float for Parquet compatibility
            for key, value in record.items():
                if isinstance(value, Decimal):
                    record[key] = float(value)
                elif isinstance(value, datetime):
                    # Ensure timezone-naive datetime for Parquet
                    record[key] = value.replace(tzinfo=None)

            records.append(record)

        return pd.DataFrame(records)

    def write(self, data: List[Any], schema: Optional[pa.Schema] = None) -> None:
        """Write data to Parquet file.

        Args:
            data: List of data objects to write
            schema: Optional PyArrow schema for validation
        """
        if not data:
            return

        df = self._convert_to_dataframe(data)

        if schema:
            # Convert DataFrame to PyArrow table with schema validation
            table = pa.Table.from_pandas(df, schema=schema)
            pq.write_table(table, self.file_path)
        else:
            # Write without schema validation
            df.to_parquet(self.file_path, index=False)

    def append(self, data: List[Any], schema: Optional[pa.Schema] = None) -> None:
        """Append data to existing Parquet file.

        Args:
            data: List of data objects to append
            schema: Optional PyArrow schema for validation
        """
        if not data:
            return

        new_df = self._convert_to_dataframe(data)

        if self.file_path.exists():
            # Read existing data
            existing_df = pd.read_parquet(self.file_path)
            # Combine with new data
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        if schema:
            # Convert to PyArrow table with schema validation
            table = pa.Table.from_pandas(combined_df, schema=schema)
            pq.write_table(table, self.file_path)
        else:
            combined_df.to_parquet(self.file_path, index=False)

    def update(self, data: List[Any], key_field: str, schema: Optional[pa.Schema] = None) -> None:
        """Update existing records in Parquet file.

        Args:
            data: List of data objects to update
            key_field: Field name to use as primary key for updates
            schema: Optional PyArrow schema for validation
        """
        if not data:
            return

        new_df = self._convert_to_dataframe(data)

        if self.file_path.exists():
            # Read existing data
            existing_df = pd.read_parquet(self.file_path)

            # Remove existing records that match the key field
            update_keys = new_df[key_field].tolist()
            existing_df = existing_df[~existing_df[key_field].isin(update_keys)]

            # Combine with updated data
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        if schema:
            # Convert to PyArrow table with schema validation
            table = pa.Table.from_pandas(combined_df, schema=schema)
            pq.write_table(table, self.file_path)
        else:
            combined_df.to_parquet(self.file_path, index=False)


class AwardeeProfileWriter(BaseParquetWriter):
    """Writer for awardee profile data."""

    def __init__(self, file_path: Path):
        """Initialize awardee profile writer."""
        super().__init__(file_path)
        self.schema = ParquetSchemaManager.get_awardee_profile_schema()

    def write(self, profiles: List[AwardeeProfile]) -> None:
        """Write awardee profiles to Parquet."""
        super().write(profiles, self.schema)

    def append(self, profiles: List[AwardeeProfile]) -> None:
        """Append awardee profiles to existing file."""
        super().append(profiles, self.schema)

    def update(self, profiles: List[AwardeeProfile]) -> None:
        """Update existing awardee profiles."""
        super().update(profiles, "uei", self.schema)


class ProgramOfficeWriter(BaseParquetWriter):
    """Writer for program office data."""

    def __init__(self, file_path: Path):
        """Initialize program office writer."""
        super().__init__(file_path)
        self.schema = ParquetSchemaManager.get_program_office_schema()

    def write(self, offices: List[ProgramOffice]) -> None:
        """Write program offices to Parquet."""
        super().write(offices, self.schema)

    def append(self, offices: List[ProgramOffice]) -> None:
        """Append program offices to existing file."""
        super().append(offices, self.schema)

    def update(self, offices: List[ProgramOffice]) -> None:
        """Update existing program offices."""
        super().update(offices, "office_code", self.schema)


class SolicitationWriter(BaseParquetWriter):
    """Writer for solicitation data."""

    def __init__(self, file_path: Path):
        """Initialize solicitation writer."""
        super().__init__(file_path)
        self.schema = ParquetSchemaManager.get_solicitation_schema()

    def write(self, solicitations: List[Solicitation]) -> None:
        """Write solicitations to Parquet."""
        super().write(solicitations, self.schema)

    def append(self, solicitations: List[Solicitation]) -> None:
        """Append solicitations to existing file."""
        super().append(solicitations, self.schema)

    def update(self, solicitations: List[Solicitation]) -> None:
        """Update existing solicitations."""
        super().update(solicitations, "solicitation_id", self.schema)


class AwardModificationWriter(BaseParquetWriter):
    """Writer for award modification data."""

    def __init__(self, file_path: Path):
        """Initialize award modification writer."""
        super().__init__(file_path)
        self.schema = ParquetSchemaManager.get_award_modification_schema()

    def write(self, modifications: List[AwardModification]) -> None:
        """Write award modifications to Parquet."""
        super().write(modifications, self.schema)

    def append(self, modifications: List[AwardModification]) -> None:
        """Append award modifications to existing file."""
        super().append(modifications, self.schema)

    def update(self, modifications: List[AwardModification]) -> None:
        """Update existing award modifications."""
        super().update(modifications, "modification_id", self.schema)


class EnrichedDataWriter:
    """Unified writer for all enriched data types."""

    def __init__(self, data_dir: Path):
        """Initialize enriched data writer.

        Args:
            data_dir: Directory for enriched data files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize individual writers
        self.awardee_writer = AwardeeProfileWriter(self.data_dir / "awardee_profiles.parquet")
        self.program_writer = ProgramOfficeWriter(self.data_dir / "program_offices.parquet")
        self.solicitation_writer = SolicitationWriter(self.data_dir / "solicitations.parquet")
        self.modification_writer = AwardModificationWriter(
            self.data_dir / "award_modifications.parquet"
        )

    def write_awardee_profiles(self, profiles: List[AwardeeProfile]) -> None:
        """Write awardee profiles."""
        self.awardee_writer.write(profiles)

    def write_program_offices(self, offices: List[ProgramOffice]) -> None:
        """Write program offices."""
        self.program_writer.write(offices)

    def write_solicitations(self, solicitations: List[Solicitation]) -> None:
        """Write solicitations."""
        self.solicitation_writer.write(solicitations)

    def write_award_modifications(self, modifications: List[AwardModification]) -> None:
        """Write award modifications."""
        self.modification_writer.write(modifications)

    def append_awardee_profiles(self, profiles: List[AwardeeProfile]) -> None:
        """Append awardee profiles."""
        self.awardee_writer.append(profiles)

    def append_program_offices(self, offices: List[ProgramOffice]) -> None:
        """Append program offices."""
        self.program_writer.append(offices)

    def append_solicitations(self, solicitations: List[Solicitation]) -> None:
        """Append solicitations."""
        self.solicitation_writer.append(solicitations)

    def append_award_modifications(self, modifications: List[AwardModification]) -> None:
        """Append award modifications."""
        self.modification_writer.append(modifications)

    def update_awardee_profiles(self, profiles: List[AwardeeProfile]) -> None:
        """Update awardee profiles."""
        self.awardee_writer.update(profiles)

    def update_program_offices(self, offices: List[ProgramOffice]) -> None:
        """Update program offices."""
        self.program_writer.update(offices)

    def update_solicitations(self, solicitations: List[Solicitation]) -> None:
        """Update solicitations."""
        self.solicitation_writer.update(solicitations)

    def update_award_modifications(self, modifications: List[AwardModification]) -> None:
        """Update award modifications."""
        self.modification_writer.update(modifications)

    def get_file_paths(self) -> Dict[str, Path]:
        """Get paths to all enriched data files.

        Returns:
            Dictionary mapping data type to file path
        """
        return {
            "awardee_profiles": self.awardee_writer.file_path,
            "program_offices": self.program_writer.file_path,
            "solicitations": self.solicitation_writer.file_path,
            "award_modifications": self.modification_writer.file_path,
        }

    def get_file_sizes(self) -> Dict[str, int]:
        """Get file sizes for all enriched data files.

        Returns:
            Dictionary mapping data type to file size in bytes
        """
        sizes = {}
        for data_type, file_path in self.get_file_paths().items():
            if file_path.exists():
                sizes[data_type] = file_path.stat().st_size
            else:
                sizes[data_type] = 0
        return sizes

    def get_record_counts(self) -> Dict[str, int]:
        """Get record counts for all enriched data files.

        Returns:
            Dictionary mapping data type to record count
        """
        counts = {}
        for data_type, file_path in self.get_file_paths().items():
            if file_path.exists():
                try:
                    df = pd.read_parquet(file_path)
                    counts[data_type] = len(df)
                except Exception:
                    counts[data_type] = 0
            else:
                counts[data_type] = 0
        return counts


class EnrichedDataReader:
    """Reader for enriched data files."""

    def __init__(self, data_dir: Path):
        """Initialize enriched data reader.

        Args:
            data_dir: Directory containing enriched data files
        """
        self.data_dir = Path(data_dir)

    def read_awardee_profiles(self, filters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Read awardee profiles with optional filtering.

        Args:
            filters: Optional filters to apply

        Returns:
            DataFrame with awardee profiles
        """
        file_path = self.data_dir / "awardee_profiles.parquet"
        if not file_path.exists():
            return pd.DataFrame()

        df = pd.read_parquet(file_path)

        if filters:
            for column, value in filters.items():
                if column in df.columns:
                    if isinstance(value, list):
                        df = df[df[column].isin(value)]
                    else:
                        df = df[df[column] == value]

        return df

    def read_program_offices(self, filters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Read program offices with optional filtering."""
        file_path = self.data_dir / "program_offices.parquet"
        if not file_path.exists():
            return pd.DataFrame()

        df = pd.read_parquet(file_path)

        if filters:
            for column, value in filters.items():
                if column in df.columns:
                    if isinstance(value, list):
                        df = df[df[column].isin(value)]
                    else:
                        df = df[df[column] == value]

        return df

    def read_solicitations(self, filters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Read solicitations with optional filtering."""
        file_path = self.data_dir / "solicitations.parquet"
        if not file_path.exists():
            return pd.DataFrame()

        df = pd.read_parquet(file_path)

        if filters:
            for column, value in filters.items():
                if column in df.columns:
                    if isinstance(value, list):
                        df = df[df[column].isin(value)]
                    else:
                        df = df[df[column] == value]

        return df

    def read_award_modifications(self, filters: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Read award modifications with optional filtering."""
        file_path = self.data_dir / "award_modifications.parquet"
        if not file_path.exists():
            return pd.DataFrame()

        df = pd.read_parquet(file_path)

        if filters:
            for column, value in filters.items():
                if column in df.columns:
                    if isinstance(value, list):
                        df = df[df[column].isin(value)]
                    else:
                        df = df[df[column] == value]

        return df

    def get_enrichment_summary(self, award_id: str) -> Dict[str, Any]:
        """Get enrichment summary for a specific award.

        Args:
            award_id: Award identifier

        Returns:
            Dictionary with enrichment summary
        """
        summary = {
            "award_id": award_id,
            "awardee_profile": None,
            "program_office": None,
            "solicitation": None,
            "modifications": [],
        }

        # Check awardee profiles (need to match by UEI or other identifier)
        awardee_df = self.read_awardee_profiles()
        if not awardee_df.empty:
            # This would require additional logic to match award to awardee
            pass

        # Check program offices (need to match by agency/program)
        program_df = self.read_program_offices()
        if not program_df.empty:
            # This would require additional logic to match award to program office
            pass

        # Check solicitations (need to match by solicitation ID)
        solicitation_df = self.read_solicitations()
        if not solicitation_df.empty:
            # This would require additional logic to match award to solicitation
            pass

        # Check modifications (direct match by award_id)
        modifications_df = self.read_award_modifications({"award_id": award_id})
        if not modifications_df.empty:
            summary["modifications"] = modifications_df.to_dict("records")

        return summary


class SolicitationStorage:
    """Storage handler for solicitation data with simplified interface."""

    def __init__(self, file_path: Path):
        """Initialize with file path."""
        self.file_path = Path(file_path)
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # Let the error be handled when actually trying to save/load
            pass

    def get_parquet_schema(self) -> pa.Schema:
        """Get PyArrow schema for solicitation data."""
        return pa.schema(
            [
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
                pa.field("performance_period", pa.int32()),
                pa.field("keywords", pa.string()),  # JSON string
                pa.field("cet_relevance_scores", pa.string()),  # JSON string
                pa.field("created_at", pa.timestamp("us")),
                pa.field("updated_at", pa.timestamp("us")),
            ]
        )

    def save_solicitations(self, solicitations: List[Solicitation]) -> None:
        """Save solicitations to Parquet file."""
        if not solicitations:
            return

        import json

        # Convert to DataFrame
        data = []
        for sol in solicitations:
            data.append(
                {
                    "solicitation_id": sol.solicitation_id,
                    "solicitation_number": sol.solicitation_number,
                    "title": sol.title,
                    "agency_code": sol.agency_code,
                    "program_office_id": sol.program_office_id,
                    "solicitation_type": sol.solicitation_type,
                    "topic_number": sol.topic_number,
                    "full_text": sol.full_text,
                    "technical_requirements": sol.technical_requirements,
                    "evaluation_criteria": sol.evaluation_criteria,
                    "funding_range_min": float(sol.funding_range_min),
                    "funding_range_max": float(sol.funding_range_max),
                    "proposal_deadline": sol.proposal_deadline,
                    "award_start_date": sol.award_start_date,
                    "performance_period": sol.performance_period,
                    "keywords": json.dumps(sol.keywords),
                    "cet_relevance_scores": json.dumps(sol.cet_relevance_scores),
                    "created_at": sol.created_at,
                    "updated_at": sol.updated_at,
                }
            )

        df = pd.DataFrame(data)

        # Write to Parquet
        table = pa.Table.from_pandas(df, schema=self.get_parquet_schema())
        pq.write_table(table, self.file_path)

    def load_solicitations(self) -> List[Solicitation]:
        """Load solicitations from Parquet file."""
        if not self.file_path.exists():
            return []

        try:
            import json
            from datetime import date

            df = pd.read_parquet(self.file_path)

            solicitations = []
            for _, row in df.iterrows():
                solicitations.append(
                    Solicitation(
                        solicitation_id=row["solicitation_id"],
                        solicitation_number=row["solicitation_number"],
                        title=row["title"],
                        agency_code=row["agency_code"],
                        program_office_id=row["program_office_id"],
                        solicitation_type=row["solicitation_type"],
                        topic_number=row["topic_number"] if pd.notna(row["topic_number"]) else None,
                        full_text=row["full_text"],
                        technical_requirements=row["technical_requirements"],
                        evaluation_criteria=row["evaluation_criteria"],
                        funding_range_min=Decimal(str(row["funding_range_min"])),
                        funding_range_max=Decimal(str(row["funding_range_max"])),
                        proposal_deadline=row["proposal_deadline"]
                        if isinstance(row["proposal_deadline"], date)
                        else (
                            row["proposal_deadline"].date()
                            if pd.notna(row["proposal_deadline"])
                            else date.today()
                        ),
                        award_start_date=row["award_start_date"]
                        if isinstance(row["award_start_date"], date)
                        else (
                            row["award_start_date"].date()
                            if pd.notna(row["award_start_date"])
                            else None
                        ),
                        performance_period=int(row["performance_period"]),
                        keywords=json.loads(row["keywords"]) if row["keywords"] else [],
                        cet_relevance_scores=json.loads(row["cet_relevance_scores"])
                        if row["cet_relevance_scores"]
                        else {},
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )

            return solicitations

        except Exception as e:
            raise Exception(f"Failed to load solicitations: {str(e)}")

    def append_solicitations(self, solicitations: List[Solicitation]) -> None:
        """Append solicitations to existing file."""
        existing = self.load_solicitations()
        all_solicitations = existing + solicitations
        self.save_solicitations(all_solicitations)

    def find_solicitation_by_id(self, solicitation_id: str) -> Optional[Solicitation]:
        """Find solicitation by ID."""
        solicitations = self.load_solicitations()
        for sol in solicitations:
            if sol.solicitation_id == solicitation_id:
                return sol
        return None

    def find_solicitations_by_agency(self, agency_code: str) -> List[Solicitation]:
        """Find solicitations by agency code."""
        solicitations = self.load_solicitations()
        return [sol for sol in solicitations if sol.agency_code == agency_code]
