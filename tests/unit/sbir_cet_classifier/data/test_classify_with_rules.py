import io
from pathlib import Path

import pandas as pd
import pytest

from sbir_cet_classifier.data.classification import classify_with_enrichment


def _write_awards_csv(tmp_path: Path) -> Path:
    # Build a minimal yet valid awards CSV that passes bootstrap + Award schema
    # Required by bootstrap: award_id, agency, abstract, award_amount
    # Additional required by Award schema (filled here): topic_code, phase, firm_name,
    # firm_city, firm_state, award_date, keywords (validator can handle str), program, sub_agency
    rows = [
        {
            "award_id": "A1",
            "agency": "Department of Defense",
            "sub_agency": "Air Force",
            "topic_code": "AF-01",
            "abstract": "Research on hypersonics propulsion and materials.",
            "keywords": "hypersonics; propulsion",
            "phase": "I",
            "firm_name": "Acme Aero",
            "firm_city": "San Diego",
            "firm_state": "CA",
            "award_amount": 150000,
            "award_date": "2023-05-01",
            "program": "Phase I",
        },
        {
            "award_id": "A2",
            "agency": "Department of Energy",
            "sub_agency": "",
            "topic_code": "Q-02",
            "abstract": "Quantum computing algorithms for simulation.",
            "keywords": "quantum computing; algorithm",
            "phase": "I",
            "firm_name": "QuantumCorp",
            "firm_city": "Boston",
            "firm_state": "MA",
            "award_amount": 150000,
            "award_date": "2023-06-15",
            "program": "Phase I",
        },
        {
            "award_id": "A3",
            "agency": "Department of Defense",
            "sub_agency": "Navy",
            "topic_code": "N-03",
            "abstract": "AI diagnostic system for medical devices.",
            "keywords": "AI; diagnostic",
            "phase": "II",
            "firm_name": "MedAI",
            "firm_city": "Seattle",
            "firm_state": "WA",
            "award_amount": 1000000,
            "award_date": "2022-02-10",
            "program": "Phase II",
        },
        {
            "award_id": "A4",
            "agency": "National Science Foundation",
            "sub_agency": "",
            "topic_code": "M-04",
            "abstract": "Advanced materials for aerospace composites.",
            "keywords": "materials; composites",
            "phase": "I",
            "firm_name": "AeroMat",
            "firm_city": "Denver",
            "firm_state": "CO",
            "award_amount": 150000,
            "award_date": "2023-03-20",
            "program": "Phase I",
        },
    ]
    df = pd.DataFrame(rows)
    path = tmp_path / "awards.csv"
    df.to_csv(path, index=False)
    return path


def test_rule_and_hybrid_columns_and_metrics_present(tmp_path: Path):
    awards_csv = _write_awards_csv(tmp_path)

    result = classify_with_enrichment(
        awards_path=awards_csv,
        sample_size=4,
        include_rule_score=True,
        include_hybrid_score=True,
        hybrid_weight=0.3,
    )

    # Basic structure
    assert "baseline" in result and "enriched" in result and "metrics" in result
    baseline = result["baseline"]
    enriched = result["enriched"]
    metrics = result["metrics"]

    # DataFrames should not be empty and must contain new columns
    assert isinstance(baseline, pd.DataFrame) and isinstance(enriched, pd.DataFrame)
    assert not baseline.empty and not enriched.empty

    for col in ("rule_score", "hybrid_score"):
        assert col in baseline.columns
        assert col in enriched.columns

    # Hybrid score equals blend of ML score and rule score for at least one row (baseline)
    # hybrid = (1-w) * score + w * rule_score
    w = 0.3
    row = baseline.iloc[0]
    assert "score" in row and "rule_score" in row and "hybrid_score" in row
    expected = (1.0 - w) * float(row["score"]) + w * float(row["rule_score"])
    assert abs(float(row["hybrid_score"]) - expected) <= 1e-6

    # Metrics should include hybrid_score_improvement when hybrid columns are present
    assert "hybrid_score_improvement" in metrics
    # It should be a float or at least not None
    assert metrics["hybrid_score_improvement"] is None or isinstance(
        metrics["hybrid_score_improvement"], (float, int)
    )


def test_no_rule_or_hybrid_columns_when_flags_disabled(tmp_path: Path):
    awards_csv = _write_awards_csv(tmp_path)

    result = classify_with_enrichment(
        awards_path=awards_csv,
        sample_size=4,
        include_rule_score=False,
        include_hybrid_score=False,
    )

    baseline = result["baseline"]
    enriched = result["enriched"]
    metrics = result["metrics"]

    # Columns should not be present when flags are disabled
    for col in ("rule_score", "hybrid_score"):
        assert col not in baseline.columns
        assert col not in enriched.columns

    # Metrics hybrid improvement should be None when hybrid was not computed
    assert metrics.get("hybrid_score_improvement") is None
