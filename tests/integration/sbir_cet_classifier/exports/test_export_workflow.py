"""Integration tests for export workflow."""

from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from sbir_cet_classifier.features.exporter import (
    ExportFormat,
    ExportOrchestrator,
    ExportStatus,
)
from sbir_cet_classifier.features.summary import SummaryFilters


@pytest.fixture
def temp_exports_dir(tmp_path):
    """Create temporary exports directory."""
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()
    return exports_dir


@pytest.fixture
def sample_awards_df():
    """Create sample awards DataFrame."""
    return pd.DataFrame([
        {
            "award_id": "AF-001-2023-001",
            "agency": "AF",
            "topic_code": "AF23-001",
            "abstract": "AI research",
            "award_amount": 150000,
            "award_date": date(2023, 1, 15),
            "firm_name": "Tech Inc",
            "firm_city": "Austin",
            "firm_state": "TX",
            "is_export_controlled": False,
        },
        {
            "award_id": "DOE-001-2023-001",
            "agency": "DOE",
            "topic_code": "DOE23-001",
            "abstract": "Energy storage",
            "award_amount": 200000,
            "award_date": date(2023, 2, 1),
            "firm_name": "Energy Co",
            "firm_city": "Boston",
            "firm_state": "MA",
            "is_export_controlled": True,  # Should be excluded
        },
    ])


@pytest.fixture
def sample_assessments_df():
    """Create sample assessments DataFrame."""
    return pd.DataFrame([
        {
            "award_id": "AF-001-2023-001",
            "taxonomy_version": "NSTC-2025Q1",
            "score": 85,
            "classification": "High",
            "primary_cet_id": "ai",
            "supporting_cet_ids": ["quantum", "biotech"],
            "assessed_at": datetime(2023, 3, 1),
        },
        {
            "award_id": "DOE-001-2023-001",
            "taxonomy_version": "NSTC-2025Q1",
            "score": 75,
            "classification": "High",
            "primary_cet_id": "energy",
            "supporting_cet_ids": [],
            "assessed_at": datetime(2023, 3, 2),
        },
    ])


@pytest.fixture
def sample_taxonomy_df():
    """Create sample taxonomy DataFrame."""
    return pd.DataFrame([
        {"cet_id": "ai", "name": "Artificial Intelligence"},
        {"cet_id": "quantum", "name": "Quantum Computing"},
        {"cet_id": "biotech", "name": "Biotechnology"},
        {"cet_id": "energy", "name": "Energy Storage"},
    ])


@pytest.fixture
def sample_filters():
    """Create sample filters."""
    return SummaryFilters(
        fiscal_year_start=2023,
        fiscal_year_end=2023,
        agencies=("AF", "DOE"),
        phases=(),
        cet_areas=(),
        location_states=(),
    )


class TestExportOrchestrator:
    """Test export orchestrator."""

    def test_create_csv_export(
        self,
        temp_exports_dir,
        sample_awards_df,
        sample_assessments_df,
        sample_taxonomy_df,
        sample_filters,
    ):
        """Test creating CSV export."""
        orchestrator = ExportOrchestrator(temp_exports_dir)

        job = orchestrator.create_export(
            filters=sample_filters,
            format=ExportFormat.CSV,
            awards_df=sample_awards_df,
            assessments_df=sample_assessments_df,
            taxonomy_df=sample_taxonomy_df,
        )

        assert job.status == ExportStatus.COMPLETE
        assert job.job_id is not None
        assert job.download_url is not None
        assert job.completed_at is not None

        # Verify export file exists
        export_path = temp_exports_dir / f"{job.job_id}.csv"
        assert export_path.exists()

        # Verify controlled award excluded
        df = pd.read_csv(export_path, comment="#")
        assert len(df) == 1  # Only non-controlled award
        assert df.iloc[0]["award_id"] == "AF-001-2023-001"

    def test_create_parquet_export(
        self,
        temp_exports_dir,
        sample_awards_df,
        sample_assessments_df,
        sample_taxonomy_df,
        sample_filters,
    ):
        """Test creating Parquet export."""
        orchestrator = ExportOrchestrator(temp_exports_dir)

        job = orchestrator.create_export(
            filters=sample_filters,
            format=ExportFormat.PARQUET,
            awards_df=sample_awards_df,
            assessments_df=sample_assessments_df,
            taxonomy_df=sample_taxonomy_df,
        )

        assert job.status == ExportStatus.COMPLETE

        # Verify export file exists
        export_path = temp_exports_dir / f"{job.job_id}.parquet"
        assert export_path.exists()

        # Verify data
        df = pd.read_parquet(export_path)
        assert len(df) == 1

    def test_get_job_status(
        self,
        temp_exports_dir,
        sample_awards_df,
        sample_assessments_df,
        sample_taxonomy_df,
        sample_filters,
    ):
        """Test retrieving job status."""
        orchestrator = ExportOrchestrator(temp_exports_dir)

        # Create job
        job = orchestrator.create_export(
            filters=sample_filters,
            format=ExportFormat.CSV,
            awards_df=sample_awards_df,
            assessments_df=sample_assessments_df,
            taxonomy_df=sample_taxonomy_df,
        )

        # Retrieve status
        retrieved_job = orchestrator.get_job_status(job.job_id)

        assert retrieved_job.job_id == job.job_id
        assert retrieved_job.status == ExportStatus.COMPLETE

    def test_get_nonexistent_job_raises(self, temp_exports_dir):
        """Test getting nonexistent job raises KeyError."""
        orchestrator = ExportOrchestrator(temp_exports_dir)

        with pytest.raises(KeyError, match="Export job not found"):
            orchestrator.get_job_status("nonexistent-job-id")

    def test_export_telemetry_logged(
        self,
        temp_exports_dir,
        sample_awards_df,
        sample_assessments_df,
        sample_taxonomy_df,
        sample_filters,
        tmp_path,
    ):
        """Test that export telemetry is logged."""
        from sbir_cet_classifier.common.config import load_config
        
        orchestrator = ExportOrchestrator(temp_exports_dir)

        # Get current telemetry count
        config = load_config()
        telemetry_path = config.artifacts_dir / "export_runs.json"
        
        initial_count = 0
        if telemetry_path.exists():
            import json
            telemetry = json.loads(telemetry_path.read_text())
            initial_count = len(telemetry.get("export_runs", []))

        orchestrator.create_export(
            filters=sample_filters,
            format=ExportFormat.CSV,
            awards_df=sample_awards_df,
            assessments_df=sample_assessments_df,
            taxonomy_df=sample_taxonomy_df,
        )

        # Verify telemetry file exists and has new entry
        assert telemetry_path.exists()

        # Verify telemetry content
        import json
        telemetry = json.loads(telemetry_path.read_text())
        assert "export_runs" in telemetry
        assert len(telemetry["export_runs"]) == initial_count + 1
        
        # Verify the latest entry has expected fields
        latest_run = telemetry["export_runs"][-1]
        assert "job_id" in latest_run
        assert "timestamp" in latest_run
        assert "record_count" in latest_run
        assert "controlled_excluded" in latest_run
        assert latest_run["controlled_excluded"] == 1

    def test_export_with_empty_dataframes(
        self,
        temp_exports_dir,
        sample_filters,
    ):
        """Test export with empty data."""
        orchestrator = ExportOrchestrator(temp_exports_dir)

        job = orchestrator.create_export(
            filters=sample_filters,
            format=ExportFormat.CSV,
            awards_df=pd.DataFrame(),
            assessments_df=pd.DataFrame(),
            taxonomy_df=pd.DataFrame(),
        )

        assert job.status == ExportStatus.COMPLETE

    def test_cet_weights_added(
        self,
        temp_exports_dir,
        sample_awards_df,
        sample_assessments_df,
        sample_taxonomy_df,
        sample_filters,
    ):
        """Test that CET weight columns are added."""
        orchestrator = ExportOrchestrator(temp_exports_dir)

        job = orchestrator.create_export(
            filters=sample_filters,
            format=ExportFormat.CSV,
            awards_df=sample_awards_df,
            assessments_df=sample_assessments_df,
            taxonomy_df=sample_taxonomy_df,
        )

        df = pd.read_csv(temp_exports_dir / f"{job.job_id}.csv", comment="#")

        # Verify weight columns exist
        assert "weight_ai" in df.columns
        assert "weight_quantum" in df.columns
        assert "weight_biotech" in df.columns
        assert "weight_energy" in df.columns

    def test_export_job_to_dict(
        self,
        temp_exports_dir,
        sample_awards_df,
        sample_assessments_df,
        sample_taxonomy_df,
        sample_filters,
    ):
        """Test ExportJob.to_dict() method."""
        orchestrator = ExportOrchestrator(temp_exports_dir)

        job = orchestrator.create_export(
            filters=sample_filters,
            format=ExportFormat.CSV,
            awards_df=sample_awards_df,
            assessments_df=sample_assessments_df,
            taxonomy_df=sample_taxonomy_df,
        )

        job_dict = job.to_dict()

        assert "jobId" in job_dict
        assert "status" in job_dict
        assert "submittedAt" in job_dict
        assert "completedAt" in job_dict
        assert "downloadUrl" in job_dict
        assert job_dict["status"] == "complete"
