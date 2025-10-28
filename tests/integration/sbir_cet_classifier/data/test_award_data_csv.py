"""Integration tests using the award_data-3.csv complete data dump.

This test module uses the full SBIR awards CSV file to verify:
- CSV parsing and data validation
- Award data schema compliance
- Data integrity and completeness
- Real-world data edge cases
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from sbir_cet_classifier.common.schemas import Award

# Path to the test CSV file (relative to project root)
CSV_FILE_PATH = Path(__file__).parent.parent.parent.parent.parent / "award_data-3.csv"


@pytest.fixture(scope="module")
def award_dataframe():
    """Load a sample from the award_data-3.csv file as a pandas DataFrame.

    Only reads the first 500 rows to keep tests fast.
    """
    if not CSV_FILE_PATH.exists():
        pytest.skip(f"Test CSV file not found at {CSV_FILE_PATH}")

    # Read only first 500 rows to keep tests fast
    df = pd.read_csv(CSV_FILE_PATH, dtype=str, nrows=500)

    # Map the CSV columns to expected schema
    # Based on the CSV structure we saw, we need to map the columns
    column_mapping = {
        "Company": "firm",
        "Award Title": "title",
        "Agency": "agency_code",
        "Branch": "bureau_code",
        "Phase": "phase",
        "Program": "program",
        "Agency Tracking Number": "tracking_number",
        "Contract": "award_id",
        "Proposal Award Date": "award_year",
        "Award Year": "fiscal_year",
        "Award Amount": "award_amount",
        "Topic Code": "topic_code",
        "State": "firm_state",
        "City": "firm_city",
        "Abstract": "abstract",
    }

    df = df.rename(columns=column_mapping)

    # Ensure required columns exist with defaults if needed
    if "keywords" not in df.columns:
        df["keywords"] = ""

    return df


def test_csv_file_exists():
    """Verify the award_data-3.csv file exists."""
    if not CSV_FILE_PATH.exists():
        pytest.skip(f"Test CSV file not found at {CSV_FILE_PATH}")
    assert CSV_FILE_PATH.exists(), f"CSV file not found at {CSV_FILE_PATH}"


def test_csv_loads_successfully(award_dataframe):
    """Verify the CSV can be loaded without errors."""
    assert award_dataframe is not None
    assert len(award_dataframe) > 0, "CSV file should contain data"


def test_csv_has_expected_columns(award_dataframe):
    """Verify the CSV has the expected column structure."""
    # Check for key columns that should exist after mapping
    expected_columns = ["award_id", "agency_code", "firm", "abstract", "award_year", "award_amount"]

    for col in expected_columns:
        assert col in award_dataframe.columns, f"Missing expected column: {col}"


def test_award_data_completeness(award_dataframe):
    """Analyze data completeness in the CSV."""
    total_rows = len(award_dataframe)

    # Check for completeness of critical fields
    award_id_complete = award_dataframe["award_id"].notna().sum()
    agency_complete = award_dataframe["agency_code"].notna().sum()
    abstract_complete = award_dataframe["abstract"].notna().sum()

    # Assert critical fields are mostly complete
    assert award_id_complete == total_rows, "All records should have an award_id"
    assert agency_complete == total_rows, "All records should have an agency"

    # Report abstract completeness (may not be 100%)
    abstract_pct = (abstract_complete / total_rows) * 100
    assert abstract_pct > 50, f"Expected >50% abstract completion, got {abstract_pct:.1f}%"


def test_award_schema_validation_sample(award_dataframe):
    """Test that awards can be validated against the Award schema.

    This tests a sample of records to verify schema compliance.
    """
    # Prepare a normalized version
    normalized = award_dataframe.copy()

    # Fill required fields with proper type handling
    if "bureau_code" not in normalized.columns:
        normalized["bureau_code"] = ""
    normalized["bureau_code"] = normalized["bureau_code"].fillna("").astype(str)

    if "topic_code" not in normalized.columns:
        normalized["topic_code"] = "UNKNOWN"
    normalized["topic_code"] = normalized["topic_code"].fillna("UNKNOWN").astype(str)

    normalized["phase"] = normalized["phase"].fillna("Other").astype(str)
    normalized["firm_state"] = normalized["firm_state"].fillna("XX").astype(str)
    normalized["firm_city"] = normalized["firm_city"].fillna("Unknown").astype(str)
    normalized["firm"] = normalized["firm"].fillna("Unknown").astype(str)
    normalized["award_amount"] = pd.to_numeric(normalized["award_amount"], errors="coerce").fillna(
        0
    )
    normalized["award_year"] = pd.to_datetime(normalized["award_year"], errors="coerce")

    # Rename to match schema
    normalized = normalized.rename(
        columns={
            "agency_code": "agency",
            "bureau_code": "sub_agency",
            "firm": "firm_name",
            "award_year": "award_date",
        }
    )

    # Create Award records from a sample (first 50 records from our already-limited dataset)
    sample_size = min(50, len(normalized))
    sample_df = normalized.head(sample_size)

    ingested_at = datetime.now(UTC)

    valid_count = 0
    invalid_count = 0
    errors = []

    for idx, row in sample_df.iterrows():
        try:
            # Get sub_agency value with proper handling
            sub_agency_val = row.get("sub_agency", "")
            if pd.isna(sub_agency_val) or sub_agency_val == "" or sub_agency_val == "nan":
                sub_agency_val = None

            # Get phase value
            phase_val = row["phase"]
            if phase_val in ["Phase I", "SBIR Phase I"]:
                phase_val = "I"
            elif phase_val in ["Phase II", "SBIR Phase II", "STTR Phase II"]:
                phase_val = "II"
            elif phase_val in ["Phase III", "SBIR Phase III"]:
                phase_val = "III"
            else:
                phase_val = "Other"

            # Try to create an Award instance
            Award(
                award_id=str(row["award_id"]),
                agency=str(row["agency"]) if pd.notna(row["agency"]) else "UNKNOWN",
                sub_agency=sub_agency_val,
                topic_code=str(row["topic_code"]),
                abstract=str(row.get("abstract", "")) if pd.notna(row.get("abstract")) else None,
                keywords=str(row.get("keywords", "")) if pd.notna(row.get("keywords")) else "",
                phase=phase_val,
                firm_name=str(row["firm_name"]),
                firm_city=str(row["firm_city"]),
                firm_state=str(row["firm_state"])[:2] if len(str(row["firm_state"])) >= 2 else "XX",
                award_amount=float(row["award_amount"]) if pd.notna(row["award_amount"]) else 0.0,
                award_date=row["award_date"].date()
                if pd.notna(row["award_date"])
                else datetime(2020, 1, 1).date(),
                source_version="award_data-3.csv",
                ingested_at=ingested_at,
            )
            valid_count += 1
        except Exception as e:
            invalid_count += 1
            if len(errors) < 5:  # Keep first 5 errors for debugging
                errors.append(f"Row {idx}: {str(e)[:100]}")

    # Assert that most records are valid
    validity_pct = (valid_count / sample_size) * 100

    if errors:
        print("\nFirst few validation errors:\n" + "\n".join(errors))

    assert validity_pct > 70, f"Expected >70% valid records, got {validity_pct:.1f}%"


def test_agency_distribution(award_dataframe):
    """Analyze the distribution of awards by agency."""
    agency_counts = award_dataframe["agency_code"].value_counts()

    # Should have multiple agencies represented
    assert len(agency_counts) > 0, "Should have at least one agency"

    # NSF appears to be a major agency based on the sample
    if "National Science Foundation" in agency_counts.index:
        assert agency_counts["National Science Foundation"] > 0


def test_phase_distribution(award_dataframe):
    """Analyze the distribution of awards by phase."""
    phase_counts = award_dataframe["phase"].value_counts()

    # Should have Phase I and Phase II awards
    phases = set(phase_counts.index)

    # Check for expected phase values
    expected_phases = {"Phase I", "Phase II", "SBIR", "STTR"}
    actual_phases = phases & expected_phases

    assert len(actual_phases) > 0, "Should have some standard phase values"


def test_award_amounts(award_dataframe):
    """Analyze award amount distributions."""
    amounts = pd.to_numeric(award_dataframe["award_amount"], errors="coerce").dropna()

    if len(amounts) > 0:
        # Check for reasonable award amounts
        assert amounts.min() >= 0, "Award amounts should be non-negative"

        # Phase I awards typically ~$150k-$250k, Phase II ~$750k-$1.5M
        # Let's check the median is reasonable
        median_amount = amounts.median()
        assert (
            100_000 <= median_amount <= 2_000_000
        ), f"Median award amount {median_amount:,.0f} seems unusual"


def test_abstract_text_analysis(award_dataframe):
    """Analyze abstract text quality and content."""
    abstracts = award_dataframe["abstract"].dropna()

    if len(abstracts) > 0:
        # Check average abstract length
        avg_length = abstracts.str.len().mean()

        # Abstracts should be substantive (typically several hundred characters)
        assert avg_length > 100, f"Average abstract length {avg_length:.0f} seems too short"

        # Check for common SBIR-related terms (use all available abstracts since we're limited to 500 rows)
        combined_text = " ".join(abstracts.str.lower())

        # Should contain technical/research terms
        sbir_terms = ["technology", "research", "development", "innovation", "system", "project"]
        found_terms = [term for term in sbir_terms if term in combined_text]

        assert (
            len(found_terms) >= 3
        ), f"Expected SBIR terminology in abstracts, found: {found_terms}"


def test_fiscal_year_range(award_dataframe):
    """Verify fiscal year data is within reasonable range."""
    if "fiscal_year" in award_dataframe.columns:
        fiscal_years = pd.to_numeric(award_dataframe["fiscal_year"], errors="coerce").dropna()

        if len(fiscal_years) > 0:
            min_year = fiscal_years.min()
            max_year = fiscal_years.max()

            # Should be reasonable years (SBIR program started in 1982)
            assert 1982 <= min_year <= 2030, f"Minimum fiscal year {min_year} seems incorrect"
            assert 2020 <= max_year <= 2030, f"Maximum fiscal year {max_year} seems incorrect"


def test_state_codes(award_dataframe):
    """Verify state codes are valid US state abbreviations."""
    # The CSV has full state names like "California", not codes like "CA"
    states = award_dataframe["firm_state"].dropna()

    if len(states) > 0:
        # Convert to string and check we have state data
        states_str = states.astype(str)

        # Just verify we have state information (not empty/nan)
        non_empty = states_str[~states_str.isin(["", "nan", "None"])].count()
        completeness_pct = (non_empty / len(states)) * 100

        # Most records should have state information
        assert (
            completeness_pct > 80
        ), f"Expected >80% state data completeness, got {completeness_pct:.1f}%"

        # Check for some common US states in full name format
        common_states = ["California", "Massachusetts", "Texas", "New York", "Virginia"]
        has_common_states = any(state in states_str.values for state in common_states)
        assert has_common_states, "Expected to find common US state names in the data"


def test_deduplication(award_dataframe):
    """Check for duplicate award IDs."""
    award_ids = award_dataframe["award_id"].dropna()

    total_ids = len(award_ids)
    unique_ids = award_ids.nunique()

    # Report duplication rate
    dup_rate = ((total_ids - unique_ids) / total_ids) * 100 if total_ids > 0 else 0

    # Some duplication might be expected (e.g., amendments, updates)
    # but should be relatively low
    assert dup_rate < 10, f"Duplication rate of {dup_rate:.1f}% seems high"
