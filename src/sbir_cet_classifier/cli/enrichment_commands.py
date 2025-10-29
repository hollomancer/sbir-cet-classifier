"""Compatibility shims for solicitation enrichment CLI tests.

Several unit tests import :mod:`sbir_cet_classifier.cli.enrichment_commands` and patch
objects on that module. The production code lives under
:mod:`sbir_cet_classifier.cli.commands.enrichment`, so this file re-exports the symbols
those tests expect while keeping the application logic in its canonical location.

This module also injects a patchable asyncio reference into the enrichment module
to allow tests to mock asyncio.run() calls.
"""

from __future__ import annotations

import asyncio

# Third-party dependencies re-exported for test patching.
import pandas as pd  # noqa: F401

from sbir_cet_classifier.common.config import EnrichmentConfig  # noqa: F401
from sbir_cet_classifier.data.enrichment.batch_processor import SolicitationBatchProcessor  # noqa: F401
from sbir_cet_classifier.data.enrichment.sam_client import SAMClient  # noqa: F401
from sbir_cet_classifier.data.enrichment.solicitation_service import SolicitationService  # noqa: F401
from sbir_cet_classifier.data.storage import SolicitationStorage  # noqa: F401

# Import the enrichment module and inject our asyncio reference
# This must happen BEFORE we import the command functions
import sbir_cet_classifier.cli.commands.enrichment as _enrichment_module

# Inject our asyncio into the enrichment module so patches to this module's asyncio
# will affect the enrichment commands
_enrichment_module.asyncio = asyncio

# Now import the CLI commands - they will use the asyncio we injected above
from sbir_cet_classifier.cli.commands.enrichment import (  # noqa: E402
    app,
    enrich_batch_solicitations,
    enrich_solicitation,
    enrichment_status,
)

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
