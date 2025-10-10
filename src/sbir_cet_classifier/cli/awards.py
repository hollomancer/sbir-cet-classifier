"""Awards CLI commands for drill-down workflows."""

from __future__ import annotations

import json

import typer

from sbir_cet_classifier.api.router import get_awards_service
from sbir_cet_classifier.features.awards import AwardsFilters

awards_app = typer.Typer(help="Award-level drill-down commands")


@awards_app.command("list")
def list_awards(
    fiscal_year_start: int = typer.Option(..., help="Start fiscal year"),
    fiscal_year_end: int = typer.Option(..., help="End fiscal year"),
    agency: list[str] | None = typer.Option(None, "--agency", help="Filter by agency"),
    phase: list[str] | None = typer.Option(None, "--phase", help="Filter by phase"),
    cet_area: list[str] | None = typer.Option(None, "--cet-area", help="Filter by CET area"),
    state: str | None = typer.Option(None, "--state", help="Filter by firm state"),
    page: int = typer.Option(1, help="Page number"),
    page_size: int = typer.Option(25, help="Records per page"),
) -> None:
    """List awards with CET applicability details."""
    try:
        service = get_awards_service()
    except Exception as exc:  # pragma: no cover
        typer.echo(f"Awards service unavailable: {exc}")
        raise typer.Exit(code=1) from exc

    filters = AwardsFilters(
        fiscal_year_start=fiscal_year_start,
        fiscal_year_end=fiscal_year_end,
        agencies=tuple(agency or []),
        phases=tuple(phase or []),
        cet_areas=tuple(cet_area or []),
        location_states=tuple([state]) if state else (),
        page=page,
        page_size=page_size,
    )

    response = service.list_awards(filters)
    typer.echo(json.dumps(response.as_dict(), indent=2))


@awards_app.command("show")
def show_award_detail(
    award_id: str = typer.Option(..., "--award-id", help="Award ID to retrieve"),
) -> None:
    """Show detailed award information with assessment history."""
    try:
        service = get_awards_service()
    except Exception as exc:  # pragma: no cover
        typer.echo(f"Awards service unavailable: {exc}")
        raise typer.Exit(code=1) from exc

    try:
        detail = service.get_award_detail(award_id)
        typer.echo(json.dumps(detail.as_dict(), indent=2))
    except KeyError:
        typer.echo(f"Award not found: {award_id}", err=True)
        raise typer.Exit(code=1)


@awards_app.command("cet-detail")
def show_cet_detail(
    cet_id: str = typer.Option(..., "--cet-id", help="CET ID to retrieve"),
    fiscal_year_start: int = typer.Option(..., help="Start fiscal year"),
    fiscal_year_end: int = typer.Option(..., help="End fiscal year"),
    agency: list[str] | None = typer.Option(None, "--agency", help="Filter by agency"),
    phase: list[str] | None = typer.Option(None, "--phase", help="Filter by phase"),
) -> None:
    """Show CET area detail with gap analytics."""
    try:
        service = get_awards_service()
    except Exception as exc:  # pragma: no cover
        typer.echo(f"Awards service unavailable: {exc}")
        raise typer.Exit(code=1) from exc

    filters = AwardsFilters(
        fiscal_year_start=fiscal_year_start,
        fiscal_year_end=fiscal_year_end,
        agencies=tuple(agency or []),
        phases=tuple(phase or []),
        page=1,
        page_size=10,
    )

    try:
        detail = service.get_cet_detail(cet_id, filters)
        typer.echo(json.dumps(detail.as_dict(), indent=2))
    except KeyError:
        typer.echo(f"CET area not found: {cet_id}", err=True)
        raise typer.Exit(code=1)


__all__ = ["awards_app"]
