"""Classification commands for running CET applicability assessments."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import typer

from sbir_cet_classifier.cli.formatters import (
    echo_error,
    echo_info,
    echo_json,
    echo_metrics,
    echo_success,
)
from sbir_cet_classifier.common.config import load_config

app = typer.Typer(help="Classification and assessment commands")


@app.command()
def run(
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
    echo_info(f"Running classification on {awards_path} (sample_size={sample_size})")

    try:
        from sbir_cet_classifier.data.classification import classify_with_enrichment
    except Exception as exc:  # pragma: no cover - defensive
        echo_error(f"Classifier unavailable: {exc}")
        raise typer.Exit(code=1) from exc

    awards_path_p = Path(awards_path)
    if not awards_path_p.exists():
        echo_error(f"Path not found: {awards_path_p}")
        raise typer.Exit(code=1)

    result = classify_with_enrichment(
        awards_path_p,
        sample_size=sample_size,
        include_rule_score=rule_score,
        include_hybrid_score=hybrid_score,
        hybrid_weight=hybrid_weight,
    )

    metrics = result.get("metrics") or {}
    echo_metrics(metrics, title="Classification Complete")

    if save_outputs:
        try:
            config = load_config()
            artifacts_root = config.storage.artifacts / "classifications"

            # Determine a partition name (use year if detectable, otherwise 'manual')
            fiscal_year = "manual"
            name = awards_path_p.name.lower()
            # crude detection: look for 4-digit year
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
                import subprocess

                output_dir = artifacts_root / str(fiscal_year)

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
                echo_success(f"Saved assessment outputs and manifest to {output_dir}/")
            except Exception as exc:
                echo_error(f"Could not write manifest: {exc}")
                echo_info(f"Saved assessment outputs to {artifacts_root}/{fiscal_year}/")
        except Exception as exc:
            echo_error(f"Could not save outputs: {exc}")
