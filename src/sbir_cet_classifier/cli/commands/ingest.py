"""Ingestion commands for SBIR award data."""

from __future__ import annotations

import typer

from sbir_cet_classifier.common.config import load_config
from sbir_cet_classifier.data.ingest import ingest_fiscal_year
from sbir_cet_classifier.cli.formatters import echo_info, echo_result, echo_success

app = typer.Typer(help="Data ingestion commands")


@app.command()
def refresh(
    fiscal_year_start: int = typer.Option(..., help="Inclusive fiscal year start."),
    fiscal_year_end: int = typer.Option(..., help="Inclusive fiscal year end."),
    source_url: str | None = typer.Option(None, help="Override SBIR.gov archive URL."),
    incremental: bool = typer.Option(True, help="Process only the provided fiscal range."),
) -> None:
    """Trigger ingestion for one or more fiscal years."""

    config = load_config()
    echo_info(f"Using storage directories: {config.storage}")

    for fiscal_year in range(fiscal_year_start, fiscal_year_end + 1):
        url = (
            source_url
            or f"https://www.sbir.gov/sites/default/files/sbir_awards_FY{fiscal_year}.zip"
        )
        echo_info(f"Ingesting fiscal year {fiscal_year} from {url}")
        result = ingest_fiscal_year(fiscal_year, url, config=config)
        echo_info(
            f"Processed fiscal year {result.fiscal_year}: "
            f"{result.records_ingested} records, "
            f"archive={result.raw_archive.name}"
        )

    if incremental:
        echo_success("Incremental refresh complete")
    else:
        echo_success("Full refresh complete")


@app.command()
def single(
    fiscal_year: int = typer.Argument(..., help="Fiscal year to ingest."),
    source_url: str | None = typer.Option(None, help="Override SBIR.gov archive URL."),
) -> None:
    """Ingest a single fiscal year.

    This command provides a lightweight wrapper for ingesting a single fiscal year
    of SBIR award data.
    """
    config = load_config()
    echo_info(f"Using storage directories: {config.storage}")

    url = source_url or f"https://www.sbir.gov/sites/default/files/sbir_awards_FY{fiscal_year}.zip"
    echo_info(f"Ingesting fiscal year {fiscal_year} from {url}")

    result = ingest_fiscal_year(fiscal_year, url, config=config)
    echo_info(
        f"Processed fiscal year {result.fiscal_year}: "
        f"{result.records_ingested} records, "
        f"archive={result.raw_archive.name}"
    )
    echo_success(f"Ingestion complete: {result.records_ingested} records processed")
