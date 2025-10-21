"""Lazy enrichment orchestrator for solicitation metadata.

This module coordinates on-demand enrichment of SBIR awards with solicitation
metadata from external APIs (NIH). Enrichment is triggered
when awards are first accessed for classification, viewing, or export.

The orchestrator checks the SQLite cache before querying APIs, handles missing
or unmatched solicitations gracefully, and tracks enrichment failures.

Typical usage:
    from sbir_cet_classifier.features.enrichment import EnrichmentOrchestrator
    from sbir_cet_classifier.common.schemas import Award

    orchestrator = EnrichmentOrchestrator()
    enriched_award = orchestrator.enrich_award(award)

    if enriched_award.enrichment_status == "enriched":
        print(f"Enriched with: {enriched_award.solicitation_description}")
    elif enriched_award.enrichment_status == "enrichment_failed":
        print("Failed to enrich, proceeding with award-only classification")
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sbir_cet_classifier.common.schemas import Award
from sbir_cet_classifier.data.external.nih import NIHAPIError, NIHClient
from sbir_cet_classifier.data.solicitation_cache import SolicitationCache
from sbir_cet_classifier.models.enrichment_metrics import EnrichmentMetrics

logger = logging.getLogger(__name__)

# API source detection rules based on agency codes
AGENCY_TO_API_SOURCE = {
    "NIH": "nih",  # National Institutes of Health has dedicated API
}


@dataclass
class EnrichedAward:
    """Award with solicitation enrichment metadata."""

    award: Award
    """Original award record."""

    enrichment_status: str
    """Status: 'enriched', 'enrichment_failed', 'not_attempted'."""

    solicitation_description: str | None = None
    """Solicitation description text if enriched."""

    solicitation_keywords: list[str] = None
    """Solicitation technical keywords if enriched."""

    api_source: str | None = None
    """API source used for enrichment (nih)."""

    retrieved_at: datetime | None = None
    """Timestamp when solicitation was retrieved."""

    failure_reason: str | None = None
    """Reason if enrichment failed."""

    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.solicitation_keywords is None:
            self.solicitation_keywords = []


class EnrichmentOrchestrator:
    """Coordinates lazy enrichment of awards with solicitation metadata.

    Manages the enrichment workflow: cache lookup → API query → failure handling.
    Tracks enrichment metrics and ensures graceful degradation when solicitations
    are unavailable.

    Attributes:
        cache: SQLite solicitation cache
        metrics: Enrichment telemetry tracker
        nih_client: NIH API client
    """

    def __init__(
        self,
        *,
        cache_path: Path | None = None,
        metrics: EnrichmentMetrics | None = None,
    ) -> None:
        """Initialize enrichment orchestrator.

        Args:
            cache_path: Optional path to cache database (uses default if not provided)
            metrics: Optional metrics tracker (creates new if not provided)
        """
        self.cache = SolicitationCache(cache_path) if cache_path else SolicitationCache()
        self.metrics = metrics if metrics else EnrichmentMetrics()

        # Initialize API clients (lazy loading)
        self.nih_client: NIHClient | None = None

        logger.info("Initialized enrichment orchestrator")

    def __enter__(self) -> EnrichmentOrchestrator:
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - closes connections."""
        self.close()

    def close(self) -> None:
        """Close all connections."""
        self.cache.close()

        if self.nih_client:
            self.nih_client.close()

        logger.debug("Closed enrichment orchestrator")

    def enrich_award(self, award: Award) -> EnrichedAward:
        """Enrich award with solicitation metadata.

        Triggers lazy enrichment: checks cache first, queries API if needed,
        handles failures gracefully. Records metrics for observability.

        Args:
            award: Award record to enrich

        Returns:
            EnrichedAward with enrichment status and solicitation data if available

        Example:
            >>> orchestrator = EnrichmentOrchestrator()
            >>> enriched = orchestrator.enrich_award(award)
            >>> if enriched.enrichment_status == "enriched":
            ...     print(f"Description: {enriched.solicitation_description}")
        """
        # Determine which API source to use based on agency
        api_source = self._determine_api_source(award)

        if not api_source:
            logger.debug(
                "No API source mapping for agency, skipping enrichment",
                extra={"award_id": award.award_id, "agency": award.agency},
            )
            return EnrichedAward(
                award=award,
                enrichment_status="not_attempted",
                failure_reason=f"No API mapping for agency: {award.agency}",
            )

        # Extract solicitation identifier
        solicitation_id = self._extract_solicitation_id(award)

        if not solicitation_id:
            logger.debug(
                "No solicitation ID available, skipping enrichment",
                extra={"award_id": award.award_id},
            )
            return EnrichedAward(
                award=award,
                enrichment_status="not_attempted",
                failure_reason="No solicitation ID in award record",
            )

        # Check cache first
        cached = self.cache.get(api_source, solicitation_id)

        if cached:
            self.metrics.record_cache_hit(api_source)
            self.metrics.record_award_processed(enriched=True)

            logger.debug(
                "Enriched award from cache",
                extra={
                    "award_id": award.award_id,
                    "api_source": api_source,
                    "solicitation_id": solicitation_id,
                },
            )

            return EnrichedAward(
                award=award,
                enrichment_status="enriched",
                solicitation_description=cached.description,
                solicitation_keywords=cached.technical_keywords,
                api_source=cached.api_source,
                retrieved_at=cached.retrieved_at,
            )

        # Cache miss - query API
        self.metrics.record_cache_miss(api_source)

        solicitation_data = self._fetch_from_api(api_source, solicitation_id, award)

        if solicitation_data:
            # Store in cache
            self.cache.put(
                solicitation_data.api_source,
                solicitation_data.solicitation_id,
                solicitation_data.description,
                solicitation_data.technical_keywords,
            )

            self.metrics.record_award_processed(enriched=True)

            logger.info(
                "Enriched award from API",
                extra={
                    "award_id": award.award_id,
                    "api_source": api_source,
                    "solicitation_id": solicitation_id,
                },
            )

            return EnrichedAward(
                award=award,
                enrichment_status="enriched",
                solicitation_description=solicitation_data.description,
                solicitation_keywords=solicitation_data.technical_keywords,
                api_source=solicitation_data.api_source,
                retrieved_at=datetime.now(UTC),
            )

        # Enrichment failed - proceed with award-only classification
        self.metrics.record_award_processed(enriched=False)

        logger.info(
            "Enrichment failed, proceeding with award-only classification",
            extra={
                "award_id": award.award_id,
                "api_source": api_source,
                "solicitation_id": solicitation_id,
            },
        )

        return EnrichedAward(
            award=award,
            enrichment_status="enrichment_failed",
            failure_reason="Solicitation not found or API error",
        )

    def _determine_api_source(self, award: Award) -> str | None:
        """Determine which API source to use for the award.

        Args:
            award: Award record

        Returns:
            API source identifier (nih) or None
        """
        # Normalize agency code
        agency_upper = award.agency.upper().strip()

        # Direct match
        if agency_upper in AGENCY_TO_API_SOURCE:
            return AGENCY_TO_API_SOURCE[agency_upper]

        # Partial match for agency codes with prefixes
        for known_agency, api_source in AGENCY_TO_API_SOURCE.items():
            if known_agency in agency_upper or agency_upper in known_agency:
                return api_source

        # No API available for this agency
        logger.debug(
            "No API available for agency",
            extra={"agency": award.agency},
        )
        return None

    def _extract_solicitation_id(self, award: Award) -> str | None:
        """Extract solicitation identifier from award record.

        Args:
            award: Award record

        Returns:
            Solicitation identifier or None
        """
        # Try topic_code first (most common)
        if hasattr(award, "topic_code") and award.topic_code and award.topic_code != "UNKNOWN":
            return award.topic_code

        # Try solicitation_id if available
        if hasattr(award, "solicitation_id") and award.solicitation_id:
            return award.solicitation_id

        # Try program + solicitation year combination
        if hasattr(award, "program") and hasattr(award, "solicitation_year"):
            if award.program and award.solicitation_year:
                return f"{award.program}-{award.solicitation_year}"

        return None

    def _fetch_from_api(
        self,
        api_source: str,
        solicitation_id: str,
        award: Award,
    ) -> object | None:
        """Fetch solicitation from appropriate API.

        Args:
            api_source: API source identifier (nih)
            solicitation_id: Solicitation identifier
            award: Award record (for additional context)

        Returns:
            SolicitationData if successful, None on failure
        """
        start_time = time.time()
        success = False
        result = None

        try:
            if api_source == "nih":
                result = self._fetch_from_nih(solicitation_id)
            else:
                logger.warning("Unknown API source", extra={"api_source": api_source})

            success = result is not None

        except Exception as e:
            logger.warning(
                "API fetch failed with exception",
                extra={
                    "api_source": api_source,
                    "solicitation_id": solicitation_id,
                    "error": str(e),
                },
            )

        finally:
            # Record metrics
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_api_call(api_source, latency_ms=latency_ms, success=success)

        return result

    def _fetch_from_nih(self, solicitation_id: str) -> object | None:
        """Fetch solicitation from NIH API."""
        if not self.nih_client:
            self.nih_client = NIHClient()

        try:
            return self.nih_client.lookup_solicitation(funding_opportunity=solicitation_id)
        except NIHAPIError as e:
            logger.warning("NIH API error", extra={"error": str(e)})
            return None

    def flush_metrics(self) -> Path:
        """Flush enrichment metrics to artifacts.

        Returns:
            Path to metrics file

        Example:
            >>> orchestrator = EnrichmentOrchestrator()
            >>> # ... enrich awards ...
            >>> metrics_path = orchestrator.flush_metrics()
        """
        return self.metrics.flush()
