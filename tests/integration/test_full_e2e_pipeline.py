#!/usr/bin/env python3
"""
Integration: full end-to-end pipeline smoke test (ingest -> enrich -> classify -> export).

This test is intentionally small and deterministic: it writes a minimal bootstrap-compatible
CSV, runs the local classification flow (which uses fallback enrichment), and then runs the
export orchestrator to produce CSV and Parquet artifacts.

Marking as integration; it can be included in CI as a slow/integration test.
"""

import json
from datetime import timezone
from pathlib import Path

import pandas as pd
import pytest

from sbir_cet_classifier.features.exporter import (
    ExportOrchestrator,
    ExportFormat,
    ExportStatus,
)
from sbir_cet_classifier.features.summary import SummaryFilters
from sbir_cet_classifier.data.classification import classify_with_enrichment


def _make_sample_awards_csv(tmp_path: Path) -> Path:
    """Create a minimal, valid awards CSV used to simulate ingestion."""
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
            "agency": "Department of Defense",
            "sub_agency": "Army",
            "topic_code": "A-04",
            "abstract": "Advanced materials for extreme environments and high temperature applications.",
            "keywords": "materials; extreme environments",
            "phase": "I",
            "firm_name": "MaterialsTech",
            "firm_city": "Austin",
            "firm_state": "TX",
            "award_amount": 150000,
            "award_date": "2023-03-15",
            "program": "Phase I",
        },
        {
            "award_id": "A5",
            "agency": "National Aeronautics and Space Administration",
            "sub_agency": "",
            "topic_code": "NASA-05",
            "abstract": "Space propulsion systems using advanced chemical and electric thrusters.",
            "keywords": "space; propulsion; thrusters",
            "phase": "II",
            "firm_name": "SpaceProp",
            "firm_city": "Houston",
            "firm_state": "TX",
            "award_amount": 750000,
            "award_date": "2023-07-01",
            "program": "Phase II",
        },
        {
            "award_id": "A6",
            "agency": "Department of Defense",
            "sub_agency": "Air Force",
            "topic_code": "AF-06",
            "abstract": "Cybersecurity solutions for critical infrastructure protection.",
            "keywords": "cybersecurity; infrastructure",
            "phase": "I",
            "firm_name": "CyberDefense",
            "firm_city": "Arlington",
            "firm_state": "VA",
            "award_amount": 150000,
            "award_date": "2023-04-20",
            "program": "Phase I",
        },
        {
            "award_id": "A7",
            "agency": "Department of Energy",
            "sub_agency": "",
            "topic_code": "DOE-07",
            "abstract": "Novel battery technologies for grid-scale energy storage.",
            "keywords": "battery; energy storage",
            "phase": "I",
            "firm_name": "EnergyStore",
            "firm_city": "Denver",
            "firm_state": "CO",
            "award_amount": 150000,
            "award_date": "2023-08-10",
            "program": "Phase I",
        },
        {
            "award_id": "A8",
            "agency": "Department of Defense",
            "sub_agency": "Navy",
            "topic_code": "N-08",
            "abstract": "Autonomous underwater vehicles for ocean surveillance.",
            "keywords": "autonomous; underwater; surveillance",
            "phase": "II",
            "firm_name": "OceanTech",
            "firm_city": "San Diego",
            "firm_state": "CA",
            "award_amount": 900000,
            "award_date": "2022-11-05",
            "program": "Phase II",
        },
    ]
    df = pd.DataFrame(rows)
    csv_path = tmp_path / "awards_sample.csv"
    df.to_csv(csv_path, index=False)
    return csv_path


@pytest.mark.integration
def test_full_pipeline_ingest_enrich_classify_export(tmp_path: Path):
    """
    End-to-end smoke test that performs a reproducible local pipeline:
    - ingest (simulated via writing a bootstrap-compatible CSV)
    - enrichment (fallback enrichment applied during classification)
    - classification (train small ApplicabilityModel and predict)
    - export (CSV/Parquet) using ExportOrchestrator
    """
    # 1) Ingest (simulated) - create sample awards CSV
    csv_path = _make_sample_awards_csv(tmp_path)

    # 2) Classify (this will perform enrichment via fallback and train small models)
    result = classify_with_enrichment(
        awards_path=csv_path,
        sample_size=8,
        include_rule_score=True,
        include_hybrid_score=True,
        hybrid_weight=0.3,
    )

    assert isinstance(result, dict)
    baseline_df = result.get("baseline")
    enriched_df = result.get("enriched")
    metrics = result.get("metrics") or {}

    # Basic assertions about classification outputs
    assert baseline_df is not None and not baseline_df.empty
    assert enriched_df is not None and not enriched_df.empty

    # Ensure rule/hybrid columns present in outputs (we requested them)
    assert "rule_score" in baseline_df.columns
    assert "hybrid_score" in baseline_df.columns
    assert "rule_score" in enriched_df.columns
    assert "hybrid_score" in enriched_df.columns

    # 3) Prepare DataFrames for export step
    # Build awards_df from the original CSV (simulate persisted awards)
    awards_df = pd.read_csv(csv_path, parse_dates=["award_date"])
    # Ensure fiscal_year exists for exporter convenience
    if "fiscal_year" not in awards_df.columns and "award_date" in awards_df.columns:
        awards_df["fiscal_year"] = pd.to_datetime(awards_df["award_date"]).dt.year

    # Prepare assessments_df to match exporter expectations:
    assessments_df = enriched_df.copy()
    # Rename primary_cet -> primary_cet_id if necessary
    if "primary_cet" in assessments_df.columns and "primary_cet_id" not in assessments_df.columns:
        assessments_df = assessments_df.rename(columns={"primary_cet": "primary_cet_id"})
    # Add missing columns with reasonable defaults
    if "taxonomy_version" not in assessments_df.columns:
        assessments_df["taxonomy_version"] = "TEST-TAX-1"
    if "supporting_cet_ids" not in assessments_df.columns:
        assessments_df["supporting_cet_ids"] = [[] for _ in range(len(assessments_df))]
    if "assessed_at" not in assessments_df.columns:
        assessments_df["assessed_at"] = pd.Timestamp.now(tz=timezone.utc)

    # 4) Export: create exports and verify artifacts
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()

    orchestrator = ExportOrchestrator(exports_dir)

    filters = SummaryFilters(
        fiscal_year_start=2022,
        fiscal_year_end=2024,
        agencies=(),
        phases=(),
        cet_areas=(),
        location_states=(),
    )

    # Create CSV export
    job_csv = orchestrator.create_export(
        filters=filters,
        format=ExportFormat.CSV,
        awards_df=awards_df,
        assessments_df=assessments_df,
        taxonomy_df=pd.DataFrame([{"cet_id": "ai", "name": "Artificial Intelligence"}]),
    )

    assert job_csv.status == ExportStatus.COMPLETE
    csv_path_out = exports_dir / f"{job_csv.job_id}.csv"
    assert csv_path_out.exists()

    df_csv = pd.read_csv(csv_path_out, comment="#")
    # There should be at least one exported row for non-controlled award(s)
    assert "award_id" in df_csv.columns
    assert len(df_csv) >= 1

    # Create Parquet export
    job_parquet = orchestrator.create_export(
        filters=filters,
        format=ExportFormat.PARQUET,
        awards_df=awards_df,
        assessments_df=assessments_df,
        taxonomy_df=pd.DataFrame([{"cet_id": "ai", "name": "Artificial Intelligence"}]),
    )
    assert job_parquet.status == ExportStatus.COMPLETE
    parquet_path_out = exports_dir / f"{job_parquet.job_id}.parquet"
    assert parquet_path_out.exists()

    df_parquet = pd.read_parquet(parquet_path_out)
    assert "award_id" in df_parquet.columns
    assert len(df_parquet) >= 1

    # Verify that an export run telemetry entry was logged (if exporter writes telemetry)
    from sbir_cet_classifier.common.config import load_config

    config = load_config()
    telemetry_path = config.artifacts_dir / "export_runs.json"
    if telemetry_path.exists():
        payload = json.loads(telemetry_path.read_text(encoding="utf-8"))
        assert "export_runs" in payload
        # Latest run should have a job_id we can match to one of the created jobs
        latest = payload["export_runs"][-1]
        assert "job_id" in latest

    # Basic metrics sanity checks
    assert isinstance(metrics, dict)
    assert "sample_size" in metrics or "train_size" in metrics
