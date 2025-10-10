"""SBIR.gov ingestion pipeline utilities."""

from __future__ import annotations

import json
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pandas as pd

from sbir_cet_classifier.common.config import AppConfig, StoragePaths, load_config
from sbir_cet_classifier.common.schemas import Award
from sbir_cet_classifier.data.store import read_partition, write_partition

RAW_ARCHIVE_SUFFIX = "zip"
PROCESSED_FILENAME = "awards.parquet"
METADATA_FILENAME = "metadata.json"

REQUIRED_COLUMNS = {
    "award_id",
    "agency_code",
    "bureau_code",
    "topic_code",
    "abstract",
    "keywords",
    "phase",
    "firm",
    "firm_city",
    "firm_state",
    "award_amount",
    "award_year",
}


@dataclass(frozen=True)
class IngestionResult:
    """Outcome summary for a single ingestion run."""

    fiscal_year: int
    source_url: str
    raw_archive: Path
    extracted_csv: Path
    records_ingested: int


def download_archive(source_url: str, destination_dir: Path) -> Path:
    """Download the SBIR bulk archive and return the local path."""

    destination_dir.mkdir(parents=True, exist_ok=True)
    archive_name = source_url.split("/")[-1]
    archive_path = destination_dir / archive_name

    with httpx.stream("GET", source_url, timeout=60.0) as response:
        response.raise_for_status()
        with archive_path.open("wb") as archive_fh:
            for chunk in response.iter_bytes():
                archive_fh.write(chunk)
    return archive_path


def extract_archive(archive_path: Path, destination_dir: Path) -> Path:
    """Extract a ZIP archive to destination_dir and return the first CSV path."""

    destination_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(destination_dir)
    csv_files = list(destination_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {archive_path}")
    return csv_files[0]


def _normalise_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

    renamed = df.rename(
        columns={
            "agency_code": "agency",
            "bureau_code": "sub_agency",
            "firm": "firm_name",
            "award_year": "award_date",
        }
    ).copy()

    renamed["award_date"] = pd.to_datetime(renamed["award_date"], errors="coerce")
    renamed["keywords"] = renamed["keywords"].fillna("")
    renamed["abstract"] = renamed["abstract"].fillna("")
    renamed["sub_agency"] = renamed["sub_agency"].fillna("")

    renamed = renamed.drop_duplicates(subset=["award_id", "agency"], keep="last")
    return renamed


def _records_from_dataframe(df: pd.DataFrame, source_version: str, ingested_at: datetime) -> list[Award]:
    records: list[Award] = []
    for row in df.to_dict(orient="records"):
        award_date = row["award_date"]
        records.append(
            Award(
                award_id=row["award_id"],
                agency=row["agency"],
                sub_agency=row.get("sub_agency") or None,
                topic_code=row["topic_code"],
                abstract=row.get("abstract") or None,
                keywords=row.get("keywords", ""),
                phase=row["phase"],
                firm_name=row["firm_name"],
                firm_city=row["firm_city"],
                firm_state=row["firm_state"],
                award_amount=float(row["award_amount"] or 0),
                award_date=award_date.date() if hasattr(award_date, "date") else datetime.strptime(str(award_date), "%Y").date(),
                source_version=source_version,
                ingested_at=ingested_at,
            )
        )
    return records


def _write_metadata(metadata: dict, artifacts_dir: Path, fiscal_year: int) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = artifacts_dir / f"{fiscal_year}-{METADATA_FILENAME}"
    with metadata_path.open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, default=str)
    return metadata_path


def ingest_fiscal_year(
    fiscal_year: int,
    source_url: str,
    *,
    config: AppConfig | None = None,
    raw_archive: Path | None = None,
) -> IngestionResult:
    """Ingest a SBIR.gov archive for a single fiscal year."""

    app_config = config or load_config()
    storage: StoragePaths = app_config.storage

    raw_dir = storage.raw / str(fiscal_year)
    processed_dir = storage.processed
    artifacts_dir = storage.artifacts

    raw_zip = raw_archive or download_archive(source_url, raw_dir)
    extracted_dir = raw_dir / "extracted"
    csv_path = extract_archive(raw_zip, extracted_dir)

    df = pd.read_csv(csv_path, dtype=str)
    normalised = _normalise_dataframe(df)

    ingested_at = datetime.now(UTC)
    records = _records_from_dataframe(normalised, source_version=raw_zip.name, ingested_at=ingested_at)

    write_partition(normalised, processed_dir, fiscal_year, filename=PROCESSED_FILENAME)
    _write_metadata(
        {
            "fiscal_year": fiscal_year,
            "source_url": source_url,
            "source_archive": raw_zip.name,
            "records": len(records),
            "ingested_at": ingested_at.isoformat(),
        },
        artifacts_dir,
        fiscal_year,
    )

    return IngestionResult(
        fiscal_year=fiscal_year,
        source_url=source_url,
        raw_archive=raw_zip,
        extracted_csv=csv_path,
        records_ingested=len(records),
    )


def iter_awards_for_year(fiscal_year: int, *, config: AppConfig | None = None) -> Iterable[Award]:
    """Yield processed awards for a fiscal year from the stored parquet."""

    app_config = config or load_config()
    processed_dir = app_config.storage.processed
    df = read_partition(processed_dir, fiscal_year, filename=PROCESSED_FILENAME)
    metadata_path = app_config.storage.artifacts / f"{fiscal_year}-{METADATA_FILENAME}"
    metadata = json.loads(metadata_path.read_text())
    ingested_at = datetime.fromisoformat(metadata["ingested_at"])
    records = _records_from_dataframe(df, metadata["source_archive"], ingested_at)
    for record in records:
        yield record


__all__ = [
    "IngestionResult",
    "download_archive",
    "extract_archive",
    "ingest_fiscal_year",
    "iter_awards_for_year",
]
