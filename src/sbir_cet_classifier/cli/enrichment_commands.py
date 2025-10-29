"""Compatibility shim for solicitation enrichment CLI tests.

This module re-exports symbols from :mod:`sbir_cet_classifier.cli.commands.enrichment`
for backward compatibility with tests that import from this location.

New code should import directly from :mod:`sbir_cet_classifier.cli.commands.enrichment`.
"""

from __future__ import annotations

# Re-export CLI commands
from sbir_cet_classifier.cli.commands.enrichment import (
    app,
    enrich_batch_solicitations,
    enrich_solicitation,
    enrichment_status,
)

# Re-export dependencies for test compatibility
from sbir_cet_classifier.common.config import EnrichmentConfig
from sbir_cet_classifier.data.enrichment.batch_processor import (
    SolicitationBatchProcessor,
)
from sbir_cet_classifier.data.enrichment.sam_client import SAMClient
from sbir_cet_classifier.data.enrichment.solicitation_service import (
    SolicitationService,
)
from sbir_cet_classifier.data.storage import SolicitationStorage

__all__ = [
    # CLI entry points
    "app",
    "enrich_solicitation",
    "enrich_batch_solicitations",
    "enrichment_status",
    # Configuration and services
    "EnrichmentConfig",
    "SolicitationService",
    "SolicitationBatchProcessor",
    "SAMClient",
    "SolicitationStorage",
]
