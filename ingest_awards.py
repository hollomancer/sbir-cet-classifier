#!/usr/bin/env python3
"""
Ingest SBIR awards from award_data-3.csv and classify them by CET.

This script:
1. Loads the award_data-3.csv file
2. Normalizes the data to match the expected schema
3. Loads the CET taxonomy
4. Classifies each award against CET areas
5. Saves the processed data for use with CLI/API
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sbir_cet_classifier.common.config import AppConfig, StoragePaths
from sbir_cet_classifier.data.taxonomy import TaxonomyRepository
from sbir_cet_classifier.models.applicability import ApplicabilityModel, band_for_score


def load_and_normalize_csv(csv_path: Path) -> pd.DataFrame:
    """Load the award_data-3.csv and normalize it to the expected schema."""
    print(f"📂 Loading CSV from {csv_path}...")
    print(f"   (This may take a few minutes for large files...)")

    # Read entire CSV file
    df = pd.read_csv(csv_path, dtype=str)
    print(f"   Loaded {len(df):,} records")

    # Map CSV columns to expected schema
    column_mapping = {
        "Company": "firm_name",
        "Award Title": "title",
        "Agency": "agency",
        "Branch": "sub_agency",
        "Phase": "phase",
        "Contract": "award_id",
        "Proposal Award Date": "award_date",
        "Award Year": "fiscal_year",
        "Award Amount": "award_amount",
        "Topic Code": "topic_code",
        "State": "firm_state",
        "City": "firm_city",
        "Abstract": "abstract",
    }

    df = df.rename(columns=column_mapping)

    # Normalize data types and fill missing values
    df["sub_agency"] = df.get("sub_agency", "").fillna("").astype(str)
    df["topic_code"] = df.get("topic_code", "UNKNOWN").fillna("UNKNOWN").astype(str)
    df["abstract"] = df.get("abstract", "").fillna("").astype(str)
    df["firm_name"] = df.get("firm_name", "Unknown").fillna("Unknown").astype(str)
    df["firm_city"] = df.get("firm_city", "Unknown").fillna("Unknown").astype(str)
    df["firm_state"] = df.get("firm_state", "XX").fillna("XX").astype(str)
    df["award_amount"] = pd.to_numeric(df.get("award_amount", 0), errors="coerce").fillna(0)
    df["award_date"] = pd.to_datetime(df.get("award_date"), errors="coerce")
    df["fiscal_year"] = pd.to_numeric(df.get("fiscal_year"), errors="coerce").fillna(2025).astype(int)

    # Normalize phase values
    phase_mapping = {
        "Phase I": "I",
        "Phase II": "II",
        "Phase III": "III",
        "SBIR Phase I": "I",
        "SBIR Phase II": "II",
        "STTR Phase II": "II",
    }
    df["phase"] = df["phase"].map(lambda x: phase_mapping.get(x, "Other") if pd.notna(x) else "Other")

    # Ensure award_id is unique
    initial_count = len(df)
    df = df.drop_duplicates(subset=["award_id"], keep="first")
    duplicates_removed = initial_count - len(df)

    # Add keywords column (empty for now)
    df["keywords"] = [[] for _ in range(len(df))]

    print(f"   Normalized to {len(df):,} unique awards")
    if duplicates_removed > 0:
        print(f"   (Removed {duplicates_removed:,} duplicate award_ids)")
    return df


def load_taxonomy(taxonomy_path: Path) -> pd.DataFrame:
    """Load the CET taxonomy."""
    print(f"📚 Loading CET taxonomy from {taxonomy_path}...")
    taxonomy_df = pd.read_csv(taxonomy_path)
    print(f"   Loaded {len(taxonomy_df)} CET areas")
    return taxonomy_df


def classify_awards(awards_df: pd.DataFrame, taxonomy_df: pd.DataFrame) -> pd.DataFrame:
    """Classify awards against CET areas using the applicability model."""
    print(f"🤖 Classifying {len(awards_df):,} awards against CET taxonomy...")
    print(f"   (This will take approximately {len(awards_df) / 1000:.0f} seconds...)")

    # Prepare training data (using simple keyword matching for now)
    # In production, this would use actual labeled training data
    cet_keywords = {
        "quantum_computing": ["quantum", "qubit", "superposition", "entanglement"],
        "quantum_sensing": ["quantum sensing", "quantum measurement", "quantum detector"],
        "artificial_intelligence": ["ai", "machine learning", "neural network", "deep learning", "computer vision"],
        "biotechnology": ["biotech", "genomics", "synthetic biology", "biomanufacturing", "protein"],
        "hypersonics": ["hypersonic", "mach 5", "high-speed flight"],
        "thermal_protection": ["thermal protection", "heat shield", "tps", "ablative"],
        "advanced_materials": ["metamaterial", "nanomaterial", "smart material", "composite"],
        "cybersecurity": ["cybersecurity", "encryption", "cryptography", "security"],
        "autonomous_systems": ["autonomous", "drone", "uav", "robot", "self-driving"],
        "semiconductors": ["semiconductor", "chip", "microelectronics", "processor"],
        "space_technology": ["spacecraft", "satellite", "space", "orbital"],
        "energy_storage": ["battery", "energy storage", "supercapacitor"],
        "renewable_energy": ["solar", "wind", "renewable energy", "photovoltaic"],
        "medical_devices": ["medical device", "diagnostic", "therapeutic", "healthcare"],
    }

    # Classify each award
    assessments = []
    ingested_at = datetime.now(timezone.utc)

    for idx, row in awards_df.iterrows():
        abstract = str(row.get("abstract", "")).lower()
        title = str(row.get("title", "")).lower()
        combined_text = f"{title} {abstract}"

        # Find best matching CET area
        best_cet = None
        best_score = 0

        for cet_id, keywords in cet_keywords.items():
            score = sum(10 for keyword in keywords if keyword in combined_text)
            if score > best_score:
                best_score = score
                best_cet = cet_id

        # Default to a generic category if no match
        if best_cet is None:
            best_cet = "advanced_manufacturing"
            best_score = 30

        # Normalize score to 0-100 range
        normalized_score = min(100, best_score * 5)
        classification = band_for_score(normalized_score)

        assessment = {
            "assessment_id": f"auto-{row['award_id']}",
            "award_id": row["award_id"],
            "taxonomy_version": "NSTC-2025Q1",
            "score": normalized_score,
            "classification": classification,
            "primary_cet_id": best_cet,
            "supporting_cet_ids": [],
            "evidence_statements": [],
            "generation_method": "automated",
            "assessed_at": ingested_at,
            "reviewer_notes": None,
        }
        assessments.append(assessment)

        if (idx + 1) % 1000 == 0:
            progress_pct = (idx + 1) / len(awards_df) * 100
            print(f"   Classified {idx + 1:,}/{len(awards_df):,} awards ({progress_pct:.1f}%)...")

    assessments_df = pd.DataFrame(assessments)
    print(f"   ✅ Classified all {len(assessments_df):,} awards")

    # Print classification summary
    print(f"\n   Classification Distribution:")
    for band, count in assessments_df['classification'].value_counts().items():
        pct = count / len(assessments_df) * 100
        print(f"      {band}: {count:,} awards ({pct:.1f}%)")

    return assessments_df


def save_processed_data(awards_df: pd.DataFrame, assessments_df: pd.DataFrame, taxonomy_df: pd.DataFrame):
    """Save processed data to parquet files."""
    print(f"💾 Saving processed data...")

    # Create directories
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    # Save data
    awards_df.to_parquet(processed_dir / "awards.parquet", index=False)
    assessments_df.to_parquet(processed_dir / "assessments.parquet", index=False)
    taxonomy_df.to_parquet(processed_dir / "taxonomy.parquet", index=False)

    print(f"   ✅ Saved to {processed_dir}/")
    print(f"      - awards.parquet ({len(awards_df):,} records)")
    print(f"      - assessments.parquet ({len(assessments_df):,} records)")
    print(f"      - taxonomy.parquet ({len(taxonomy_df)} records)")


def main():
    """Main ingestion workflow."""
    print("=" * 60)
    print("SBIR Award CET Classification Pipeline")
    print("=" * 60)

    # Paths
    csv_path = Path("award_data-3.csv")
    taxonomy_path = Path("data/taxonomy/cet_taxonomy_v1.csv")

    # Check files exist
    if not csv_path.exists():
        print(f"❌ Error: {csv_path} not found")
        return 1

    if not taxonomy_path.exists():
        print(f"❌ Error: {taxonomy_path} not found")
        return 1

    # Load and process data
    awards_df = load_and_normalize_csv(csv_path)
    taxonomy_df = load_taxonomy(taxonomy_path)
    assessments_df = classify_awards(awards_df, taxonomy_df)

    # Save results
    save_processed_data(awards_df, assessments_df, taxonomy_df)

    print("\n" + "=" * 60)
    print("✅ Ingestion Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. View summary: python -m sbir_cet_classifier.cli.app summary --fiscal-year-start 2023 --fiscal-year-end 2025")
    print("  2. List awards: python -m sbir_cet_classifier.cli.app awards list --fiscal-year-start 2023 --fiscal-year-end 2025 --page 1")
    print("  3. Start API: uvicorn sbir_cet_classifier.api.router:router --reload")

    return 0


if __name__ == "__main__":
    sys.exit(main())
