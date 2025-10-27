"""Typer CLI entry point for SBIR CET workflows."""

from __future__ import annotations

import json

import typer

from sbir_cet_classifier.api.router import get_summary_service
from sbir_cet_classifier.cli.awards import awards_app
from sbir_cet_classifier.cli.enrichment_commands import app as enrichment_app
from sbir_cet_classifier.cli.export import export_app
from sbir_cet_classifier.cli.config import app as config_app
from sbir_cet_classifier.common.config import load_config
from sbir_cet_classifier.data.ingest import ingest_fiscal_year
from sbir_cet_classifier.features.summary import SummaryFilters
from sbir_cet_classifier.cli.rules import app as rules_app

app = typer.Typer(help="SBIR CET applicability tooling")
app.add_typer(awards_app, name="awards")
app.add_typer(export_app, name="export")
app.add_typer(enrichment_app, name="enrich")
app.add_typer(config_app, name="config")
app.add_typer(rules_app, name="rules")


@app.command()
def refresh(
    fiscal_year_start: int = typer.Option(..., help="Inclusive fiscal year start."),
    fiscal_year_end: int = typer.Option(..., help="Inclusive fiscal year end."),
    source_url: str | None = typer.Option(None, help="Override SBIR.gov archive URL."),
    incremental: bool = typer.Option(True, help="Process only the provided fiscal range."),
) -> None:
    """Trigger ingestion for one or more fiscal years."""

    config = load_config()
    typer.echo(f"Using storage directories: {config.storage}")
    for fiscal_year in range(fiscal_year_start, fiscal_year_end + 1):
        url = (
            source_url
            or f"https://www.sbir.gov/sites/default/files/sbir_awards_FY{fiscal_year}.zip"
        )
        typer.echo(f"Ingesting fiscal year {fiscal_year} from {url}")
        result = ingest_fiscal_year(fiscal_year, url, config=config)
        typer.echo(
            f"Processed fiscal year {result.fiscal_year}: "
            f"{result.records_ingested} records, "
            f"archive={result.raw_archive.name}"
        )
    if incremental:
        typer.echo("Incremental refresh complete")
    else:
        typer.echo("Full refresh complete")


@app.command("ingest")
def ingest(
    fiscal_year: int = typer.Argument(..., help="Fiscal year to ingest."),
    source_url: str | None = typer.Option(None, help="Override SBIR.gov archive URL."),
) -> None:
    """Ingest a single fiscal year (wrapper around ingest_fiscal_year).

    This command provides a lightweight compatibility wrapper similar to the
    previous top-level `ingest_awards.py` script but delegates to the
    package ingestion utility `ingest_fiscal_year`.
    """
    config = load_config()
    typer.echo(f"Using storage directories: {config.storage}")

    url = source_url or f"https://www.sbir.gov/sites/default/files/sbir_awards_FY{fiscal_year}.zip"
    typer.echo(f"Ingesting fiscal year {fiscal_year} from {url}")

    result = ingest_fiscal_year(fiscal_year, url, config=config)
    typer.echo(
        f"Processed fiscal year {result.fiscal_year}: "
        f"{result.records_ingested} records, "
        f"archive={result.raw_archive.name}"
    )


@app.command("classify")
def classify(
    awards_path: str = typer.Option(
        ..., "--awards-path", "-p", help="Path to awards CSV for classification"
    ),
    sample_size: int = typer.Option(
        100, "--sample-size", "-n", help="Maximum number of awards to use"
    ),
    save_outputs: bool = typer.Option(
        True, "--save/--no-save", help="Save assessment outputs to processed storage"
    ),
    rule_score: bool = typer.Option(
        False, "--rule-score/--no-rule-score", help="Include rule-based score column"
    ),
    hybrid_score: bool = typer.Option(
        False, "--hybrid-score/--no-hybrid-score", help="Include hybrid blended score"
    ),
    hybrid_weight: float = typer.Option(
        0.5, "--hybrid-weight", help="Hybrid weight for rule score (0..1). 0=ML only, 1=rule only"
    ),
) -> None:
    """Run the classification experiment (baseline vs enriched) on a local awards file.

    This command calls `sbir_cet_classifier.data.classification.classify_with_enrichment`
    and optionally persists the baseline/enriched assessment DataFrames to the
    configured processed storage location.

    Options:
    - --rule-score: include a rule_score column derived from RuleBasedScorer
    - --hybrid-score: include a hybrid_score that blends ML and rule scores
    - --hybrid-weight: weight for the rule component in the hybrid (0..1)
    """
    from pathlib import Path
    import pandas as pd

    typer.echo(f"Running classification on {awards_path} (sample_size={sample_size})")
    try:
        from sbir_cet_classifier.data.classification import classify_with_enrichment
    except Exception as exc:  # pragma: no cover - defensive
        typer.echo(f"Classifier unavailable: {exc}")
        raise typer.Exit(code=1) from exc

    awards_path_p = Path(awards_path)
    if not awards_path_p.exists():
        typer.echo(f"Path not found: {awards_path_p}")
        raise typer.Exit(code=1)

    result = classify_with_enrichment(
        awards_path_p,
        sample_size=sample_size,
        include_rule_score=rule_score,
        include_hybrid_score=hybrid_score,
        hybrid_weight=hybrid_weight,
    )
    metrics = result.get("metrics") or {}
    typer.echo("Classification complete. Metrics:")
    typer.echo(json.dumps(metrics, indent=2, default=str))

    if save_outputs:
        try:
            config = load_config()
            artifacts_root = config.storage.artifacts / "classifications"
            # Determine a partition name (use year if detectable, otherwise 'manual')
            fiscal_year = "manual"
            name = awards_path_p.name.lower()
            # crude detection: look for 4-digit year
            import re

            m = re.search(r"(20\d{2})", name)
            if m:
                fiscal_year = int(m.group(1))
            # Persist DataFrames to artifacts/classifications/<partition>/
            from sbir_cet_classifier.data.store import write_partition

            baseline_df = result.get("baseline")
            enriched_df = result.get("enriched")
            # Write assessment outputs
            if baseline_df is not None and not baseline_df.empty:
                write_partition(
                    baseline_df,
                    artifacts_root,
                    fiscal_year,
                    filename="assessments_baseline.parquet",
                )
            if enriched_df is not None and not enriched_df.empty:
                write_partition(
                    enriched_df,
                    artifacts_root,
                    fiscal_year,
                    filename="assessments_enriched.parquet",
                )
            # Write a manifest with run metadata alongside outputs
            try:
                from datetime import datetime, timezone
                import subprocess

                output_dir = artifacts_root / str(fiscal_year)
                metrics = result.get("metrics") or {}
                # Try to capture current git commit; fall back to 'unknown'
                try:
                    git_commit = subprocess.run(
                        ["git", "rev-parse", "HEAD"],
                        capture_output=True,
                        text=True,
                        check=True,
                    ).stdout.strip()
                except Exception:
                    git_commit = "unknown"

                # Compute optional rule/hybrid row counts
                baseline_rule_score_rows = (
                    int(baseline_df["rule_score"].notna().sum())
                    if (baseline_df is not None and "rule_score" in baseline_df.columns)
                    else 0
                )
                enriched_rule_score_rows = (
                    int(enriched_df["rule_score"].notna().sum())
                    if (enriched_df is not None and "rule_score" in enriched_df.columns)
                    else 0
                )
                baseline_hybrid_score_rows = (
                    int(baseline_df["hybrid_score"].notna().sum())
                    if (baseline_df is not None and "hybrid_score" in baseline_df.columns)
                    else 0
                )
                enriched_hybrid_score_rows = (
                    int(enriched_df["hybrid_score"].notna().sum())
                    if (enriched_df is not None and "hybrid_score" in enriched_df.columns)
                    else 0
                )

                manifest = {
                    "command": "classify",
                    "awards_path": str(awards_path_p),
                    "sample_size": int(sample_size),
                    "save_outputs": bool(save_outputs),
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "git_commit": git_commit,
                    "artifacts_dir": str(output_dir),
                    "baseline_rows": int(len(baseline_df)) if baseline_df is not None else 0,
                    "enriched_rows": int(len(enriched_df)) if enriched_df is not None else 0,
                    "rule_score_enabled": bool(rule_score),
                    "hybrid_score_enabled": bool(hybrid_score),
                    "hybrid_weight": float(hybrid_weight),
                    "baseline_rule_score_rows": baseline_rule_score_rows,
                    "enriched_rule_score_rows": enriched_rule_score_rows,
                    "baseline_hybrid_score_rows": baseline_hybrid_score_rows,
                    "enriched_hybrid_score_rows": enriched_hybrid_score_rows,
                    "metrics": metrics,
                }
                manifest_path = output_dir / "manifest.json"
                with manifest_path.open("w", encoding="utf-8") as fh:
                    json.dump(manifest, fh, indent=2)
                typer.echo(f"Saved assessment outputs and manifest to {output_dir}/")
            except Exception as exc:
                typer.echo(f"Could not write manifest: {exc}")
                typer.echo(f"Saved assessment outputs to {artifacts_root}/{fiscal_year}/")
        except Exception as exc:
            typer.echo(f"Could not save outputs: {exc}")


@app.command()
def summary(
    fiscal_year_start: int = typer.Argument(...),
    fiscal_year_end: int = typer.Argument(...),
    agency: list[str] | None = typer.Option(
        None,
        "--agency",
        help="Filter by agency; pass multiple flags for multi-select.",
    ),
) -> None:
    """Display CET summary metrics for the requested filters."""

    try:
        service = get_summary_service()
    except Exception as exc:  # pragma: no cover - defensive
        typer.echo(f"Summary service unavailable: {exc}")
        raise typer.Exit(code=1) from exc

    filters = SummaryFilters(
        fiscal_year_start=fiscal_year_start,
        fiscal_year_end=fiscal_year_end,
        agencies=tuple(agency or []),
    )
    result = service.summarize(filters).as_dict()
    typer.echo(json.dumps(result, indent=2))


@app.command("review-queue")
def review_queue(  # pragma: no cover - thin wrapper
    list_pending: bool = typer.Option(False, "--list", help="List pending items."),
    escalate: str | None = typer.Option(None, help="Escalate item by queue ID."),
) -> None:
    """Interact with the manual review queue."""

    if list_pending:
        typer.echo("Listing pending queue items... (implementation pending)")
    elif escalate:
        typer.echo(f"Escalating queue item {escalate} (implementation pending)")
    else:
        typer.echo("Use --list or --escalate to interact with the review queue.")


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
