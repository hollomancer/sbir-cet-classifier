"""Archive download retry logic with cache fallback for SBIR.gov resilience."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from sbir_cet_classifier.common.config import load_config


@dataclass
class RetryAttempt:
    """Record of a single download retry."""

    attempt_number: int
    timestamp: datetime
    success: bool
    error_message: str | None = None


@dataclass
class ArchiveRetryLog:
    """Complete log of retry attempts for an archive download."""

    log_id: str
    source_url: str
    fiscal_year: int
    started_at: datetime
    completed_at: datetime | None
    retry_attempts: list[RetryAttempt]
    final_status: str  # "success", "cache_fallback", "failed"
    cache_path: Path | None = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "log_id": self.log_id,
            "source_url": self.source_url,
            "fiscal_year": self.fiscal_year,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_attempts": [
                {
                    "attempt_number": attempt.attempt_number,
                    "timestamp": attempt.timestamp.isoformat(),
                    "success": attempt.success,
                    "error_message": attempt.error_message,
                }
                for attempt in self.retry_attempts
            ],
            "final_status": self.final_status,
            "cache_path": str(self.cache_path) if self.cache_path else None,
        }


class ArchiveRetryManager:
    """Manages archive downloads with retry logic and cache fallback."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        artifacts_dir: Path | None = None,
        retry_window_hours: int = 24,
        retry_interval_minutes: int = 30,
    ) -> None:
        config = load_config()
        self.cache_dir = cache_dir or config.data_dir / "archive_cache"
        self.artifacts_dir = artifacts_dir or config.artifacts_dir
        self.retry_log_path = self.artifacts_dir / "archive_retry_logs.json"

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.retry_window_hours = retry_window_hours
        self.retry_interval_minutes = retry_interval_minutes

    def download_with_retry(
        self, source_url: str, fiscal_year: int, destination_dir: Path
    ) -> tuple[Path, ArchiveRetryLog]:
        """
        Attempt to download archive with retry logic and cache fallback.

        Args:
            source_url: URL of the SBIR.gov ZIP archive
            fiscal_year: Fiscal year being downloaded
            destination_dir: Target directory for the download

        Returns:
            Tuple of (archive_path, retry_log)

        Raises:
            RuntimeError: If download fails after retry window and no cache available
        """
        log_id = str(uuid.uuid4())
        started_at = datetime.now()
        retry_attempts: list[RetryAttempt] = []

        destination_dir.mkdir(parents=True, exist_ok=True)
        archive_name = source_url.split("/")[-1]
        archive_path = destination_dir / archive_name

        # Calculate retry deadline
        deadline = started_at + timedelta(hours=self.retry_window_hours)
        attempt_number = 0

        while datetime.now() < deadline:
            attempt_number += 1
            attempt_time = datetime.now()

            try:
                # Attempt download
                self._download_archive(source_url, archive_path)

                # Success - cache the archive
                self._cache_archive(archive_path, fiscal_year)

                retry_attempts.append(
                    RetryAttempt(
                        attempt_number=attempt_number,
                        timestamp=attempt_time,
                        success=True,
                    )
                )

                # Build success log
                retry_log = ArchiveRetryLog(
                    log_id=log_id,
                    source_url=source_url,
                    fiscal_year=fiscal_year,
                    started_at=started_at,
                    completed_at=datetime.now(),
                    retry_attempts=retry_attempts,
                    final_status="success",
                )
                self._append_to_log(retry_log)

                return archive_path, retry_log

            except Exception as e:
                error_message = f"{type(e).__name__}: {e}"
                retry_attempts.append(
                    RetryAttempt(
                        attempt_number=attempt_number,
                        timestamp=attempt_time,
                        success=False,
                        error_message=error_message,
                    )
                )

                # Wait before next retry
                if datetime.now() < deadline:
                    time.sleep(self.retry_interval_minutes * 60)

        # Retry window expired - try cache fallback
        cached_path = self._get_cached_archive(fiscal_year)

        if cached_path:
            retry_log = ArchiveRetryLog(
                log_id=log_id,
                source_url=source_url,
                fiscal_year=fiscal_year,
                started_at=started_at,
                completed_at=datetime.now(),
                retry_attempts=retry_attempts,
                final_status="cache_fallback",
                cache_path=cached_path,
            )
            self._append_to_log(retry_log)
            self._alert_operator(retry_log)

            return cached_path, retry_log

        # No cache available - complete failure
        retry_log = ArchiveRetryLog(
            log_id=log_id,
            source_url=source_url,
            fiscal_year=fiscal_year,
            started_at=started_at,
            completed_at=datetime.now(),
            retry_attempts=retry_attempts,
            final_status="failed",
        )
        self._append_to_log(retry_log)
        self._alert_operator(retry_log)

        raise RuntimeError(
            f"Archive download failed after {self.retry_window_hours}h retry window. No cache available for FY{fiscal_year}."
        )

    def _download_archive(self, source_url: str, destination: Path) -> None:
        """Execute a single download attempt."""
        with httpx.stream("GET", source_url, timeout=120.0, follow_redirects=True) as response:
            response.raise_for_status()
            with destination.open("wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)

    def _cache_archive(self, archive_path: Path, fiscal_year: int) -> None:
        """Copy archive to cache directory for future fallback."""
        cache_path = self.cache_dir / f"FY{fiscal_year}_{archive_path.name}"
        cache_path.write_bytes(archive_path.read_bytes())

    def _get_cached_archive(self, fiscal_year: int) -> Path | None:
        """Retrieve cached archive if available."""
        candidates = list(self.cache_dir.glob(f"FY{fiscal_year}_*.zip"))
        if candidates:
            # Return most recent cache
            return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        return None

    def _append_to_log(self, retry_log: ArchiveRetryLog) -> None:
        """Append retry log to cumulative artifact log."""
        if self.retry_log_path.exists():
            existing = json.loads(self.retry_log_path.read_text())
        else:
            existing = {"retry_logs": []}

        existing["retry_logs"].append(retry_log.to_dict())
        self.retry_log_path.write_text(json.dumps(existing, indent=2))

    def _alert_operator(self, retry_log: ArchiveRetryLog) -> None:
        """Generate operator alert for incomplete or failed downloads."""
        alert_path = self.artifacts_dir / f"ALERT_{retry_log.log_id}.txt"
        alert_content = f"""ARCHIVE DOWNLOAD ALERT

Status: {retry_log.final_status}
Fiscal Year: {retry_log.fiscal_year}
Source URL: {retry_log.source_url}
Started: {retry_log.started_at.isoformat()}
Attempts: {len(retry_log.retry_attempts)}

Recommendation: {'Verify cache integrity and rerun refresh' if retry_log.final_status == 'cache_fallback' else 'Check SBIR.gov availability and retry manually'}
"""
        alert_path.write_text(alert_content)


__all__ = [
    "RetryAttempt",
    "ArchiveRetryLog",
    "ArchiveRetryManager",
]
