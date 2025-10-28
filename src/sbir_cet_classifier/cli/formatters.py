"""Shared output formatting utilities for CLI commands."""

from __future__ import annotations

import json
from typing import Any

import typer


def echo_json(data: dict[str, Any], indent: int = 2) -> None:
    """Format and echo JSON data to the console.

    Args:
        data: Dictionary to format as JSON
        indent: Number of spaces for indentation (default: 2)
    """
    typer.echo(json.dumps(data, indent=indent, default=str))


def echo_success(message: str) -> None:
    """Echo a success message in green.

    Args:
        message: Success message to display
    """
    typer.secho(message, fg=typer.colors.GREEN)


def echo_error(message: str) -> None:
    """Echo an error message in red.

    Args:
        message: Error message to display
    """
    typer.secho(message, fg=typer.colors.RED, err=True)


def echo_warning(message: str) -> None:
    """Echo a warning message in yellow.

    Args:
        message: Warning message to display
    """
    typer.secho(message, fg=typer.colors.YELLOW)


def echo_info(message: str) -> None:
    """Echo an informational message.

    Args:
        message: Info message to display
    """
    typer.echo(message)


def echo_result(label: str, value: Any) -> None:
    """Echo a labeled result value.

    Args:
        label: Label for the value
        value: Value to display
    """
    typer.echo(f"{label}: {value}")


def echo_metrics(metrics: dict[str, Any], title: str = "Metrics") -> None:
    """Format and display metrics as formatted JSON.

    Args:
        metrics: Dictionary of metrics to display
        title: Optional title to display before metrics
    """
    if title:
        typer.echo(f"\n{title}:")
    echo_json(metrics)


def format_progress(current: int, total: int, prefix: str = "") -> str:
    """Format a progress indicator string.

    Args:
        current: Current progress value
        total: Total/target value
        prefix: Optional prefix text

    Returns:
        Formatted progress string
    """
    percentage = (current / total * 100) if total > 0 else 0
    result = f"{current}/{total} ({percentage:.1f}%)"
    if prefix:
        result = f"{prefix} {result}"
    return result


def echo_table_row(*columns: str, separator: str = " | ") -> None:
    """Echo a simple table row.

    Args:
        columns: Column values to display
        separator: Separator between columns (default: " | ")
    """
    typer.echo(separator.join(str(col) for col in columns))


def echo_section_header(title: str, char: str = "=") -> None:
    """Echo a section header with underline.

    Args:
        title: Section title
        char: Character to use for underline (default: "=")
    """
    typer.echo(f"\n{title}")
    typer.echo(char * len(title))
