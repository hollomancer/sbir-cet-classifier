from __future__ import annotations

import json
import zipfile
from datetime import UTC
from pathlib import Path

import pandas as pd

from sbir_cet_classifier.common.config import AppConfig, StoragePaths
from sbir_cet_classifier.data.ingest import (
    IngestionResult,
    ingest_fiscal_year,
    iter_awards_for_year,
)


def _write_test_archive(tmp_dir: Path) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    data = pd.DataFrame(
        [
            {
                "award_id": "AF123",
                "agency_code": "AF",
                "bureau_code": "AFRL",
                "topic_code": "AF-001",
                "abstract": "Hypersonic propulsion research",
                "keywords": "propulsion;hypersonic",
                "phase": "I",
                "firm": "Aero Labs",
                "firm_city": "Dayton",
                "firm_state": "OH",
                "award_amount": "150000",
                "award_year": "2023-06-01",
            },
            {
                "award_id": "AF123",
                "agency_code": "AF",
                "bureau_code": "AFRL",
                "topic_code": "AF-001",
                "abstract": "Hypersonic propulsion research - revised",
                "keywords": "propulsion;hypersonic",
                "phase": "I",
                "firm": "Aero Labs",
                "firm_city": "Dayton",
                "firm_state": "OH",
                "award_amount": "160000",
                "award_year": "2023-06-01",
            },
            {
                "award_id": "NAV456",
                "agency_code": "NAVY",
                "bureau_code": "ONR",
                "topic_code": "NAV-010",
                "abstract": "Undersea communications",
                "keywords": "communications;undersea",
                "phase": "II",
                "firm": "Blue Sea Tech",
                "firm_city": "San Diego",
                "firm_state": "CA",
                "award_amount": "900000",
                "award_year": "2023-09-15",
            },
        ]
    )

    csv_path = tmp_dir / "awards.csv"
    data.to_csv(csv_path, index=False)
    zip_path = tmp_dir / "sbir_awards_FY2023.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(csv_path, arcname="awards.csv")
    return zip_path


def _build_config(tmp_dir: Path) -> AppConfig:
    storage = StoragePaths(
        raw=tmp_dir / "raw",
        processed=tmp_dir / "processed",
        artifacts=tmp_dir / "artifacts",
    )
    for path in (storage.raw, storage.processed, storage.artifacts):
        path.mkdir(parents=True, exist_ok=True)
    return AppConfig(storage=storage)


def test_ingest_fiscal_year_processes_archive(tmp_path):
    config = _build_config(tmp_path)
    archive_path = _write_test_archive(config.storage.raw / "2023")

    result: IngestionResult = ingest_fiscal_year(
        fiscal_year=2023,
        source_url="https://example.com/sbir_awards_FY2023.zip",
        config=config,
        raw_archive=archive_path,
    )

    assert result.records_ingested == 2
    processed_parquet = config.storage.processed / "2023" / "awards.parquet"
    assert processed_parquet.exists()

    metadata_path = config.storage.artifacts / "2023-metadata.json"
    metadata = json.loads(metadata_path.read_text())
    assert metadata["records"] == 2
    assert metadata["source_archive"] == archive_path.name

    rows = list(iter_awards_for_year(2023, config=config))
    assert {row.award_id for row in rows} == {"AF123", "NAV456"}
    assert all(row.ingested_at.tzinfo == UTC for row in rows)
