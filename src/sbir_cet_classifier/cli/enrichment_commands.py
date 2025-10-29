"""Compatibility shims for solicitation enrichment CLI tests.

Several unit tests import :mod:`sbir_cet_classifier.cli.enrichment_commands` and patch
objects on that module. The production code lives under
:mod:`sbir_cet_classifier.cli.commands.enrichment`, so this file re-exports the symbols
those tests expect while keeping the application logic in its canonical location.
"""

from __future__ import annotations

import asyncio

# Third-party dependencies re-exported for test patching.
import pandas as pd  # noqa: F401

from sbir_cet_classifier.cli.commands.enrichment import (
    app,
    enrich_batch_solicitations,
    enrich_solicitation,
    enrichment_status,
)
from sbir_cet_classifier.common.config import EnrichmentConfig  # noqa: F401
from sbir_cet_classifier.data.enrichment.batch_processor import SolicitationBatchProcessor  # noqa: F401
from sbir_cet_classifier.data.enrichment.sam_client import SAMClient  # noqa: F401
from sbir_cet_classifier.data.enrichment.solicitation_service import SolicitationService  # noqa: F401
from sbir_cet_classifier.data.storage import SolicitationStorage  # noqa: F401

__all__ = [
    "asyncio",
    "pd",
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
