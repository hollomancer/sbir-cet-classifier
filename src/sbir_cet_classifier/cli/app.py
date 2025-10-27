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

app = typer.Typer(help="SBIR CET applicability tooling")
app.add_typer(awards_app, name="awards")
app.add_typer(export_app, name="export")
app.add_typer(enrichment_app, name="enrich")
app.add_typer(config_app, name="config")


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
) -> None:
    """Run the classification experiment (baseline vs enriched) on a local awards file.

    This command calls `sbir_cet_classifier.data.classification.classify_with_enrichment`
    and optionally persists the baseline/enriched assessment DataFrames to the
    configured processed storage location.
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

    result = classify_with_enrichment(awards_path_p, sample_size=sample_size)
    metrics = result.get("metrics") or {}
    typer.echo("Classification complete. Metrics:")
    typer.echo(json.dumps(metrics, indent=2, default=str))

    if save_outputs:
        try:
            config = load_config()
            processed_dir = config.storage.processed
            # Determine a partition name (use year if detectable, otherwise 'manual')
            fiscal_year = "manual"
            name = awards_path_p.name.lower()
            # crude detection: look for 4-digit year
            import re

            m = re.search(r"(20\\d{2})", name)
            if m:
                fiscal_year = int(m.group(1))
            # Persist DataFrames to processed/<partition>/
            from sbir_cet_classifier.data.store import write_partition

            baseline_df = result.get("baseline")
            enriched_df = result.get("enriched")
            if baseline_df is not None and not baseline_df.empty:
                write_partition(
                    baseline_df, processed_dir, fiscal_year, filename="assessments_baseline.parquet"
                )
            if enriched_df is not None and not enriched_df.empty:
                write_partition(
                    enriched_df, processed_dir, fiscal_year, filename="assessments_enriched.parquet"
                )
            typer.echo(f"Saved assessment outputs to {processed_dir}/{fiscal_year}/")
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
