"""Bootstrap CSV loader for initial cold-start award data ingestion.

This module handles one-time ingestion of awards-data.csv, validating schema
compatibility with SBIR.gov format and mapping columns to canonical Award schema.
After bootstrap, subsequent refreshes use the SBIR.gov bulk download pipeline.

Typical usage:
    from pathlib import Path
    from sbir_cet_classifier.data.bootstrap import load_bootstrap_csv

    result = load_bootstrap_csv(Path("data/raw/awards-data.csv"))
    print(f"Loaded {len(result.awards)} awards from bootstrap CSV")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from pydantic import ValidationError

from sbir_cet_classifier.common.config import AppConfig
from sbir_cet_classifier.common.schemas import Award

logger = logging.getLogger(__name__)

# Minimum required columns for bootstrap CSV (matches FR-008 specification)
BOOTSTRAP_REQUIRED_COLUMNS = {
    "award_id",
    "agency",
    "abstract",
    "award_amount",
}

# Optional columns that may be present in bootstrap CSV
BOOTSTRAP_OPTIONAL_COLUMNS = {
    "sub_agency",
    "topic_code",
    "keywords",
    "phase",
    "firm_name",
    "firm_city",
    "firm_state",
    "award_date",
    "program",
    "solicitation_id",
    "solicitation_year",
}

# Column name mappings from common CSV variants to canonical schema
COLUMN_MAPPINGS = {
    # Agency fields
    "agency_code": "agency",
    "agency_name": "agency",
    "bureau_code": "sub_agency",
    "bureau": "sub_agency",
    "sub_agency_code": "sub_agency",
    # Firm fields
    "firm": "firm_name",
    "company": "firm_name",
    "organization": "firm_name",
    "state": "firm_state",
    "city": "firm_city",
    "location_state": "firm_state",
    "location_city": "firm_city",
    # Award fields
    "award_year": "award_date",
    "fiscal_year": "award_date",
    "year": "award_date",
    "amount": "award_amount",
    "dollars": "award_amount",
    "obligated_amount": "award_amount",
    # Topic fields
    "topic": "topic_code",
    "topic_number": "topic_code",
    "solicitation_topic": "topic_code",
}


@dataclass
class BootstrapResult:
    """Result of bootstrap CSV ingestion."""

    awards: list[Award]
    """Successfully loaded award records."""

    total_rows: int
    """Total rows in source CSV."""

    loaded_count: int
    """Number of awards successfully loaded."""

    skipped_count: int
    """Number of rows skipped due to validation errors."""

    field_mappings: dict[str, str]
    """Column name mappings applied during ingestion."""

    ingested_at: datetime
    """Timestamp when ingestion completed."""


class BootstrapCSVError(Exception):
    """Raised when bootstrap CSV loading fails due to schema issues."""


def load_bootstrap_csv(
    csv_path: Path,
    *,
    config: Optional[AppConfig] = None,
) -> BootstrapResult:
    """Load awards from bootstrap CSV file.

    Args:
        csv_path: Path to awards-data.csv file
        config: Optional application configuration (unused, for API compatibility)

    Returns:
        BootstrapResult containing loaded awards and ingestion metadata

    Raises:
        BootstrapCSVError: If required columns are missing or CSV cannot be read
        FileNotFoundError: If csv_path does not exist

    Example:
        >>> from pathlib import Path
        >>> result = load_bootstrap_csv(Path("data/raw/awards-data.csv"))
        >>> print(f"Loaded {result.loaded_count} awards")
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Bootstrap CSV not found: {csv_path}")

    logger.info("Starting bootstrap CSV ingestion", extra={"csv_path": str(csv_path)})

    try:
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    except Exception as e:
        raise BootstrapCSVError(f"Failed to read CSV file: {e}") from e

    if df.empty:
        raise BootstrapCSVError("Bootstrap CSV is empty")

    logger.info("Read CSV file", extra={"total_rows": len(df), "columns": list(df.columns)})

    # Apply column mappings
    field_mappings = _apply_column_mappings(df)
    if field_mappings:
        logger.info("Applied column mappings", extra={"mappings": field_mappings})

    # Validate required columns are present
    _validate_required_columns(df)

    # Normalize and convert to Award records
    ingested_at = datetime.now(timezone.utc)
    awards, skipped = _convert_to_awards(df, ingested_at)

    logger.info(
        "Bootstrap CSV ingestion complete",
        extra={
            "total_rows": len(df),
            "loaded_count": len(awards),
            "skipped_count": skipped,
            "ingested_at": ingested_at.isoformat(),
        },
    )

    return BootstrapResult(
        awards=awards,
        total_rows=len(df),
        loaded_count=len(awards),
        skipped_count=skipped,
        field_mappings=field_mappings,
        ingested_at=ingested_at,
    )


def _apply_column_mappings(df: pd.DataFrame) -> dict[str, str]:
    """Apply column name mappings to DataFrame in-place.

    Args:
        df: DataFrame to apply mappings to (modified in-place)

    Returns:
        Dictionary of applied mappings {original_name: canonical_name}
    """
    applied_mappings: dict[str, str] = {}

    for original_col in df.columns:
        original_lower = original_col.lower().strip()
        if original_lower in COLUMN_MAPPINGS:
            canonical_name = COLUMN_MAPPINGS[original_lower]
            if canonical_name not in df.columns:  # Avoid overwriting existing canonical columns
                applied_mappings[original_col] = canonical_name

    if applied_mappings:
        df.rename(columns=applied_mappings, inplace=True)

    return applied_mappings


def _validate_required_columns(df: pd.DataFrame) -> None:
    """Validate that all required columns are present.

    Args:
        df: DataFrame to validate

    Raises:
        BootstrapCSVError: If any required columns are missing
    """
    present_columns = set(df.columns)
    missing_columns = BOOTSTRAP_REQUIRED_COLUMNS - present_columns

    if missing_columns:
        raise BootstrapCSVError(
            f"Bootstrap CSV missing required columns: {', '.join(sorted(missing_columns))}. "
            f"Required: {', '.join(sorted(BOOTSTRAP_REQUIRED_COLUMNS))}"
        )


def _convert_to_awards(df: pd.DataFrame, ingested_at: datetime) -> tuple[list[Award], int]:
    """Convert DataFrame rows to Award records.

    Args:
        df: Normalized DataFrame with canonical column names
        ingested_at: Timestamp for ingestion metadata

    Returns:
        Tuple of (successfully loaded awards, count of skipped rows)
    """
    awards: list[Award] = []
    skipped = 0

    for idx, row in df.iterrows():
        try:
            award_dict = _prepare_award_dict(row, ingested_at)
            award = Award(**award_dict)
            awards.append(award)
        except (ValidationError, ValueError) as e:
            logger.warning(
                "Skipping invalid award record",
                extra={
                    "row_index": idx,
                    "award_id": row.get("award_id", "<missing>"),
                    "error": str(e),
                },
            )
            skipped += 1

    return awards, skipped


def _prepare_award_dict(row: pd.Series, ingested_at: datetime) -> dict[str, Any]:
    """Prepare award dictionary from DataFrame row.

    Args:
        row: DataFrame row as Series
        ingested_at: Timestamp for ingestion metadata

    Returns:
        Dictionary suitable for Award model construction
    """
    award_dict: dict[str, Any] = {
        "award_id": row["award_id"].strip(),
        "agency": row["agency"].strip(),
        "abstract": row["abstract"].strip() if row.get("abstract") else None,
        "award_amount": _parse_amount(row["award_amount"]),
        "ingested_at": ingested_at,
        "source_version": "bootstrap_csv",  # Mark as bootstrap ingestion per FR-008
    }

    # Add optional fields if present
    if "sub_agency" in row and row["sub_agency"]:
        award_dict["sub_agency"] = row["sub_agency"].strip()

    if "topic_code" in row and row["topic_code"]:
        award_dict["topic_code"] = row["topic_code"].strip()
    else:
        # topic_code is required by Award schema, provide placeholder
        award_dict["topic_code"] = "UNKNOWN"

    if "keywords" in row and row["keywords"]:
        # Handle comma-separated keywords
        keywords_str = row["keywords"].strip()
        award_dict["keywords"] = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]

    if "phase" in row and row["phase"]:
        phase = row["phase"].strip().upper()
        # Normalize phase to canonical values
        if phase in ("I", "1", "ONE"):
            award_dict["phase"] = "I"
        elif phase in ("II", "2", "TWO"):
            award_dict["phase"] = "II"
        elif phase in ("III", "3", "THREE"):
            award_dict["phase"] = "III"
        else:
            award_dict["phase"] = "Other"
    else:
        award_dict["phase"] = "Other"

    if "firm_name" in row and row["firm_name"]:
        award_dict["firm_name"] = row["firm_name"].strip()

    if "firm_city" in row and row["firm_city"]:
        award_dict["firm_city"] = row["firm_city"].strip()

    if "firm_state" in row and row["firm_state"]:
        award_dict["firm_state"] = row["firm_state"].strip().upper()

    if "award_date" in row and row["award_date"]:
        award_dict["award_date"] = _parse_award_date(row["award_date"])

    if "program" in row and row["program"]:
        award_dict["program"] = row["program"].strip()

    if "solicitation_id" in row and row["solicitation_id"]:
        award_dict["solicitation_id"] = row["solicitation_id"].strip()

    if "solicitation_year" in row and row["solicitation_year"]:
        try:
            award_dict["solicitation_year"] = int(row["solicitation_year"])
        except (ValueError, TypeError):
            pass  # Skip invalid solicitation years

    return award_dict


def _parse_amount(amount_str: str) -> float:
    """Parse award amount string to float.

    Args:
        amount_str: Amount string (may contain $, commas, etc.)

    Returns:
        Parsed amount as float

    Raises:
        ValueError: If amount cannot be parsed
    """
    # Strip currency symbols, commas, whitespace
    cleaned = amount_str.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError as e:
        raise ValueError(f"Invalid award amount: {amount_str}") from e


def _parse_award_date(date_str: str) -> str:
    """Parse and normalize award date.

    Args:
        date_str: Date string (may be year only, ISO date, etc.)

    Returns:
        Normalized date string (ISO format or year only)
    """
    date_str = date_str.strip()

    # If it's just a year (4 digits), return as-is
    if date_str.isdigit() and len(date_str) == 4:
        return date_str

    # Try parsing as date and return ISO format
    try:
        parsed = pd.to_datetime(date_str)
        return parsed.strftime("%Y-%m-%d")
    except Exception:
        # Fall back to original string if parsing fails
        return date_str
