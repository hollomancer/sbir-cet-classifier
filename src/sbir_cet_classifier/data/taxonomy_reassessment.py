"""Taxonomy re-assessment pipeline for handling CET taxonomy updates."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sbir_cet_classifier.common.config import load_config
from sbir_cet_classifier.data.store import load_awards_from_parquet
from sbir_cet_classifier.data.taxonomy import TaxonomyRepository
from sbir_cet_classifier.models.applicability import ApplicabilityScorer

if TYPE_CHECKING:
    from sbir_cet_classifier.common.schemas import ApplicabilityAssessment


@dataclass
class TaxonomyDiff:
    """Represents changes between two taxonomy versions."""

    old_version: str
    new_version: str
    added_cets: list[str] = field(default_factory=list)
    removed_cets: list[str] = field(default_factory=list)
    modified_cets: list[str] = field(default_factory=list)

    def has_changes(self) -> bool:
        """Check if there are any meaningful changes."""
        return bool(self.added_cets or self.removed_cets or self.modified_cets)


@dataclass
class ReassessmentManifest:
    """Metadata for a taxonomy re-assessment run."""

    run_id: str
    timestamp: datetime
    old_taxonomy_version: str
    new_taxonomy_version: str
    taxonomy_diff: TaxonomyDiff
    awards_processed: int
    awards_affected: int
    execution_duration_seconds: float

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "old_taxonomy_version": self.old_taxonomy_version,
            "new_taxonomy_version": self.new_taxonomy_version,
            "taxonomy_diff": {
                "added_cets": self.taxonomy_diff.added_cets,
                "removed_cets": self.taxonomy_diff.removed_cets,
                "modified_cets": self.taxonomy_diff.modified_cets,
            },
            "awards_processed": self.awards_processed,
            "awards_affected": self.awards_affected,
            "execution_duration_seconds": self.execution_duration_seconds,
        }


class TaxonomyReassessmentRunner:
    """Orchestrates re-classification when taxonomy versions change."""

    def __init__(
        self,
        taxonomy_repo: TaxonomyRepository | None = None,
        artifacts_dir: Path | None = None,
    ) -> None:
        config = load_config()
        self.taxonomy_repo = taxonomy_repo or TaxonomyRepository(
            config.data_dir / "taxonomy"
        )
        self.artifacts_dir = artifacts_dir or config.artifacts_dir / "taxonomy_updates"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

    def compute_taxonomy_diff(
        self, old_version: str, new_version: str
    ) -> TaxonomyDiff:
        """Compare two taxonomy versions and identify changes."""
        old_taxonomy = self.taxonomy_repo.load(old_version)
        new_taxonomy = self.taxonomy_repo.load(new_version)

        old_ids = {entry.cet_id for entry in old_taxonomy.entries}
        new_ids = {entry.cet_id for entry in new_taxonomy.entries}

        added = list(new_ids - old_ids)
        removed = list(old_ids - new_ids)

        # Check for modified definitions in common IDs
        common_ids = old_ids & new_ids
        modified = []
        for cet_id in common_ids:
            old_entry = old_taxonomy.get(cet_id)
            new_entry = new_taxonomy.get(cet_id)
            # Consider modified if definition or name changed
            if (
                old_entry
                and new_entry
                and (
                    old_entry.definition != new_entry.definition
                    or old_entry.name != new_entry.name
                )
            ):
                modified.append(cet_id)

        return TaxonomyDiff(
            old_version=old_version,
            new_version=new_version,
            added_cets=sorted(added),
            removed_cets=sorted(removed),
            modified_cets=sorted(modified),
        )

    def reassess_awards(
        self,
        new_version: str,
        fiscal_year_start: int | None = None,
        fiscal_year_end: int | None = None,
    ) -> ReassessmentManifest:
        """
        Re-run applicability classification with a new taxonomy version.

        Args:
            new_version: Target taxonomy version to apply
            fiscal_year_start: Optional fiscal year filter (inclusive)
            fiscal_year_end: Optional fiscal year filter (inclusive)

        Returns:
            Manifest documenting the reassessment run
        """
        start_time = datetime.now()
        run_id = str(uuid.uuid4())

        # Load new taxonomy
        new_taxonomy = self.taxonomy_repo.load(new_version)

        # Determine old version (current latest before this update)
        versions = self.taxonomy_repo.list_versions()
        old_version = versions[-2] if len(versions) >= 2 else versions[0]

        # Compute diff
        taxonomy_diff = self.compute_taxonomy_diff(old_version, new_version)

        # Load awards from storage
        config = load_config()
        awards_df = load_awards_from_parquet(
            config.data_dir / "processed",
            fiscal_year_start=fiscal_year_start,
            fiscal_year_end=fiscal_year_end,
        )

        # Initialize scorer with new taxonomy
        scorer = ApplicabilityScorer(taxonomy=new_taxonomy)

        # Re-classify each award
        awards_processed = 0
        awards_affected = 0
        new_assessments: list[ApplicabilityAssessment] = []

        for _, award_row in awards_df.iterrows():
            awards_processed += 1

            # Score with new taxonomy
            assessment = scorer.score_award(
                award_id=award_row["award_id"],
                abstract=award_row.get("abstract"),
                keywords=award_row.get("keywords", []),
                topic_code=award_row["topic_code"],
            )

            # Tag assessment with new taxonomy version
            assessment.taxonomy_version = new_version
            new_assessments.append(assessment)

            # Check if classification changed (would require loading old assessment)
            # For simplicity, consider all awards affected if taxonomy changed
            if taxonomy_diff.has_changes():
                awards_affected += 1

        # Persist new assessments (append to historical record)
        self._save_assessments(new_assessments, new_version)

        # Calculate execution time
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Build manifest
        manifest = ReassessmentManifest(
            run_id=run_id,
            timestamp=start_time,
            old_taxonomy_version=old_version,
            new_taxonomy_version=new_version,
            taxonomy_diff=taxonomy_diff,
            awards_processed=awards_processed,
            awards_affected=awards_affected,
            execution_duration_seconds=duration,
        )

        # Save manifest
        self._save_manifest(manifest)

        return manifest

    def _save_assessments(
        self, assessments: list[ApplicabilityAssessment], version: str
    ) -> None:
        """Persist reassessments to artifact storage."""
        config = load_config()
        assessments_dir = config.artifacts_dir / "assessments" / version
        assessments_dir.mkdir(parents=True, exist_ok=True)

        output_path = assessments_dir / "reassessments.json"
        payload = [assessment.model_dump(mode="json") for assessment in assessments]
        output_path.write_text(json.dumps(payload, indent=2))

    def _save_manifest(self, manifest: ReassessmentManifest) -> None:
        """Write reassessment manifest to artifacts."""
        manifest_path = self.artifacts_dir / f"{manifest.run_id}.json"
        manifest_path.write_text(json.dumps(manifest.to_dict(), indent=2))


__all__ = [
    "TaxonomyDiff",
    "ReassessmentManifest",
    "TaxonomyReassessmentRunner",
]
