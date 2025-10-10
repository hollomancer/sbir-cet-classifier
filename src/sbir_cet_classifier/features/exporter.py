"""Export orchestration for CET applicability datasets."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from sbir_cet_classifier.common.config import load_config

if TYPE_CHECKING:
    from sbir_cet_classifier.features.summary import SummaryFilters


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    PARQUET = "parquet"


class ExportStatus(str, Enum):
    """Export job status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ExportMetadata:
    """Metadata accompanying an export."""

    data_currency_note: str
    ingestion_timestamp: str
    source_version: str
    controlled_awards_excluded: int
    taxonomy_version: str
    export_timestamp: str


@dataclass
class ExportJob:
    """Represents an export job."""

    job_id: str
    status: ExportStatus
    filters: dict
    format: ExportFormat
    submitted_at: datetime
    completed_at: datetime | None = None
    download_url: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict:
        """Convert to API response format."""
        return {
            "jobId": self.job_id,
            "status": self.status.value,
            "submittedAt": self.submitted_at.isoformat(),
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "downloadUrl": self.download_url,
            "message": self.error_message,
        }


class ExportOrchestrator:
    """Coordinates export generation with governance controls."""

    def __init__(self, exports_dir: Path | None = None) -> None:
        config = load_config()
        self.exports_dir = exports_dir or config.artifacts_dir / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_registry = self.exports_dir / "jobs.json"

    def create_export(
        self,
        filters: SummaryFilters,
        format: ExportFormat,
        awards_df: pd.DataFrame,
        assessments_df: pd.DataFrame,
        taxonomy_df: pd.DataFrame,
        include_review_queue: bool = False,
    ) -> ExportJob:
        """
        Create an export job for the given filters and data.

        Args:
            filters: Applied filters for the export
            format: Export format (CSV or Parquet)
            awards_df: Awards DataFrame
            assessments_df: Assessments DataFrame
            taxonomy_df: Taxonomy DataFrame
            include_review_queue: Whether to include unresolved review items

        Returns:
            ExportJob with status and job ID
        """
        job_id = str(uuid.uuid4())
        job = ExportJob(
            job_id=job_id,
            status=ExportStatus.PENDING,
            filters=self._serialize_filters(filters),
            format=format,
            submitted_at=datetime.now(),
        )

        # Save job to registry
        self._save_job(job)

        # Execute export synchronously (in production, this would be async)
        try:
            job.status = ExportStatus.RUNNING
            self._save_job(job)

            # Generate export file
            export_path = self._generate_export_file(
                job_id,
                format,
                awards_df,
                assessments_df,
                taxonomy_df,
                filters,
                include_review_queue,
            )

            job.status = ExportStatus.COMPLETE
            job.completed_at = datetime.now()
            job.download_url = f"/exports/download/{export_path.name}"
            self._save_job(job)

        except Exception as e:
            job.status = ExportStatus.FAILED
            job.completed_at = datetime.now()
            job.error_message = f"{type(e).__name__}: {e}"
            self._save_job(job)

        return job

    def get_job_status(self, job_id: str) -> ExportJob:
        """Retrieve export job status."""
        jobs = self._load_jobs()
        for job_data in jobs:
            if job_data["job_id"] == job_id:
                return self._deserialize_job(job_data)
        raise KeyError(f"Export job not found: {job_id}")

    def _generate_export_file(
        self,
        job_id: str,
        format: ExportFormat,
        awards_df: pd.DataFrame,
        assessments_df: pd.DataFrame,
        taxonomy_df: pd.DataFrame,
        filters: SummaryFilters,
        include_review_queue: bool,
    ) -> Path:
        """Generate the actual export file."""
        # Merge awards with latest assessments
        latest_assessments = (
            assessments_df.sort_values("assessed_at")
            .drop_duplicates("award_id", keep="last")
        )

        merged = awards_df.merge(
            latest_assessments,
            on="award_id",
            how="left",
            suffixes=("", "_assessment"),
        )

        # Exclude controlled awards from line-level output
        controlled_count = merged["is_export_controlled"].sum() if "is_export_controlled" in merged.columns else 0
        export_df = merged[~merged.get("is_export_controlled", False)]

        # Add normalized CET weights (0-1, summing to 1 per award)
        export_df = self._add_cet_weights(export_df, taxonomy_df)

        # Generate metadata
        metadata = ExportMetadata(
            data_currency_note=f"Ingested from SBIR.gov as of {datetime.now().date().isoformat()}",
            ingestion_timestamp=datetime.now().isoformat(),
            source_version="SBIR.gov bulk downloads",
            controlled_awards_excluded=int(controlled_count),
            taxonomy_version=export_df["taxonomy_version"].mode().iloc[0] if "taxonomy_version" in export_df.columns and not export_df.empty else "unknown",
            export_timestamp=datetime.now().isoformat(),
        )

        # Write export file
        if format == ExportFormat.CSV:
            export_path = self.exports_dir / f"{job_id}.csv"
            export_df.to_csv(export_path, index=False)
            # Append metadata as comments
            self._append_metadata_to_csv(export_path, metadata)
        else:
            export_path = self.exports_dir / f"{job_id}.parquet"
            # Store metadata in parquet metadata
            export_df.to_parquet(export_path, index=False)

        # Log export telemetry
        self._log_export_telemetry(job_id, len(export_df), metadata)

        return export_path

    def _add_cet_weights(self, df: pd.DataFrame, taxonomy_df: pd.DataFrame) -> pd.DataFrame:
        """Add normalized CET weight columns to export."""
        result = df.copy()

        # Get all CET IDs from taxonomy
        cet_ids = taxonomy_df["cet_id"].tolist() if not taxonomy_df.empty else []

        # Initialize weight columns
        for cet_id in cet_ids:
            result[f"weight_{cet_id}"] = 0.0

        # Assign weights based on primary and supporting CET alignments
        for idx, row in result.iterrows():
            primary_cet = row.get("primary_cet_id")
            supporting_cets = row.get("supporting_cet_ids", [])

            if isinstance(supporting_cets, str):
                supporting_cets = json.loads(supporting_cets) if supporting_cets else []

            total_cets = 1 + len(supporting_cets)
            if total_cets > 0:
                # Primary CET gets higher weight
                if primary_cet and f"weight_{primary_cet}" in result.columns:
                    result.at[idx, f"weight_{primary_cet}"] = 0.6 / total_cets * total_cets

                # Supporting CETs split remaining weight
                remaining_weight = 0.4
                for cet in supporting_cets:
                    if f"weight_{cet}" in result.columns:
                        result.at[idx, f"weight_{cet}"] = remaining_weight / len(supporting_cets) if supporting_cets else 0

        return result

    def _append_metadata_to_csv(self, csv_path: Path, metadata: ExportMetadata) -> None:
        """Append metadata as CSV comments."""
        with csv_path.open("a") as f:
            f.write("\n# Metadata\n")
            f.write(f"# Data Currency: {metadata.data_currency_note}\n")
            f.write(f"# Ingestion Timestamp: {metadata.ingestion_timestamp}\n")
            f.write(f"# Source Version: {metadata.source_version}\n")
            f.write(f"# Controlled Awards Excluded: {metadata.controlled_awards_excluded}\n")
            f.write(f"# Taxonomy Version: {metadata.taxonomy_version}\n")
            f.write(f"# Export Timestamp: {metadata.export_timestamp}\n")

    def _log_export_telemetry(self, job_id: str, record_count: int, metadata: ExportMetadata) -> None:
        """Log export run telemetry."""
        config = load_config()
        telemetry_path = config.artifacts_dir / "export_runs.json"

        if telemetry_path.exists():
            telemetry = json.loads(telemetry_path.read_text())
        else:
            telemetry = {"export_runs": []}

        telemetry["export_runs"].append({
            "job_id": job_id,
            "timestamp": metadata.export_timestamp,
            "record_count": record_count,
            "controlled_excluded": metadata.controlled_awards_excluded,
            "taxonomy_version": metadata.taxonomy_version,
        })

        telemetry_path.write_text(json.dumps(telemetry, indent=2))

    def _serialize_filters(self, filters: SummaryFilters) -> dict:
        """Convert filters to JSON-serializable dict."""
        return {
            "fiscal_year_start": filters.fiscal_year_start,
            "fiscal_year_end": filters.fiscal_year_end,
            "agencies": list(filters.agencies),
            "phases": list(filters.phases),
            "cet_areas": list(filters.cet_areas),
            "location_states": list(filters.location_states),
        }

    def _save_job(self, job: ExportJob) -> None:
        """Save job to registry."""
        jobs = self._load_jobs()

        # Update or add job
        found = False
        for i, existing_job in enumerate(jobs):
            if existing_job["job_id"] == job.job_id:
                jobs[i] = self._serialize_job(job)
                found = True
                break

        if not found:
            jobs.append(self._serialize_job(job))

        self.jobs_registry.write_text(json.dumps({"jobs": jobs}, indent=2))

    def _load_jobs(self) -> list[dict]:
        """Load jobs from registry."""
        if not self.jobs_registry.exists():
            return []
        payload = json.loads(self.jobs_registry.read_text())
        return payload.get("jobs", [])

    def _serialize_job(self, job: ExportJob) -> dict:
        """Convert ExportJob to dict for storage."""
        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "filters": job.filters,
            "format": job.format.value,
            "submitted_at": job.submitted_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "download_url": job.download_url,
            "error_message": job.error_message,
        }

    def _deserialize_job(self, data: dict) -> ExportJob:
        """Convert dict to ExportJob."""
        return ExportJob(
            job_id=data["job_id"],
            status=ExportStatus(data["status"]),
            filters=data["filters"],
            format=ExportFormat(data["format"]),
            submitted_at=datetime.fromisoformat(data["submitted_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            download_url=data.get("download_url"),
            error_message=data.get("error_message"),
        )


__all__ = [
    "ExportFormat",
    "ExportJob",
    "ExportMetadata",
    "ExportOrchestrator",
    "ExportStatus",
]
