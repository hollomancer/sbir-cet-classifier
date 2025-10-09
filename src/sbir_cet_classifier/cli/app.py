"""Typer CLI entry point for SBIR CET workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from sbir_cet_classifier.common.config import load_config
from sbir_cet_classifier.data.ingest import ingest_fiscal_year
from sbir_cet_classifier.api.router import get_summary_service
from sbir_cet_classifier.features.summary import SummaryFilters

app = typer.Typer(help="SBIR CET applicability tooling")


@app.command()
def refresh(
    fiscal_year_start: int = typer.Option(..., help="Inclusive fiscal year start."),
    fiscal_year_end: int = typer.Option(..., help="Inclusive fiscal year end."),
    source_url: Optional[str] = typer.Option(None, help="Override SBIR.gov archive URL."),
    incremental: bool = typer.Option(True, help="Process only the provided fiscal range."),
) -> None:
    """Trigger ingestion for one or more fiscal years."""

    config = load_config()
    typer.echo(f"Using storage directories: {config.storage}")
    for fiscal_year in range(fiscal_year_start, fiscal_year_end + 1):
        url = source_url or f"https://www.sbir.gov/sites/default/files/sbir_awards_FY{fiscal_year}.zip"
        typer.echo(f"Ingesting fiscal year {fiscal_year} from {url}")
        result = ingest_fiscal_year(fiscal_year, url, config=config)
        typer.echo(
            f"Processed fiscal year {result.fiscal_year}: {result.records_ingested} records, archive={result.raw_archive.name}"
        )
    if incremental:
        typer.echo("Incremental refresh complete")
    else:
        typer.echo("Full refresh complete")


@app.command()
def summary(
    fiscal_year_start: int = typer.Argument(...),
    fiscal_year_end: int = typer.Argument(...),
    agency: Optional[list[str]] = typer.Option(
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


@app.command()
def awards(
    fiscal_year: int = typer.Argument(..., help="Fiscal year to inspect."),
    award_id: Optional[str] = typer.Option(None, help="Specific award to show."),
) -> None:
    """Inspect award-level applicability details."""

    typer.echo(
        "Awards command stub. Detailed implementation will stream award records in later phases."
    )


@app.command("review-queue")
def review_queue(  # pragma: no cover - thin wrapper
    list_pending: bool = typer.Option(False, "--list", help="List pending items."),
    escalate: Optional[str] = typer.Option(None, help="Escalate item by queue ID."),
) -> None:
    """Interact with the manual review queue."""

    if list_pending:
        typer.echo("Listing pending queue items... (implementation pending)")
    elif escalate:
        typer.echo(f"Escalating queue item {escalate} (implementation pending)")
    else:
        typer.echo("Use --list or --escalate to interact with the review queue.")


@app.command()
def export(
    output: Path = typer.Option(Path("exports/output.csv"), help="Export destination path."),
    fiscal_year_start: int = typer.Option(...),
    fiscal_year_end: int = typer.Option(...),
) -> None:
    """Trigger export for the selected filters."""

    typer.echo(
        f"Export command stub - results will be written to {output}. Detailed export logic will be implemented later."
    )


def main() -> None:  # pragma: no cover
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
