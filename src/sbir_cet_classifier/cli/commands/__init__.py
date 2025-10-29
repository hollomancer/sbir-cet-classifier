"""CLI command modules for SBIR CET Classifier.

This package organizes CLI commands into feature-based modules:
- ingest: Data ingestion commands
- classify: Classification and assessment commands
- summary: Summary and reporting commands
- review_queue: Manual review queue commands
- awards: Award data management commands
- award_enrichment: Award enrichment commands
- enrichment: Data enrichment commands (solicitations)
- export: Data export commands
- config: Configuration management commands
- rules: Rule management commands
"""

from __future__ import annotations

from sbir_cet_classifier.cli.commands.awards import awards_app
from sbir_cet_classifier.cli.commands.award_enrichment import (
    app as award_enrichment_app,
    enrich_single,
    enrich_batch,
    enrichment_status,
    enrich_awardee,
    enrich_program,
    enrich_modifications,
    enrich_solicitation,
)
from sbir_cet_classifier.cli.commands.classify import app as classify_app
from sbir_cet_classifier.cli.commands.config import app as config_app
from sbir_cet_classifier.cli.commands.enrichment import (
    app as enrichment_app,
    enrich_solicitation as _enrich_solicitation_cmd,
    enrich_batch_solicitations as _enrich_batch_cmd,
    enrichment_status as _enrichment_status_cmd,
)
from sbir_cet_classifier.cli.commands.export import export_app
from sbir_cet_classifier.cli.commands.ingest import app as ingest_app
from sbir_cet_classifier.cli.commands.review_queue import app as review_queue_app
from sbir_cet_classifier.cli.commands.rules import app as rules_app
from sbir_cet_classifier.cli.commands.summary import app as summary_app

# Batch enrichment service export for test patching
try:
    from sbir_cet_classifier.data.enrichment.batch_enricher import (  # type: ignore
        BatchEnrichmentService,
    )
except Exception:

    class BatchEnrichmentService:  # pragma: no cover - test patch target
        def __init__(self, *args, **kwargs):
            pass

        def enrich_batch(self, *args, **kwargs):
            return {}

        def resume_batch(self, *args, **kwargs):
            return {}


# Expose services and utilities so tests can patch these symbols on this module path
from sbir_cet_classifier.data.enrichment.enrichers import EnrichmentService  # for patching
from sbir_cet_classifier.data.enrichment.status import EnrichmentStatusTracker  # for patching
from sbir_cet_classifier.data.enrichment.models import AwardeeEnrichmentService  # for patching

# Optional services: provide lightweight shims if not present in the codebase
try:
    from sbir_cet_classifier.data.enrichment.models import (  # type: ignore
        ProgramOfficeEnrichmentService,
        SolicitationEnrichmentService,
        ModificationsEnrichmentService,
    )
except Exception:

    class ProgramOfficeEnrichmentService:  # pragma: no cover - test patch target
        def __init__(self, *args, **kwargs): ...
        def enrich_program_office(self, *args, **kwargs):
            return {}

    class SolicitationEnrichmentService:  # pragma: no cover - test patch target
        def __init__(self, *args, **kwargs): ...
        def enrich_solicitation(self, *args, **kwargs):
            return {}

    class ModificationsEnrichmentService:  # pragma: no cover - test patch target
        def __init__(self, *args, **kwargs): ...
        def enrich_modifications(self, *args, **kwargs):
            return {}


# Re-export load_config for tests that patch configuration loading
from sbir_cet_classifier.common.config import load_config as load_config  # re-export


# Note: enrich_awardee, enrich_program, and enrich_modifications are now
# imported from award_enrichment module above


__all__ = [
    "awards_app",
    "award_enrichment_app",
    "classify_app",
    "config_app",
    "enrichment_app",
    "export_app",
    "ingest_app",
    "review_queue_app",
    "rules_app",
    "summary_app",
    # Exposed services and helpers for patching in tests
    "EnrichmentService",
    "EnrichmentStatusTracker",
    "AwardeeEnrichmentService",
    "ProgramOfficeEnrichmentService",
    "SolicitationEnrichmentService",
    "ModificationsEnrichmentService",
    "BatchEnrichmentService",
    "load_config",
    # Award enrichment commands expected by tests
    "enrich_single",
    "enrich_batch",
    "enrichment_status",
    "enrich_awardee",
    "enrich_program",
    "enrich_modifications",
    "enrich_solicitation",
]
