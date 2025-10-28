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
from datetime import date, datetime
from sbir_cet_classifier.common.datetime_utils import UTC
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from sbir_cet_classifier.common.config import AppConfig
from sbir_cet_classifier.common.schemas import Award
from sbir_cet_classifier.data.batch_validation import (
    normalize_agencies_batch,
    optimize_dtypes,
    prevalidate_batch,
)

logger = logging.getLogger(__name__)

# US State name to 2-character code mapping
US_STATE_CODES = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
    "district of columbia": "DC",
    "puerto rico": "PR",
    "guam": "GU",
    "virgin islands": "VI",
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
    config: AppConfig | None = None,
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
    ingested_at = datetime.now(UTC)
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
    """Convert DataFrame rows to Award records with batch validation.

    Args:
        df: Normalized DataFrame with canonical column names
        ingested_at: Timestamp for ingestion metadata

    Returns:
        Tuple of (successfully loaded awards, count of skipped rows)
    """
    # Optimize dtypes for performance
    df = optimize_dtypes(df)

    # Normalize agency names in batch
    df = normalize_agencies_batch(df)

    # Pre-validate in batch (fast pandas operations)
    valid_df, invalid_df = prevalidate_batch(df)

    logger.info(
        "Batch pre-validation complete",
        extra={
            "total_rows": len(df),
            "valid_rows": len(valid_df),
            "invalid_rows": len(invalid_df),
        },
    )

    # Convert valid records to Award objects
    awards: list[Award] = []
    skipped = len(invalid_df)

    for idx, row in valid_df.iterrows():
        try:
            award_dict = _prepare_award_dict(row, ingested_at)
            # Coerce award_date to a date object before constructing Award
            ad = award_dict.get("award_date")
            if isinstance(ad, str):
                if ad.isdigit() and len(ad) == 4:
                    award_dict["award_date"] = date(int(ad), 7, 1)
                else:
                    try:
                        award_dict["award_date"] = pd.to_datetime(ad).date()
                    except Exception:
                        award_dict["award_date"] = ingested_at.date()
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
        "award_id": row["award_id"].strip()
        if isinstance(row["award_id"], str)
        else str(row["award_id"]),
        "agency": row["agency"]
        if isinstance(row["agency"], str)
        else str(row["agency"]),  # Already normalized
        "abstract": row["abstract"].strip()
        if ("abstract" in row.index and row["abstract"] and pd.notna(row["abstract"]))
        else None,
        "award_amount": _parse_amount(row["award_amount"]),
        "ingested_at": ingested_at,
        "source_version": "bootstrap_csv",  # Mark as bootstrap ingestion per FR-008
    }

    # Add optional fields if present
    if row.get("sub_agency"):
        award_dict["sub_agency"] = row["sub_agency"].strip()

    if row.get("topic_code"):
        award_dict["topic_code"] = row["topic_code"].strip()
    else:
        # topic_code is required by Award schema, provide placeholder
        award_dict["topic_code"] = "UNKNOWN"

    if row.get("keywords"):
        # Handle comma-separated keywords
        keywords_str = row["keywords"].strip()
        award_dict["keywords"] = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]

    if row.get("phase"):
        phase = row["phase"].strip().upper()
        # Normalize phase to canonical values (exact match first)
        if phase in ("III", "3", "THREE"):
            award_dict["phase"] = "III"
        elif phase in ("II", "2", "TWO"):
            award_dict["phase"] = "II"
        elif phase in ("I", "1", "ONE"):
            award_dict["phase"] = "I"
        else:
            award_dict["phase"] = "Other"
    else:
        award_dict["phase"] = "Other"

    # firm_name is required, use placeholder if missing
    if row.get("firm_name"):
        award_dict["firm_name"] = row["firm_name"].strip()
    else:
        award_dict["firm_name"] = "UNKNOWN"

    # firm_city is required, use placeholder if missing
    if row.get("firm_city"):
        award_dict["firm_city"] = row["firm_city"].strip()
    else:
        award_dict["firm_city"] = "Unknown"

    # firm_state is required (2-char code), use placeholder if missing
    if row.get("firm_state"):
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

    # award_date is required, use award_year, then solicitation_year, then ingestion date if missing
    raw_date = row.get("award_date")
    if raw_date and pd.notna(raw_date):
        # If it's a numeric year, convert to July 1st of that year
        if isinstance(raw_date, (int, float)):
            try:
                year = int(raw_date)
                award_dict["award_date"] = date(year, 7, 1)
            except (ValueError, TypeError):
                award_dict["award_date"] = ingested_at.date()
        else:
            # It's a string, parse it
            parsed_date = _parse_award_date(raw_date)
            # If parsed_date is just a year string (4 digits), convert to July 1st
            # Preserve parsed date as returned by _parse_award_date.
            # If it's a year-only string (e.g., '2023'), keep it as '2023' per tests.
            award_dict["award_date"] = parsed_date
    elif "award year" in row.index and pd.notna(row["award year"]):
        # Use award year column as first fallback (assume July 1st of that year)
        try:
            year = int(row["award year"])
            award_dict["award_date"] = date(year, 7, 1)
        except (ValueError, TypeError):
            # If award year is invalid, try solicitation_year
            if "solicitation_year" in row.index and pd.notna(row["solicitation_year"]):
                try:
                    year = int(row["solicitation_year"])
                    award_dict["award_date"] = date(year, 7, 1)
                except (ValueError, TypeError):
                    award_dict["award_date"] = ingested_at.date()
            else:
                award_dict["award_date"] = ingested_at.date()
    elif "solicitation_year" in row.index and pd.notna(row["solicitation_year"]):
        # Use solicitation_year as second fallback (assume July 1st of that year)
        try:
            year = int(row["solicitation_year"])
            award_dict["award_date"] = date(year, 7, 1)
        except (ValueError, TypeError):
            award_dict["award_date"] = ingested_at.date()
    else:
        # Use ingestion timestamp date as last resort fallback
        award_dict["award_date"] = ingested_at.date()

    if row.get("program"):
        award_dict["program"] = row["program"].strip()

    if row.get("solicitation_id"):
        award_dict["solicitation_id"] = row["solicitation_id"].strip()

    if "solicitation_year" in row.index and pd.notna(row["solicitation_year"]):
        try:
            award_dict["solicitation_year"] = int(row["solicitation_year"])
        except (ValueError, TypeError):
            pass  # Skip invalid solicitation years

    return award_dict


def _parse_amount(amount_str: str | int | float) -> float:
    """Parse award amount to float.

    Args:
        amount_str: Amount as string, int, or float (may contain $, commas, etc.)

    Returns:
        Parsed amount as float

    Raises:
        ValueError: If amount cannot be parsed
    """
    # Handle numeric types directly
    if isinstance(amount_str, (int, float)):
        return float(amount_str)

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
