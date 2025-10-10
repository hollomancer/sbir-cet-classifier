"""Export CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from sbir_cet_classifier.features.exporter import ExportFormat, ExportOrchestrator
from sbir_cet_classifier.features.summary import SummaryFilters

export_app = typer.Typer(help="Export commands for dataset sharing")


@export_app.command("create")
def create_export(
    fiscal_year_start: int = typer.Option(..., help="Start fiscal year"),
    fiscal_year_end: int = typer.Option(..., help="End fiscal year"),
    agency: list[str] | None = typer.Option(None, "--agency", help="Filter by agencies"),
    phase: list[str] | None = typer.Option(None, "--phase", help="Filter by phases"),
    format: str = typer.Option("csv", help="Export format: csv or parquet"),
    output: Path | None = typer.Option(None, "--output", help="Output file path"),
) -> None:
    """Create a new export job."""
    filters = SummaryFilters(
        fiscal_year_start=fiscal_year_start,
        fiscal_year_end=fiscal_year_end,
        agencies=tuple(agency or []),
        phases=tuple(phase or []),
    )

    export_format = ExportFormat(format.lower())

    # In production, this would load actual data
    # For now, create a stub export
    orchestrator = ExportOrchestrator()

    typer.echo(f"Creating export job with format: {export_format.value}")
    typer.echo(f"Filters: FY{fiscal_year_start}-{fiscal_year_end}, Agencies: {agency or 'All'}")

    # Stub: would call orchestrator.create_export() with actual data
    job_id = "stub-job-id"
    typer.echo(f"Export job created: {job_id}")
    typer.echo(f"Use 'export status --job-id {job_id}' to check progress")


@export_app.command("status")
def export_status(
    job_id: str = typer.Option(..., "--job-id", help="Export job ID"),
) -> None:
    """Check export job status."""
    orchestrator = ExportOrchestrator()

    try:
        job = orchestrator.get_job_status(job_id)
        typer.echo(json.dumps(job.to_dict(), indent=2))
    except KeyError:
        typer.echo(f"Export job not found: {job_id}", err=True)
        raise typer.Exit(code=1)


__all__ = ["export_app"]
