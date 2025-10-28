"""CLI command modules for SBIR CET Classifier.

This package organizes CLI commands into feature-based modules:
- ingest: Data ingestion commands
- classify: Classification and assessment commands
- summary: Summary and reporting commands
- review_queue: Manual review queue commands
- awards: Award data management commands
- enrichment: Data enrichment commands
- export: Data export commands
- config: Configuration management commands
- rules: Rule management commands
"""

from __future__ import annotations

from sbir_cet_classifier.cli.commands.awards import awards_app
from sbir_cet_classifier.cli.commands.classify import app as classify_app
from sbir_cet_classifier.cli.commands.config import app as config_app
from sbir_cet_classifier.cli.commands.enrichment import app as enrichment_app
from sbir_cet_classifier.cli.commands.export import export_app
from sbir_cet_classifier.cli.commands.ingest import app as ingest_app
from sbir_cet_classifier.cli.commands.review_queue import app as review_queue_app
from sbir_cet_classifier.cli.commands.rules import app as rules_app
from sbir_cet_classifier.cli.commands.summary import app as summary_app

__all__ = [
    "awards_app",
    "classify_app",
    "config_app",
    "enrichment_app",
    "export_app",
    "ingest_app",
    "review_queue_app",
    "rules_app",
    "summary_app",
]
