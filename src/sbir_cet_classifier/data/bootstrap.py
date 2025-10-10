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

# US State name to 2-character code mapping
US_STATE_CODES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
    "puerto rico": "PR", "guam": "GU", "virgin islands": "VI",
}

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
    "branch": "sub_agency",
    "sub_agency_code": "sub_agency",
    # Firm fields
    "firm": "firm_name",
    "company": "firm_name",
    "organization": "firm_name",
    "state": "firm_state",
    "city": "firm_city",
    "location_state": "firm_state",
    "location_city": "firm_city",
    # Award ID mappings (various formats)
    "agency tracking number": "award_id",
    "contract": "award_id",
    "award_number": "award_id",
    "contract_number": "award_id",
    # Award fields
    "award year": "award_date",
    "award_year": "award_date",
    "fiscal_year": "award_date",
    "year": "award_date",
    "proposal award date": "award_date",
    "award amount": "award_amount",
    "amount": "award_amount",
    "dollars": "award_amount",
    "obligated_amount": "award_amount",
    # Topic fields
    "topic": "topic_code",
    "topic code": "topic_code",
    "topic_number": "topic_code",
    "solicitation_topic": "topic_code",
    # Solicitation fields
    "solicitation number": "solicitation_id",
    "solicitation_number": "solicitation_id",
    "solicitation year": "solicitation_year",
    "solicitation_year": "solicitation_year",
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
    already_mapped_to: set[str] = set()  # Track which canonical names have been assigned

    for original_col in df.columns:
        original_lower = original_col.lower().strip()
        if original_lower in COLUMN_MAPPINGS:
            canonical_name = COLUMN_MAPPINGS[original_lower]
            # Skip if this canonical name has already been assigned (avoid duplicates)
            if canonical_name in already_mapped_to:
                continue
            # Avoid overwriting existing canonical columns
            if canonical_name not in df.columns:
                applied_mappings[original_col] = canonical_name
                already_mapped_to.add(canonical_name)

    if applied_mappings:
        df.rename(columns=applied_mappings, inplace=True)

    # Normalize all column names to lowercase for consistent access
    lowercase_mapping = {col: col.lower() for col in df.columns}
    df.rename(columns=lowercase_mapping, inplace=True)

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
        "abstract": row["abstract"].strip() if ("abstract" in row.index and row["abstract"]) else None,
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
        if "I" in phase and "II" not in phase and "III" not in phase:
            award_dict["phase"] = "I"
        elif "II" in phase and "III" not in phase:
            award_dict["phase"] = "II"
        elif "III" in phase:
            award_dict["phase"] = "III"
        elif phase in ("1", "ONE"):
            award_dict["phase"] = "I"
        elif phase in ("2", "TWO"):
            award_dict["phase"] = "II"
        elif phase in ("3", "THREE"):
            award_dict["phase"] = "III"
        else:
            award_dict["phase"] = "Other"
    else:
        award_dict["phase"] = "Other"

    # firm_name is required, use placeholder if missing
    if "firm_name" in row and row["firm_name"]:
        award_dict["firm_name"] = row["firm_name"].strip()
    else:
        award_dict["firm_name"] = "UNKNOWN"

    # firm_city is required, use placeholder if missing
    if "firm_city" in row and row["firm_city"]:
        award_dict["firm_city"] = row["firm_city"].strip()
    else:
        award_dict["firm_city"] = "Unknown"

    # firm_state is required (2-char code), use placeholder if missing
    if "firm_state" in row and row["firm_state"]:
        state_str = row["firm_state"].strip()
        # Try to map state name to code, otherwise use as-is if already 2 chars
        state_lower = state_str.lower()
        if state_lower in US_STATE_CODES:
            award_dict["firm_state"] = US_STATE_CODES[state_lower]
        elif len(state_str) == 2:
            award_dict["firm_state"] = state_str.upper()
        else:
            # Invalid state format, use placeholder
            award_dict["firm_state"] = "XX"
    else:
        award_dict["firm_state"] = "XX"  # Placeholder 2-char code

    # award_date is required, use ingestion date if missing
    if "award_date" in row and row["award_date"]:
        award_dict["award_date"] = _parse_award_date(row["award_date"])
    else:
        # Use ingestion timestamp date as fallback
        award_dict["award_date"] = ingested_at.date()

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
