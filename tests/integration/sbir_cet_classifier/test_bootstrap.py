from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from typer.testing import CliRunner

from sbir_cet_classifier.cli.app import app
from sbir_cet_classifier.common.config import AppConfig, StoragePaths
from sbir_cet_classifier.common.schemas import Award
from sbir_cet_classifier.data.store import read_partition, write_partition

runner = CliRunner()


def _build_config(tmp_path: Path) -> AppConfig:
    storage = StoragePaths(
        raw=tmp_path / "raw",
        processed=tmp_path / "processed",
        artifacts=tmp_path / "artifacts",
    )
    for path in (storage.raw, storage.processed, storage.artifacts):
        path.mkdir(parents=True, exist_ok=True)
    return AppConfig(storage=storage)


def test_award_schema_roundtrip(tmp_path):
    award = Award(
        award_id="AF123",
        agency="AF",
        sub_agency="AFRL",
        topic_code="AF-001",
        abstract="Hypersonic propulsion research",
        keywords=["hypersonic", "propulsion"],
        phase="I",
        firm_name="Aero Labs",
        firm_city="Dayton",
        firm_state="OH",
        award_amount=150000.0,
        award_date=datetime(2023, 6, 1).date(),
        source_version="sbir_awards_FY2023.zip",
        ingested_at=datetime.now(UTC),
    )
    assert award.agency == "AF"

    df = pd.DataFrame([award.model_dump()])
    write_partition(df, tmp_path, partition=2023, filename="awards.parquet")
    reloaded = read_partition(tmp_path, 2023, filename="awards.parquet")
    assert reloaded.iloc[0]["award_id"] == "AF123"


def test_cli_refresh_invokes_ingestion(monkeypatch, tmp_path):
    config = _build_config(tmp_path)
    calls: list[int] = []

    def fake_config():
        return config

    def fake_ingest(year: int, url: str, config, raw_archive=None):  # type: ignore[no-redef]
        calls.append(year)
        return type("Result", (), {
            "fiscal_year": year,
            "source_url": url,
            "raw_archive": Path(f"archive_{year}.zip"),
            "records_ingested": 10,
        })()

    monkeypatch.setattr("sbir_cet_classifier.cli.app.load_config", fake_config)
    monkeypatch.setattr("sbir_cet_classifier.cli.app.ingest_fiscal_year", fake_ingest)

    result = runner.invoke(
        app,
        [
            "refresh",
            "--fiscal-year-start",
            "2023",
            "--fiscal-year-end",
            "2024",
        ],
    )
    assert result.exit_code == 0
    assert calls == [2023, 2024]
