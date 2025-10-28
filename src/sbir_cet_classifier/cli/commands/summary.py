"""Summary commands for displaying CET metrics and statistics."""

from __future__ import annotations

import typer

from sbir_cet_classifier.api.router import get_summary_service
from sbir_cet_classifier.cli.formatters import echo_error, echo_json
from sbir_cet_classifier.features.summary import SummaryFilters

app = typer.Typer(help="Summary and reporting commands")


@app.command()
def show(
    fiscal_year_start: int = typer.Argument(..., help="Start fiscal year (inclusive)"),
    fiscal_year_end: int = typer.Argument(..., help="End fiscal year (inclusive)"),
    agency: list[str] | None = typer.Option(
        None,
        "--agency",
        help="Filter by agency; pass multiple flags for multi-select.",
    ),
) -> None:
    """Display CET summary metrics for the requested filters.

    Shows aggregated statistics including:
    - Total awards and awardees
    - CET-applicable counts and percentages
    - Breakdowns by agency (if filtered)
    - Fiscal year ranges

    Examples:
        # Show summary for FY 2020-2023
        sbir summary show 2020 2023

        # Filter by specific agencies
        sbir summary show 2020 2023 --agency DOD --agency NASA
    """
    try:
        service = get_summary_service()
    except Exception as exc:  # pragma: no cover - defensive
        echo_error(f"Summary service unavailable: {exc}")
        raise typer.Exit(code=1) from exc

    filters = SummaryFilters(
        fiscal_year_start=fiscal_year_start,
        fiscal_year_end=fiscal_year_end,
        agencies=tuple(agency or []),
    )

    result = service.summarize(filters).as_dict()
    echo_json(result)
