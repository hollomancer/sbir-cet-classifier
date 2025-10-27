"""
Configuration CLI commands (e.g. `config validate`).

This module provides a small Typer subcommand group for validating and
inspecting the YAML configuration files used by the application.
"""

from __future__ import annotations

import typer

from sbir_cet_classifier.common.yaml_config import (
    load_taxonomy_config,
    load_classification_config,
    load_enrichment_config,
)

app = typer.Typer(help="Inspect and validate configuration files")


@app.command("validate")
def validate() -> None:
    """Validate YAML configuration files used by the application.

    This command mirrors the previous standalone `validate_config.py`
    script but is available under the package CLI as:

        python -m sbir_cet_classifier.cli.app config validate
    """
    typer.echo("Validating YAML configuration files...\n")

    # Taxonomy
    try:
        tax_config = load_taxonomy_config()
        typer.echo("✅ taxonomy.yaml")
        typer.echo(f"   Version: {getattr(tax_config, 'version', 'N/A')}")
        typer.echo(f"   Effective date: {getattr(tax_config, 'effective_date', 'N/A')}")
        categories = getattr(tax_config, "categories", None)
        typer.echo(f"   Categories: {len(categories) if categories is not None else 'N/A'}")
        if categories:
            sample = categories[0]
            typer.echo(
                f"   Sample: {getattr(sample, 'id', 'N/A')} - {getattr(sample, 'name', 'N/A')}"
            )
    except Exception as exc:  # pragma: no cover - surface errors to user
        typer.echo(f"❌ taxonomy.yaml: {exc}")
        raise typer.Exit(code=1) from exc

    # Classification
    try:
        clf_config = load_classification_config()
        typer.echo("\n✅ classification.yaml")
        # Defensive access to nested fields which may vary across schema versions
        try:
            ngrams = clf_config.vectorizer.ngram_range
        except Exception:
            ngrams = "N/A"
        try:
            stop_words_count = len(clf_config.stop_words)
        except Exception:
            stop_words_count = "N/A"
        try:
            bands = ", ".join(clf_config.scoring.bands.keys())
        except Exception:
            bands = "N/A"

        typer.echo(f"   Vectorizer: {ngrams} n-grams")
        typer.echo(f"   Stop words: {stop_words_count} terms")
        typer.echo(f"   Bands: {bands}")
    except Exception as exc:  # pragma: no cover - surface errors to user
        typer.echo(f"❌ classification.yaml: {exc}")
        raise typer.Exit(code=1) from exc

    # Enrichment
    try:
        enr_config = load_enrichment_config()
        typer.echo("\n✅ enrichment.yaml")
        typer.echo(f"   Version: {getattr(enr_config, 'version', 'N/A')}")
        try:
            topic_domains = getattr(enr_config, "topic_domains", {}) or {}
            agency_focus = getattr(enr_config, "agency_focus", {}) or {}
            sample_topics = list(topic_domains.keys())[:5]
        except Exception:
            topic_domains = {}
            agency_focus = {}
            sample_topics = []
        typer.echo(f"   Topic domains: {len(topic_domains)}")
        typer.echo(f"   Agencies: {len(agency_focus)}")
        typer.echo(f"   Sample topics: {', '.join(sample_topics) if sample_topics else 'N/A'}")
    except Exception as exc:  # pragma: no cover - surface errors to user
        typer.echo(f"❌ enrichment.yaml: {exc}")
        raise typer.Exit(code=1) from exc

    typer.echo("\n✅ All configuration files are valid!")


__all__ = ["app"]
