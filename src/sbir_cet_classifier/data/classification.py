#!/usr/bin/env python3
"""
Classification utilities.

This module provides a reusable `classify_with_enrichment` helper that was
previously implemented as a top-level script. It uses the package's
bootstrap loader, enrichment fallback, and the applicability model to train
and evaluate a small experiment comparing plain award text vs. enriched
text (e.g., solicitation/context enrichment).

Public API:
- classify_with_enrichment(awards_path: Path, sample_size: int = 100, include_rule_score: bool = False, include_hybrid_score: bool = False, hybrid_weight: float = 0.5) -> dict

The returned dictionary contains:
- "baseline": pd.DataFrame of baseline predictions
- "enriched": pd.DataFrame of enriched predictions
- "score_improvement": float (enriched.mean - baseline.mean)
- "high_conf_improvement": int (delta in number of 'High' classifications)
- "metrics": dict with summary statistics
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict

import pandas as pd

from sbir_cet_classifier.data.bootstrap import load_bootstrap_csv
from sbir_cet_classifier.features.fallback_enrichment import enrich_with_fallback
from sbir_cet_classifier.models.applicability import ApplicabilityModel, TrainingExample
from sbir_cet_classifier.models.rules_scorer import RuleBasedScorer


def classify_with_enrichment(
    awards_path: Path,
    sample_size: int = 100,
    include_rule_score: bool = False,
    include_hybrid_score: bool = False,
    hybrid_weight: float = 0.5,
) -> Dict[str, Any]:
    """
    Run a small classification experiment comparing baseline vs enriched text.

    Args:
        awards_path: Path to a CSV (or a path recognized by `load_bootstrap_csv`)
                     that contains award records for bootstrapping.
        sample_size: Maximum number of awards to load and use for the experiment.

    Returns:
        A dictionary with pandas DataFrames for 'baseline' and 'enriched'
        predictions and a few summary metrics.
    """
    print("=== Classification with Enrichment ===\n")
    print(f"Loading awards from {awards_path}...")

    # Load awards using existing bootstrap utility which returns a lightweight
    # container with `.awards` sequence of Award objects.
    result = load_bootstrap_csv(awards_path)
    awards = result.awards[:sample_size]
    print(f"Loaded {len(awards)} awards\n")

    if not awards:
        raise ValueError(f"No awards loaded from {awards_path}")

    # Split train/test (small experiment)
    train_size = min(50, len(awards) // 2)
    test_size = len(awards) - train_size

    print(f"Training set: {train_size} awards")
    print(f"Test set: {test_size} awards\n")

    # Mock CET labels for demonstration. In a real experiment these should be
    # sourced from labeled data.
    cet_labels = [
        "ai",
        "quantum",
        "biotech",
        "energy",
        "materials",
        "cyber",
        "space",
        "manufacturing",
    ]

    # Build training examples (baseline)
    print("=== Training Model WITHOUT Enrichment ===")
    train_examples_baseline: list[TrainingExample] = []
    for i, award in enumerate(awards[:train_size]):
        text = f"{award.abstract or ''} {' '.join(award.keywords or [])}"
        cet_id = cet_labels[i % len(cet_labels)]
        train_examples_baseline.append(TrainingExample(award.award_id, text, cet_id))

    start = time.time()
    model_baseline = ApplicabilityModel()
    model_baseline.fit(train_examples_baseline)
    train_time_baseline = time.time() - start
    print(f"Training time: {train_time_baseline:.2f}s\n")

    # Build training examples (enriched)
    print("=== Training Model WITH Enrichment ===")
    train_examples_enriched: list[TrainingExample] = []
    for i, award in enumerate(awards[:train_size]):
        text = f"{award.abstract or ''} {' '.join(award.keywords or [])}"
        enriched_text = enrich_with_fallback(award, text)
        cet_id = cet_labels[i % len(cet_labels)]
        train_examples_enriched.append(TrainingExample(award.award_id, enriched_text, cet_id))

    start = time.time()
    model_enriched = ApplicabilityModel()
    model_enriched.fit(train_examples_enriched)
    train_time_enriched = time.time() - start
    print(f"Training time: {train_time_enriched:.2f}s\n")

    # Clamp hybrid weight to [0,1] for safety
    try:
        hybrid_weight = float(hybrid_weight)
    except Exception:
        hybrid_weight = 0.5
    if hybrid_weight < 0.0:
        hybrid_weight = 0.0
    elif hybrid_weight > 1.0:
        hybrid_weight = 1.0

    # Initialize rule-based scorer (optional) and evaluate on held-out set
    scorer = RuleBasedScorer() if (include_rule_score or include_hybrid_score) else None
    print("=== Testing on Held-Out Awards ===\n")

    results_baseline: list[dict] = []
    results_enriched: list[dict] = []

    for award in awards[train_size:]:
        text = f"{award.abstract or ''} {' '.join(award.keywords or [])}"

        pred_baseline = model_baseline.predict(award.award_id, text)
        row_b = {
            "award_id": award.award_id,
            "primary_cet": pred_baseline.primary_cet_id,
            "score": pred_baseline.primary_score,
            "classification": pred_baseline.classification,
            "text_length": len(text),
        }
        if scorer is not None:
            rs_all = scorer.score_text(
                text,
                agency=getattr(award, "agency", None),
                branch=getattr(award, "sub_agency", None),
            )
            rule_score_b = float(rs_all.get(pred_baseline.primary_cet_id, 0.0))
            if include_rule_score:
                row_b["rule_score"] = rule_score_b
            if include_hybrid_score:
                row_b["hybrid_score"] = float(
                    (1.0 - hybrid_weight) * pred_baseline.primary_score
                    + hybrid_weight * rule_score_b
                )
        results_baseline.append(row_b)

        enriched_text = enrich_with_fallback(award, text)
        pred_enriched = model_enriched.predict(award.award_id, enriched_text)
        row_e = {
            "award_id": award.award_id,
            "primary_cet": pred_enriched.primary_cet_id,
            "score": pred_enriched.primary_score,
            "classification": pred_enriched.classification,
            "text_length": len(enriched_text),
        }
        if scorer is not None:
            rs_all_e = scorer.score_text(
                enriched_text,
                agency=getattr(award, "agency", None),
                branch=getattr(award, "sub_agency", None),
            )
            rule_score_e = float(rs_all_e.get(pred_enriched.primary_cet_id, 0.0))
            if include_rule_score:
                row_e["rule_score"] = rule_score_e
            if include_hybrid_score:
                row_e["hybrid_score"] = float(
                    (1.0 - hybrid_weight) * pred_enriched.primary_score
                    + hybrid_weight * rule_score_e
                )
        results_enriched.append(row_e)

    df_baseline = pd.DataFrame(results_baseline)
    df_enriched = pd.DataFrame(results_enriched)

    # Print summary
    def _summary(df: pd.DataFrame, label: str) -> None:
        print(f"{label}:")
        if df.empty:
            print("  (no records)\n")
            return
        mean_score = df["score"].mean()
        high_count = (df["classification"] == "High").sum()
        med_count = (df["classification"] == "Medium").sum()
        low_count = (df["classification"] == "Low").sum()
        avg_len = df["text_length"].mean()
        print(f"  Avg score: {mean_score:.1f}")
        print(f"  High confidence: {high_count} ({high_count/len(df)*100:.1f}%)")
        print(f"  Medium confidence: {med_count} ({med_count/len(df)*100:.1f}%)")
        print(f"  Low confidence: {low_count} ({low_count/len(df)*100:.1f}%)")
        print(f"  Avg text length: {avg_len:.0f} chars\n")

    print("=== Results Comparison ===\n")
    _summary(df_baseline, "Baseline (Award-Only)")
    _summary(df_enriched, "Enriched (Award + Solicitation Context)")

    # Compute simple impact metrics
    score_improvement = df_enriched["score"].mean() - df_baseline["score"].mean()
    if (
        include_hybrid_score
        and "hybrid_score" in df_baseline.columns
        and "hybrid_score" in df_enriched.columns
    ):
        hybrid_score_improvement = (
            df_enriched["hybrid_score"].mean() - df_baseline["hybrid_score"].mean()
        )
    else:
        hybrid_score_improvement = None
    high_conf_improvement = (df_enriched["classification"] == "High").sum() - (
        df_baseline["classification"] == "High"
    ).sum()
    text_increase = df_enriched["text_length"].mean() - df_baseline["text_length"].mean()

    print("=== Impact Summary ===\n")
    print(f"Score improvement: {score_improvement:+.1f} points")
    if hybrid_score_improvement is not None:
        print(f"Hybrid score improvement: {hybrid_score_improvement:+.1f} points")
    print(f"High confidence increase: {high_conf_improvement:+d} awards")
    print(
        f"Text enrichment: {text_increase:+.0f} chars avg ({text_increase/df_baseline['text_length'].mean()*100:+.1f}%)"
    )
    print()

    print("=== Sample Predictions ===\n")
    for i in range(min(5, len(df_baseline))):
        b = df_baseline.iloc[i]
        e = df_enriched.iloc[i]
        print(f"{i+1}. Award {b['award_id']}")
        print(f"   Baseline: {b['primary_cet']} ({b['score']:.0f}) - {b['classification']}")
        print(f"   Enriched: {e['primary_cet']} ({e['score']:.0f}) - {e['classification']}")
        if b["primary_cet"] != e["primary_cet"]:
            print("   ⚠️  CET changed!")
        print()

    print("✅ Classification with enrichment complete")

    metrics = {
        "train_time_baseline_s": train_time_baseline,
        "train_time_enriched_s": train_time_enriched,
        "sample_size": len(awards),
        "train_size": train_size,
        "test_size": test_size,
        "score_improvement": float(score_improvement),
        "hybrid_score_improvement": float(hybrid_score_improvement)
        if hybrid_score_improvement is not None
        else None,
        "high_conf_improvement": int(high_conf_improvement),
        "text_increase": float(text_increase),
    }

    return {
        "baseline": df_baseline,
        "enriched": df_enriched,
        "score_improvement": float(score_improvement),
        "high_conf_improvement": int(high_conf_improvement),
        "metrics": metrics,
    }


__all__ = ["classify_with_enrichment"]
