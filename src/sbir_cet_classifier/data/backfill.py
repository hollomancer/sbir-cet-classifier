"""Fiscal-year backfill workflow for reprocessing corrected SBIR award data."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sbir_cet_classifier.common.config import load_config
from sbir_cet_classifier.data.ingest import ingest_fiscal_year
from sbir_cet_classifier.data.taxonomy import load_taxonomy_from_directory
from sbir_cet_classifier.models.applicability import ApplicabilityScorer

if TYPE_CHECKING:
    from sbir_cet_classifier.common.schemas import ApplicabilityAssessment


@dataclass
class BackfillWindow:
    """Defines the scope of a backfill operation."""

    fiscal_year_start: int
    fiscal_year_end: int
    reason: str  # e.g., "SBIR.gov correction", "schema migration"
    operator_notes: str | None = None


@dataclass
class BackfillManifest:
    """Metadata for a backfill run."""

    run_id: str
    timestamp: datetime
    window: BackfillWindow
    fiscal_years_processed: list[int]
    awards_reprocessed: int
    execution_duration_seconds: float
    errors: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "window": {
                "fiscal_year_start": self.window.fiscal_year_start,
                "fiscal_year_end": self.window.fiscal_year_end,
                "reason": self.window.reason,
                "operator_notes": self.window.operator_notes,
            },
            "fiscal_years_processed": self.fiscal_years_processed,
            "awards_reprocessed": self.awards_reprocessed,
            "execution_duration_seconds": self.execution_duration_seconds,
            "errors": self.errors,
        }


class BackfillRunner:
    """Coordinates fiscal-year backfills with targeted partition updates."""

    def __init__(self, artifacts_dir: Path | None = None) -> None:
        config = load_config()
        self.artifacts_dir = artifacts_dir or config.artifacts_dir
        self.backfill_log_path = self.artifacts_dir / "backfill_runs.json"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def run_backfill(
        self,
        window: BackfillWindow,
        source_url_template: str = "https://www.sbir.gov/sites/default/files/sbir_awards_FY{year}.zip",
    ) -> BackfillManifest:
        """
        Execute a backfill for the specified fiscal year range.

        Args:
            window: Defines the fiscal years and reasoning for backfill
            source_url_template: URL template with {year} placeholder

        Returns:
            Manifest documenting the backfill operation
        """
        start_time = datetime.now()
        run_id = str(uuid.uuid4())
        errors = []
        processed_years = []
        total_awards = 0

        config = load_config()

        for fiscal_year in range(window.fiscal_year_start, window.fiscal_year_end + 1):
            try:
                # Re-ingest the fiscal year data
                source_url = source_url_template.format(year=fiscal_year)
                result = ingest_fiscal_year(fiscal_year, source_url, config=config)

                # Re-run applicability scoring
                taxonomy = load_taxonomy_from_directory(config.data_dir / "taxonomy")
                scorer = ApplicabilityScorer(taxonomy=taxonomy)

                # Process awards from the newly ingested partition
                from sbir_cet_classifier.data.ingest import iter_awards_for_year

                assessments: list[ApplicabilityAssessment] = []
                for award in iter_awards_for_year(fiscal_year, config=config):
                    assessment = scorer.score_award(
                        award_id=award.award_id,
                        abstract=award.abstract,
                        keywords=award.keywords.split(",") if award.keywords else [],
                        topic_code=award.topic_code,
                    )
                    assessments.append(assessment)

                # Persist updated assessments
                self._save_assessments(assessments, fiscal_year)

                processed_years.append(fiscal_year)
                total_awards += result.records_ingested

            except Exception as e:
                error_msg = f"Fiscal year {fiscal_year}: {type(e).__name__}: {e}"
                errors.append(error_msg)

        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Build manifest
        manifest = BackfillManifest(
            run_id=run_id,
            timestamp=start_time,
            window=window,
            fiscal_years_processed=processed_years,
            awards_reprocessed=total_awards,
            execution_duration_seconds=duration,
            errors=errors,
        )

        # Append to backfill log
        self._append_to_log(manifest)

        return manifest

    def _save_assessments(
        self, assessments: list[ApplicabilityAssessment], fiscal_year: int
    ) -> None:
        """Persist reassessments after backfill."""
        config = load_config()
        assessments_dir = config.artifacts_dir / "assessments" / str(fiscal_year)
        assessments_dir.mkdir(parents=True, exist_ok=True)

        output_path = assessments_dir / "backfill_assessments.json"
        payload = [assessment.model_dump(mode="json") for assessment in assessments]
        output_path.write_text(json.dumps(payload, indent=2))

    def _append_to_log(self, manifest: BackfillManifest) -> None:
        """Append backfill manifest to the cumulative log."""
        # Load existing log
        if self.backfill_log_path.exists():
            existing_log = json.loads(self.backfill_log_path.read_text())
        else:
            existing_log = {"backfill_runs": []}

        # Append new manifest
        existing_log["backfill_runs"].append(manifest.to_dict())

        # Write back
        self.backfill_log_path.write_text(json.dumps(existing_log, indent=2))


__all__ = [
    "BackfillWindow",
    "BackfillManifest",
    "BackfillRunner",
]
