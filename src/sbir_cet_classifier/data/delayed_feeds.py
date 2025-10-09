"""Delayed-feed queue handling for asynchronous agency data arrivals."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sbir_cet_classifier.common.config import load_config


@dataclass
class PendingFeed:
    """Represents a delayed or pending agency data file."""

    feed_id: str
    agency: str
    fiscal_year: int
    file_path: Path
    received_at: datetime
    status: str  # "pending", "processed", "failed"
    processed_at: datetime | None = None
    error_message: str | None = None


@dataclass
class ReconciliationReport:
    """Summary of delayed feed processing and deduplication results."""

    report_id: str
    timestamp: datetime
    feeds_processed: int
    awards_ingested: int
    duplicates_found: int
    late_arrivals: list[str] = field(default_factory=list)  # Agency names
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "feeds_processed": self.feeds_processed,
            "awards_ingested": self.awards_ingested,
            "duplicates_found": self.duplicates_found,
            "late_arrivals": self.late_arrivals,
            "errors": self.errors,
        }


class DelayedFeedQueue:
    """Manages pending agency data files and deduplication."""

    def __init__(
        self, queue_dir: Path | None = None, artifacts_dir: Path | None = None
    ) -> None:
        config = load_config()
        self.queue_dir = queue_dir or config.data_dir / "pending_feeds"
        self.artifacts_dir = (
            artifacts_dir or config.artifacts_dir / "delayed_feed_reports"
        )

        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.queue_manifest_path = self.queue_dir / "queue_manifest.json"

    def enqueue_feed(
        self, agency: str, fiscal_year: int, file_path: Path
    ) -> PendingFeed:
        """
        Add a delayed agency feed file to the pending queue.

        Args:
            agency: Agency acronym (e.g., "AF", "NASA")
            fiscal_year: Fiscal year of the data
            file_path: Path to the pending data file

        Returns:
            PendingFeed entry representing the queued file
        """
        feed_id = str(uuid.uuid4())
        pending_feed = PendingFeed(
            feed_id=feed_id,
            agency=agency,
            fiscal_year=fiscal_year,
            file_path=file_path,
            received_at=datetime.now(),
            status="pending",
        )

        # Update manifest
        self._append_to_manifest(pending_feed)

        return pending_feed

    def process_pending_feeds(self) -> ReconciliationReport:
        """
        Process all pending feeds and deduplicate by (award_id, agency).

        Returns:
            ReconciliationReport documenting the processing run
        """
        report_id = str(uuid.uuid4())
        start_time = datetime.now()

        manifest = self._load_manifest()
        pending_feeds = [f for f in manifest if f.status == "pending"]

        awards_ingested = 0
        duplicates_found = 0
        late_arrivals = []
        errors = []
        feeds_processed = 0

        for feed in pending_feeds:
            try:
                # Import awards from the delayed feed
                awards = self._import_feed_file(feed.file_path)

                # Deduplicate by (award_id, agency)
                dedup_awards, dup_count = self._deduplicate_awards(awards, feed.agency)

                awards_ingested += len(dedup_awards)
                duplicates_found += dup_count
                feeds_processed += 1

                # Mark as processed
                feed.status = "processed"
                feed.processed_at = datetime.now()

                # Track late arrivals
                late_arrivals.append(feed.agency)

            except Exception as e:
                error_msg = f"Feed {feed.feed_id} ({feed.agency}): {type(e).__name__}: {e}"
                errors.append(error_msg)
                feed.status = "failed"
                feed.error_message = error_msg

        # Update manifest with new statuses
        self._save_manifest(manifest)

        # Build reconciliation report
        report = ReconciliationReport(
            report_id=report_id,
            timestamp=start_time,
            feeds_processed=feeds_processed,
            awards_ingested=awards_ingested,
            duplicates_found=duplicates_found,
            late_arrivals=late_arrivals,
            errors=errors,
        )

        # Save report to artifacts
        self._save_report(report)

        return report

    def list_pending(self) -> list[PendingFeed]:
        """Return all feeds with status 'pending'."""
        manifest = self._load_manifest()
        return [f for f in manifest if f.status == "pending"]

    def _import_feed_file(self, file_path: Path) -> list[dict]:
        """Parse feed file and return list of award dictionaries."""
        # Placeholder: In production, this would handle CSV/JSON/ZIP parsing
        # For now, assume JSON array format
        if not file_path.exists():
            raise FileNotFoundError(f"Feed file not found: {file_path}")

        payload = json.loads(file_path.read_text())
        return payload.get("awards", [])

    def _deduplicate_awards(
        self, awards: list[dict], agency: str
    ) -> tuple[list[dict], int]:
        """
        Deduplicate awards by (award_id, agency) key.

        Returns:
            Tuple of (unique_awards, duplicate_count)
        """
        seen_keys = set()
        unique_awards = []
        duplicate_count = 0

        for award in awards:
            key = (award.get("award_id"), agency)
            if key in seen_keys:
                duplicate_count += 1
            else:
                seen_keys.add(key)
                unique_awards.append(award)

        return unique_awards, duplicate_count

    def _load_manifest(self) -> list[PendingFeed]:
        """Load the queue manifest from disk."""
        if not self.queue_manifest_path.exists():
            return []

        payload = json.loads(self.queue_manifest_path.read_text())
        feeds = []
        for entry in payload.get("feeds", []):
            feeds.append(
                PendingFeed(
                    feed_id=entry["feed_id"],
                    agency=entry["agency"],
                    fiscal_year=entry["fiscal_year"],
                    file_path=Path(entry["file_path"]),
                    received_at=datetime.fromisoformat(entry["received_at"]),
                    status=entry["status"],
                    processed_at=(
                        datetime.fromisoformat(entry["processed_at"])
                        if entry.get("processed_at")
                        else None
                    ),
                    error_message=entry.get("error_message"),
                )
            )
        return feeds

    def _save_manifest(self, feeds: list[PendingFeed]) -> None:
        """Persist the full queue manifest."""
        payload = {
            "feeds": [
                {
                    "feed_id": f.feed_id,
                    "agency": f.agency,
                    "fiscal_year": f.fiscal_year,
                    "file_path": str(f.file_path),
                    "received_at": f.received_at.isoformat(),
                    "status": f.status,
                    "processed_at": f.processed_at.isoformat()
                    if f.processed_at
                    else None,
                    "error_message": f.error_message,
                }
                for f in feeds
            ]
        }
        self.queue_manifest_path.write_text(json.dumps(payload, indent=2))

    def _append_to_manifest(self, feed: PendingFeed) -> None:
        """Add a new pending feed to the manifest."""
        feeds = self._load_manifest()
        feeds.append(feed)
        self._save_manifest(feeds)

    def _save_report(self, report: ReconciliationReport) -> None:
        """Write reconciliation report to artifacts directory."""
        report_path = self.artifacts_dir / f"{report.report_id}.json"
        report_path.write_text(json.dumps(report.to_dict(), indent=2))


__all__ = [
    "PendingFeed",
    "ReconciliationReport",
    "DelayedFeedQueue",
]
