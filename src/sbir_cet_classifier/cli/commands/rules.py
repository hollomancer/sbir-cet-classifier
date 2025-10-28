"""Typer CLI commands for rule-based CET scoring.

This module exposes a `rules` subcommand group that lets you score free text
using the rule-based scorer (priors + keywords + context rules) backed by
`config/classification.yaml`.

Examples:
    # Score a text directly
    python -m sbir_cet_classifier.cli.app rules score \
        --text "This project develops quantum algorithms for cryptography" \
        --agency "Department of Energy" \
        --top-n 5

    # Score text from a file and output JSON
    python -m sbir_cet_classifier.cli.app rules score \
        --text-file path/to/abstract.txt \
        --json

    # Read from stdin
    echo "AI diagnostic platform..." | python -m sbir_cet_classifier.cli.app rules score --json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from sbir_cet_classifier.models.rules_scorer import RuleBasedScorer

app = typer.Typer(name="rules", help="Rule-based CET scoring utilities")


def _read_text(*, text: Optional[str], text_file: Optional[str]) -> str:
    """Resolve text input from CLI options or stdin."""
    if text and text.strip():
        return text

    if text_file:
        p = Path(text_file)
        if not p.exists():
            raise typer.BadParameter(f"Text file not found: {p}")
        return p.read_text(encoding="utf-8")

    # If piping is used, read stdin
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        if data and data.strip():
            return data

    raise typer.BadParameter(
        "No input text provided. Use --text, --text-file, or pipe content via stdin."
    )


@app.command("score")
def score(
    text: Optional[str] = typer.Option(
        None,
        "--text",
        "-t",
        help="Text to score. Alternatively use --text-file or pipe via stdin.",
    ),
    text_file: Optional[str] = typer.Option(
        None,
        "--text-file",
        "-f",
        help="Path to a file containing text to score.",
    ),
    agency: Optional[str] = typer.Option(
        None,
        "--agency",
        "-a",
        help='Agency name (e.g., "Department of Defense") to apply priors.',
    ),
    branch: Optional[str] = typer.Option(
        None,
        "--branch",
        "-b",
        help='Branch/Sub-agency (e.g., "Air Force") to apply priors.',
    ),
    top_n: int = typer.Option(
        5,
        "--top-n",
        "-n",
        min=1,
        help="Show the top N CET areas by rule-based score.",
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        help="Show all CET scores (sorted) instead of only top-N.",
    ),
    as_json: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON.",
    ),
) -> None:
    """Score text with the rule-based scorer and display the highest-scoring CET areas."""
    input_text = _read_text(text=text, text_file=text_file).strip()
    if not input_text:
        raise typer.BadParameter("Input text is empty after trimming.")

    scorer = RuleBasedScorer()

    if show_all:
        scores = scorer.score_text(input_text, agency=agency, branch=branch)
        # Sort descending
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        if as_json:
            payload = {
                "input": {
                    "agency": agency,
                    "branch": branch,
                    "top_n": None,
                    "all": True,
                },
                "results": [{"cet_id": k, "score": v} for k, v in ranked],
            }
            typer.echo(json.dumps(payload, indent=2))
        else:
            typer.echo("Rule-based scores (all CET areas):")
            for cet_id, score in ranked:
                typer.echo(f"- {cet_id}: {score:.1f}")
        return

    # Top-N view
    ranked = scorer.score_and_rank_top(input_text, agency=agency, branch=branch, top_n=top_n)
    if as_json:
        payload = {
            "input": {
                "agency": agency,
                "branch": branch,
                "top_n": top_n,
                "all": False,
            },
            "results": [{"cet_id": k, "score": v} for k, v in ranked],
        }
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(f"Top-{top_n} CET areas by rule-based score:")
        for cet_id, score in ranked:
            typer.echo(f"- {cet_id}: {score:.1f}")


__all__ = ["app"]
