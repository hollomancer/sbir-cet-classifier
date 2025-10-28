"""Typer CLI entry point for SBIR CET workflows.

This module serves as the main entrypoint for the CLI application,
organizing commands into feature-based subcommands.
"""

from __future__ import annotations

import typer

from sbir_cet_classifier.cli.commands import (
    awards_app,
    classify_app,
    config_app,
    enrichment_app,
    export_app,
    ingest_app,
    review_queue_app,
    rules_app,
    summary_app,
)

app = typer.Typer(
    help="SBIR CET applicability classification and analysis tooling",
    no_args_is_help=True,
)

# Register command groups
app.add_typer(ingest_app, name="ingest", help="Data ingestion commands")
app.add_typer(classify_app, name="classify", help="Classification and assessment commands")
app.add_typer(summary_app, name="summary", help="Summary and reporting commands")
app.add_typer(review_queue_app, name="review-queue", help="Manual review queue commands")
app.add_typer(awards_app, name="awards", help="Award data management commands")
app.add_typer(enrichment_app, name="enrich", help="Data enrichment commands")
app.add_typer(export_app, name="export", help="Data export commands")
app.add_typer(config_app, name="config", help="Configuration management commands")
app.add_typer(rules_app, name="rules", help="Rule management commands")


def main() -> None:  # pragma: no cover
    """Main CLI entrypoint."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
