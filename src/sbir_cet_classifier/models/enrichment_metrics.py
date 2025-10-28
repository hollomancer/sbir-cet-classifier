"""Enrichment telemetry module for observability.

This module tracks solicitation enrichment metrics including cache hit rates,
API latency distributions, and enrichment success/failure rates per API source.

Metrics are persisted to artifacts/enrichment_runs.json for observability
and performance analysis per NFR-008.

Typical usage:
    from sbir_cet_classifier.models.enrichment_metrics import EnrichmentMetrics

    metrics = EnrichmentMetrics()
    metrics.record_cache_hit("nih")
    metrics.record_api_call("nih", latency_ms=150.5, success=True)
    metrics.flush()  # Write to artifacts/enrichment_runs.json
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from sbir_cet_classifier.common.datetime_utils import UTC
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Default artifacts directory for enrichment metrics
DEFAULT_ARTIFACTS_DIR = Path("artifacts")


@dataclass
class APISourceMetrics:
    """Per-API-source enrichment metrics."""

    api_source: str
    """API source identifier (nih)."""

    cache_hits: int = 0
    """Number of cache hits for this API source."""

    cache_misses: int = 0
    """Number of cache misses requiring API calls."""

    api_calls_successful: int = 0
    """Number of successful API calls."""

    api_calls_failed: int = 0
    """Number of failed API calls (timeout, error, not found)."""

    latencies_ms: list[float] = field(default_factory=list)
    """Latency measurements for API calls in milliseconds."""

    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate percentage."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100.0

    @property
    def success_rate(self) -> float:
        """Calculate API call success rate percentage."""
        total = self.api_calls_successful + self.api_calls_failed
        if total == 0:
            return 0.0
        return (self.api_calls_successful / total) * 100.0

    @property
    def latency_p50(self) -> float | None:
        """Calculate p50 (median) latency in milliseconds."""
        if not self.latencies_ms:
            return None
        return float(np.percentile(self.latencies_ms, 50))

    @property
    def latency_p95(self) -> float | None:
        """Calculate p95 latency in milliseconds."""
        if not self.latencies_ms:
            return None
        return float(np.percentile(self.latencies_ms, 95))

    @property
    def latency_p99(self) -> float | None:
        """Calculate p99 latency in milliseconds."""
        if not self.latencies_ms:
            return None
        return float(np.percentile(self.latencies_ms, 99))

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "api_source": self.api_source,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate_pct": round(self.cache_hit_rate, 2),
            "api_calls_successful": self.api_calls_successful,
            "api_calls_failed": self.api_calls_failed,
            "success_rate_pct": round(self.success_rate, 2),
            "latency_ms": {
                "p50": round(self.latency_p50, 2) if self.latency_p50 is not None else None,
                "p95": round(self.latency_p95, 2) if self.latency_p95 is not None else None,
                "p99": round(self.latency_p99, 2) if self.latency_p99 is not None else None,
                "count": len(self.latencies_ms),
            },
        }


@dataclass
class EnrichmentRun:
    """Represents a single enrichment run with aggregated metrics."""

    run_id: str
    """Unique identifier for this enrichment run."""

    started_at: datetime
    """Timestamp when enrichment run started."""

    completed_at: datetime | None = None
    """Timestamp when enrichment run completed."""

    api_metrics: dict[str, APISourceMetrics] = field(default_factory=dict)
    """Per-API-source metrics, keyed by api_source."""

    total_awards_processed: int = 0
    """Total number of awards processed in this run."""

    awards_enriched: int = 0
    """Number of awards successfully enriched."""

    awards_failed: int = 0
    """Number of awards that failed enrichment."""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds() if self.completed_at else None
            ),
            "total_awards_processed": self.total_awards_processed,
            "awards_enriched": self.awards_enriched,
            "awards_failed": self.awards_failed,
            "enrichment_rate_pct": (
                round((self.awards_enriched / self.total_awards_processed) * 100, 2)
                if self.total_awards_processed > 0
                else 0.0
            ),
            "api_sources": {
                source: metrics.to_dict() for source, metrics in self.api_metrics.items()
            },
        }


class EnrichmentMetrics:
    """Tracks and persists enrichment telemetry metrics.

    Provides methods to record cache hits/misses, API calls, latencies,
    and success/failure events. Metrics are aggregated per API source
    and can be flushed to artifacts/enrichment_runs.json.

    Attributes:
        run_id: Unique identifier for current enrichment run
        started_at: Timestamp when metrics tracking started
        artifacts_dir: Directory for writing metrics artifacts
    """

    def __init__(
        self,
        *,
        run_id: str | None = None,
        artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR,
    ) -> None:
        """Initialize enrichment metrics tracker.

        Args:
            run_id: Optional run identifier (generated if not provided)
            artifacts_dir: Directory for writing metrics (default: artifacts/)
        """
        self.run_id = run_id or self._generate_run_id()
        self.started_at = datetime.now(UTC)
        self.artifacts_dir = Path(artifacts_dir)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self._api_metrics: dict[str, APISourceMetrics] = {}
        self._total_awards_processed = 0
        self._awards_enriched = 0
        self._awards_failed = 0

        logger.info("Initialized enrichment metrics", extra={"run_id": self.run_id})

    def _generate_run_id(self) -> str:
        """Generate unique run identifier."""
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return f"enrichment_{timestamp}"

    def _get_or_create_api_metrics(self, api_source: str) -> APISourceMetrics:
        """Get or create metrics tracker for API source."""
        if api_source not in self._api_metrics:
            self._api_metrics[api_source] = APISourceMetrics(api_source=api_source)
        return self._api_metrics[api_source]

    def record_cache_hit(self, api_source: str) -> None:
        """Record a cache hit for the specified API source.

        Args:
            api_source: API source identifier (nih)
        """
        metrics = self._get_or_create_api_metrics(api_source)
        metrics.cache_hits += 1

        logger.debug(
            "Recorded cache hit",
            extra={"api_source": api_source, "run_id": self.run_id},
        )

    def record_cache_miss(self, api_source: str) -> None:
        """Record a cache miss for the specified API source.

        Args:
            api_source: API source identifier (nih)
        """
        metrics = self._get_or_create_api_metrics(api_source)
        metrics.cache_misses += 1

        logger.debug(
            "Recorded cache miss",
            extra={"api_source": api_source, "run_id": self.run_id},
        )

    def record_api_call(
        self,
        api_source: str,
        *,
        latency_ms: float,
        success: bool,
    ) -> None:
        """Record an API call with latency and outcome.

        Args:
            api_source: API source identifier (nih)
            latency_ms: API call latency in milliseconds
            success: Whether API call succeeded (True) or failed (False)
        """
        metrics = self._get_or_create_api_metrics(api_source)

        if success:
            metrics.api_calls_successful += 1
        else:
            metrics.api_calls_failed += 1

        metrics.latencies_ms.append(latency_ms)

        logger.debug(
            "Recorded API call",
            extra={
                "api_source": api_source,
                "latency_ms": latency_ms,
                "success": success,
                "run_id": self.run_id,
            },
        )

    def record_award_processed(self, *, enriched: bool) -> None:
        """Record that an award was processed.

        Args:
            enriched: Whether award was successfully enriched (True) or failed (False)
        """
        self._total_awards_processed += 1

        if enriched:
            self._awards_enriched += 1
        else:
            self._awards_failed += 1

        logger.debug(
            "Recorded award processed",
            extra={"enriched": enriched, "run_id": self.run_id},
        )

    def get_summary(self) -> dict:
        """Get current metrics summary.

        Returns:
            Dictionary containing aggregated metrics across all API sources
        """
        run = EnrichmentRun(
            run_id=self.run_id,
            started_at=self.started_at,
            completed_at=datetime.now(UTC),
            api_metrics=self._api_metrics.copy(),
            total_awards_processed=self._total_awards_processed,
            awards_enriched=self._awards_enriched,
            awards_failed=self._awards_failed,
        )

        return run.to_dict()

    def flush(self) -> Path:
        """Flush metrics to artifacts/enrichment_runs.json.

        Returns:
            Path to written metrics file

        Example:
            >>> metrics = EnrichmentMetrics()
            >>> # ... record metrics ...
            >>> path = metrics.flush()
            >>> print(f"Metrics written to {path}")
        """
        completed_at = datetime.now(UTC)

        run = EnrichmentRun(
            run_id=self.run_id,
            started_at=self.started_at,
            completed_at=completed_at,
            api_metrics=self._api_metrics.copy(),
            total_awards_processed=self._total_awards_processed,
            awards_enriched=self._awards_enriched,
            awards_failed=self._awards_failed,
        )

        # Read existing runs
        metrics_file = self.artifacts_dir / "enrichment_runs.json"
        existing_runs = []

        if metrics_file.exists():
            try:
                with metrics_file.open("r") as f:
                    existing_data = json.load(f)
                    if isinstance(existing_data, list):
                        existing_runs = existing_data
                    elif isinstance(existing_data, dict) and "runs" in existing_data:
                        existing_runs = existing_data["runs"]
            except (OSError, json.JSONDecodeError) as e:
                logger.warning(
                    "Failed to read existing enrichment metrics, starting fresh",
                    extra={"error": str(e)},
                )

        # Append new run
        existing_runs.append(run.to_dict())

        # Write back
        output = {
            "runs": existing_runs,
            "last_updated": completed_at.isoformat(),
            "total_runs": len(existing_runs),
        }

        with metrics_file.open("w") as f:
            json.dump(output, f, indent=2)

        logger.info(
            "Flushed enrichment metrics",
            extra={"run_id": self.run_id, "metrics_file": str(metrics_file)},
        )

        return metrics_file


def load_enrichment_metrics(
    artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR,
) -> list[dict]:
    """Load historical enrichment metrics from artifacts.

    Args:
        artifacts_dir: Directory containing enrichment_runs.json

    Returns:
        List of enrichment run dictionaries

    Example:
        >>> runs = load_enrichment_metrics()
        >>> for run in runs:
        ...     print(f"{run['run_id']}: {run['enrichment_rate_pct']}% enriched")
    """
    metrics_file = Path(artifacts_dir) / "enrichment_runs.json"

    if not metrics_file.exists():
        logger.info("No enrichment metrics file found")
        return []

    try:
        with metrics_file.open("r") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "runs" in data:
            return data["runs"]
        else:
            logger.warning("Unexpected enrichment metrics format")
            return []

    except (OSError, json.JSONDecodeError) as e:
        logger.error("Failed to load enrichment metrics", extra={"error": str(e)})
        return []
