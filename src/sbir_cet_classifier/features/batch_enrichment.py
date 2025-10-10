"""Batch enrichment optimization for export operations.

This module provides optimized batch enrichment for scenarios where multiple
awards share the same solicitation (e.g., export operations). It identifies
unique (API source, solicitation ID) tuples, checks the cache, and fetches
missing solicitations efficiently to minimize redundant API calls.

The batch optimizer deduplicates solicitation requests and updates all awards
sharing the same solicitation atomically, significantly improving performance
for large export batches.

Typical usage:
    from sbir_cet_classifier.features.batch_enrichment import BatchEnrichmentOptimizer
    from sbir_cet_classifier.common.schemas import Award

    optimizer = BatchEnrichmentOptimizer()
    enriched_awards = optimizer.enrich_batch(awards)

    print(f"Enriched {len(enriched_awards)} awards with {optimizer.get_stats()}")
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from sbir_cet_classifier.common.schemas import Award
from sbir_cet_classifier.features.enrichment import (
    AGENCY_TO_API_SOURCE,
    EnrichedAward,
    EnrichmentOrchestrator,
)
from sbir_cet_classifier.models.enrichment_metrics import EnrichmentMetrics

logger = logging.getLogger(__name__)


@dataclass
class BatchEnrichmentStats:
    """Statistics for batch enrichment operation."""

    total_awards: int
    """Total number of awards in batch."""

    unique_solicitations: int
    """Number of unique solicitation identifiers."""

    cache_hits: int
    """Number of solicitations found in cache."""

    api_calls: int
    """Number of API calls made."""

    enriched_count: int
    """Number of awards successfully enriched."""

    failed_count: int
    """Number of awards that failed enrichment."""

    @property
    def deduplication_ratio(self) -> float:
        """Calculate deduplication efficiency ratio.

        Returns ratio of unique solicitations to total awards.
        Lower is better (more deduplication).
        """
        if self.total_awards == 0:
            return 0.0
        return self.unique_solicitations / self.total_awards


class BatchEnrichmentOptimizer:
    """Optimizes enrichment for batches of awards.

    Analyzes award batches to identify unique solicitations, deduplicates
    requests, and efficiently enriches all awards sharing the same solicitation.
    Especially beneficial for export operations where many awards may share
    solicitations.

    Attributes:
        orchestrator: Underlying enrichment orchestrator
        metrics: Enrichment telemetry tracker
    """

    def __init__(
        self,
        *,
        orchestrator: EnrichmentOrchestrator | None = None,
        metrics: EnrichmentMetrics | None = None,
    ) -> None:
        """Initialize batch enrichment optimizer.

        Args:
            orchestrator: Optional enrichment orchestrator (creates new if not provided)
            metrics: Optional metrics tracker (creates new if not provided)
        """
        self.metrics = metrics if metrics else EnrichmentMetrics()
        self.orchestrator = (
            orchestrator if orchestrator else EnrichmentOrchestrator(metrics=self.metrics)
        )

        # Track stats for this batch
        self._stats = BatchEnrichmentStats(
            total_awards=0,
            unique_solicitations=0,
            cache_hits=0,
            api_calls=0,
            enriched_count=0,
            failed_count=0,
        )

        logger.info("Initialized batch enrichment optimizer")

    def __enter__(self) -> BatchEnrichmentOptimizer:
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - closes connections."""
        self.close()

    def close(self) -> None:
        """Close connections."""
        self.orchestrator.close()

    def enrich_batch(self, awards: list[Award]) -> list[EnrichedAward]:
        """Enrich a batch of awards with optimized solicitation fetching.

        Analyzes the batch to identify unique solicitations, deduplicates
        requests, and enriches all awards efficiently.

        Args:
            awards: List of awards to enrich

        Returns:
            List of enriched awards in same order as input

        Example:
            >>> optimizer = BatchEnrichmentOptimizer()
            >>> enriched_awards = optimizer.enrich_batch(awards)
            >>> stats = optimizer.get_stats()
            >>> print(f"Deduplication ratio: {stats.deduplication_ratio:.2%}")
        """
        if not awards:
            logger.info("Empty batch, nothing to enrich")
            return []

        self._stats.total_awards = len(awards)

        logger.info(
            "Starting batch enrichment",
            extra={"total_awards": len(awards)},
        )

        # Step 1: Group awards by (api_source, solicitation_id)
        solicitation_groups = self._group_by_solicitation(awards)

        self._stats.unique_solicitations = len(solicitation_groups)

        logger.info(
            "Identified unique solicitations",
            extra={
                "total_awards": len(awards),
                "unique_solicitations": self._stats.unique_solicitations,
                "deduplication_ratio": f"{self._stats.deduplication_ratio:.2%}",
            },
        )

        # Step 2: Enrich each unique solicitation (orchestrator handles caching)
        solicitation_results = {}

        for solicitation_key, group_awards in solicitation_groups.items():
            # Pick first award from group as representative
            representative = group_awards[0]

            # Enrich using orchestrator (which handles caching internally)
            enriched = self.orchestrator.enrich_award(representative)

            # Store result for all awards in this group
            solicitation_results[solicitation_key] = enriched

            # Update stats
            if enriched.enrichment_status == "enriched":
                self._stats.enriched_count += len(group_awards)
            else:
                self._stats.failed_count += len(group_awards)

        logger.info(
            "Batch enrichment complete",
            extra={
                "total_awards": self._stats.total_awards,
                "unique_solicitations": self._stats.unique_solicitations,
                "enriched_count": self._stats.enriched_count,
                "failed_count": self._stats.failed_count,
            },
        )

        # Step 3: Build enriched awards list in original order
        enriched_awards = []

        for award in awards:
            solicitation_key = self._get_solicitation_key(award)

            if solicitation_key and solicitation_key in solicitation_results:
                # Use cached enrichment result but with this award's data
                template = solicitation_results[solicitation_key]
                enriched = EnrichedAward(
                    award=award,  # Use original award
                    enrichment_status=template.enrichment_status,
                    solicitation_description=template.solicitation_description,
                    solicitation_keywords=template.solicitation_keywords,
                    api_source=template.api_source,
                    retrieved_at=template.retrieved_at,
                    failure_reason=template.failure_reason,
                )
            else:
                # No solicitation key available
                enriched = EnrichedAward(
                    award=award,
                    enrichment_status="not_attempted",
                    failure_reason="No solicitation identifier",
                )

            enriched_awards.append(enriched)

        return enriched_awards

    def _group_by_solicitation(
        self,
        awards: list[Award],
    ) -> dict[tuple[str, str], list[Award]]:
        """Group awards by (api_source, solicitation_id).

        Args:
            awards: List of awards to group

        Returns:
            Dictionary mapping (api_source, solicitation_id) to list of awards
        """
        groups: dict[tuple[str, str], list[Award]] = defaultdict(list)

        for award in awards:
            solicitation_key = self._get_solicitation_key(award)
            if solicitation_key:
                groups[solicitation_key].append(award)
            else:
                # No solicitation identifier - treat as unique
                unique_key = ("unknown", award.award_id)
                groups[unique_key].append(award)

        return groups

    def _get_solicitation_key(self, award: Award) -> tuple[str, str] | None:
        """Get (api_source, solicitation_id) key for award.

        Args:
            award: Award record

        Returns:
            Tuple of (api_source, solicitation_id) or None
        """
        # Determine API source
        api_source = self._determine_api_source(award)
        if not api_source:
            return None

        # Extract solicitation ID
        solicitation_id = self._extract_solicitation_id(award)
        if not solicitation_id:
            return None

        return (api_source, solicitation_id)

    def _determine_api_source(self, award: Award) -> str | None:
        """Determine API source for award (same logic as orchestrator)."""
        agency_upper = award.agency.upper().strip()

        if agency_upper in AGENCY_TO_API_SOURCE:
            return AGENCY_TO_API_SOURCE[agency_upper]

        for known_agency, api_source in AGENCY_TO_API_SOURCE.items():
            if known_agency in agency_upper or agency_upper in known_agency:
                return api_source

        return "grants.gov"  # Default fallback

    def _extract_solicitation_id(self, award: Award) -> str | None:
        """Extract solicitation ID from award (same logic as orchestrator)."""
        if hasattr(award, "topic_code") and award.topic_code and award.topic_code != "UNKNOWN":
            return award.topic_code

        if hasattr(award, "solicitation_id") and award.solicitation_id:
            return award.solicitation_id

        if hasattr(award, "program") and hasattr(award, "solicitation_year"):
            if award.program and award.solicitation_year:
                return f"{award.program}-{award.solicitation_year}"

        return None

    def get_stats(self) -> BatchEnrichmentStats:
        """Get batch enrichment statistics.

        Returns:
            BatchEnrichmentStats with performance metrics

        Example:
            >>> optimizer = BatchEnrichmentOptimizer()
            >>> enriched = optimizer.enrich_batch(awards)
            >>> stats = optimizer.get_stats()
            >>> print(f"Enriched {stats.enriched_count}/{stats.total_awards} awards")
            >>> print(f"Deduplication saved {stats.total_awards - stats.unique_solicitations} API calls")
        """
        return self._stats

    def flush_metrics(self):
        """Flush enrichment metrics to artifacts.

        Returns:
            Path to metrics file
        """
        return self.orchestrator.flush_metrics()
