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

from sbir_cet_classifier.common.classification_config import load_classification_rules

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


@app.command("show")
def show(
    section: str = typer.Option(
        "all",
        "--section",
        "-s",
        help="Which section to show: taxonomy|classification|enrichment|rules|cet_keywords|priors|context_rules|all",
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="Limit items shown for long lists"),
) -> None:
    """Show configuration sections and rule summaries for quick inspection."""
    sec = (section or "all").strip().lower()

    # Taxonomy section
    if sec in ("taxonomy", "all"):
        try:
            tax_config = load_taxonomy_config()
            categories = getattr(tax_config, "categories", []) or []
            typer.echo("🧭 taxonomy.yaml")
            typer.echo(f"   Version: {getattr(tax_config, 'version', 'N/A')}")
            typer.echo(f"   Effective date: {getattr(tax_config, 'effective_date', 'N/A')}")
            typer.echo(f"   Categories: {len(categories)}")
            if categories:
                typer.echo("   Sample categories:")
                for cat in categories[:limit]:
                    cat_id = getattr(cat, "id", "N/A")
                    cat_name = getattr(cat, "name", "N/A")
                    typer.echo(f"     - {cat_id}: {cat_name}")
        except Exception as exc:
            typer.echo(f"❌ taxonomy.yaml: {exc}")

    # Classification (hyperparameters) section
    if sec in ("classification", "all"):
        try:
            clf_config = load_classification_config()
            typer.echo("\n⚙️  classification.yaml")
            try:
                ngrams = clf_config.vectorizer.ngram_range
            except Exception:
                ngrams = "N/A"
            try:
                stop_words_count = len(clf_config.stop_words)
            except Exception:
                stop_words_count = "N/A"
            try:
                bands = list(clf_config.scoring.bands.keys())
            except Exception:
                bands = []
            typer.echo(f"   Vectorizer n-grams: {ngrams}")
            typer.echo(f"   Stop words: {stop_words_count}")
            typer.echo(f"   Bands: {', '.join(bands) if bands else 'N/A'}")
        except Exception as exc:
            typer.echo(f"❌ classification.yaml: {exc}")

    # Enrichment section
    if sec in ("enrichment", "all"):
        try:
            enr_config = load_enrichment_config()
            topic_domains = getattr(enr_config, "topic_domains", {}) or {}
            agency_focus = getattr(enr_config, "agency_focus", {}) or {}
            typer.echo("\n🧩 enrichment.yaml")
            typer.echo(f"   Version: {getattr(enr_config, 'version', 'N/A')}")
            typer.echo(f"   Topic domains: {len(topic_domains)}")
            typer.echo(f"   Agencies: {len(agency_focus)}")
            if topic_domains:
                typer.echo("   Sample topic domains:")
                for k in list(topic_domains.keys())[:limit]:
                    typer.echo(f"     - {k}")
        except Exception as exc:
            typer.echo(f"❌ enrichment.yaml: {exc}")

    # Rules (priors, keywords, context rules) section
    if sec in ("rules", "cet_keywords", "priors", "context_rules", "all"):
        try:
            rules = load_classification_rules()
            # Overall rules summary
            if sec in ("rules", "all"):
                typer.echo("\n🧠 classification rules (from classification.yaml)")
                typer.echo(f"   CET keyword sets: {len(rules.cet_keywords)}")
                typer.echo(f"   Agency priors: {len(rules.agency_priors)} agencies")
                typer.echo(f"   Branch priors: {len(rules.branch_priors)} branches")
                typer.echo(f"   Context rules: {len(rules.context_rules)} CET areas")

            # CET keywords detail
            if sec in ("cet_keywords", "all"):
                cet_ids = list(rules.cet_keywords.keys())
                typer.echo("\n   CET keywords:")
                for cet_id in cet_ids[:limit]:
                    bucket = rules.cet_keywords.get(cet_id)
                    core = getattr(bucket, "core", []) if bucket is not None else []
                    related = getattr(bucket, "related", []) if bucket is not None else []
                    typer.echo(f"     - {cet_id}: core={len(core)}, related={len(related)}")
                    if core:
                        typer.echo(f"         core sample: {', '.join(core[:min(3, len(core))])}")

            # Priors detail
            if sec in ("priors", "all"):
                typer.echo("\n   Agency priors:")
                for agency in list(rules.agency_priors.keys())[:limit]:
                    typer.echo(f"     - {agency}: {len(rules.agency_priors[agency])} CET boosts")
                if rules.branch_priors:
                    typer.echo("   Branch priors:")
                    for branch in list(rules.branch_priors.keys())[:limit]:
                        typer.echo(
                            f"     - {branch}: {len(rules.branch_priors[branch])} CET boosts"
                        )

            # Context rules detail
            if sec in ("context_rules", "all"):
                typer.echo("\n   Context rules:")
                for cet_id, rule_list in list(rules.context_rules.items())[:limit]:
                    typer.echo(f"     - {cet_id}: {len(rule_list)} rule(s)")
                    if rule_list:
                        r = rule_list[0]
                        req = getattr(r, "required_keywords", None) or []
                        boost = getattr(r, "boost", 0)
                        typer.echo(f"         sample: requires={req}, boost={boost}")
        except Exception as exc:
            typer.echo(f"❌ classification rules: {exc}")


__all__ = ["app"]
