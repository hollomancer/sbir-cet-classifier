"""Awards CLI commands for drill-down workflows."""

from __future__ import annotations

import json
from typing import Annotated

import typer

from sbir_cet_classifier.api.router import get_awards_service
from sbir_cet_classifier.features.awards import AwardsFilters

awards_app = typer.Typer(help="Award-level drill-down commands")


@awards_app.command("list")
def list_awards(
    fiscal_year_start: Annotated[int, typer.Option(help="Start fiscal year")],
    fiscal_year_end: Annotated[int, typer.Option(help="End fiscal year")],
    agency: Annotated[list[str] | None, typer.Option("--agency", help="Filter by agency")] = None,
    phase: Annotated[list[str] | None, typer.Option("--phase", help="Filter by phase")] = None,
    cet_area: Annotated[
        list[str] | None, typer.Option("--cet-area", help="Filter by CET area")
    ] = None,
    state: Annotated[str | None, typer.Option("--state", help="Filter by firm state")] = None,
    page: Annotated[int, typer.Option(help="Page number")] = 1,
    page_size: Annotated[int, typer.Option(help="Records per page")] = 25,
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
    award_id: Annotated[str, typer.Option("--award-id", help="Award ID to retrieve")],
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
    cet_id: Annotated[str, typer.Option("--cet-id", help="CET ID to retrieve")],
    fiscal_year_start: Annotated[int, typer.Option(help="Start fiscal year")],
    fiscal_year_end: Annotated[int, typer.Option(help="End fiscal year")],
    agency: Annotated[list[str] | None, typer.Option("--agency", help="Filter by agency")] = None,
    phase: Annotated[list[str] | None, typer.Option("--phase", help="Filter by phase")] = None,
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
