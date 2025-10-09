#!/usr/bin/env python3
"""
Ingest SBIR awards from award_data-3.csv and classify them by CET.

This script:
1. Loads the award_data-3.csv file
2. Normalizes the data to match the expected schema
3. Loads the CET taxonomy
4. Classifies each award against CET areas (multi-label with weights)
5. Saves the processed data for use with CLI/API
"""

import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import numpy as np

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

    # Generate synthetic IDs for NULL/missing contracts
    print(f"   Generating synthetic IDs for awards with missing contracts...")
    null_mask = df["award_id"].isna() | (df["award_id"] == "")
    null_count = null_mask.sum()

    def generate_synthetic_id(row):
        """Generate unique ID from award attributes."""
        # Create composite key from available fields
        composite = f"{row['firm_name']}|{row['title']}|{row['award_date']}|{row['award_amount']}|{row['agency']}"
        hash_val = hashlib.md5(composite.encode()).hexdigest()[:16]
        return f"SYNTH-{hash_val}"

    df.loc[null_mask, "award_id"] = df[null_mask].apply(generate_synthetic_id, axis=1)

    if null_count > 0:
        print(f"   Generated {null_count:,} synthetic IDs for awards with missing contracts")

    # Now deduplicate - both real and synthetic IDs
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
    """Classify awards against CET areas using multi-label weighted classification."""
    print(f"🤖 Classifying {len(awards_df):,} awards against CET taxonomy...")
    print(f"   Using improved multi-label weighted classification...")
    print(f"   (This will take approximately {len(awards_df) / 800:.0f} seconds...)")

    # Enhanced keyword matching with weighted importance
    # Format: {cet_id: {"core": [...], "related": [...], "negative": [...]}}
    cet_keywords = {
        "quantum_computing": {
            "core": ["quantum computing", "quantum computer", "qubit", "quantum algorithm"],
            "related": ["quantum", "superposition", "entanglement", "quantum gate"],
            "negative": ["quantum mechanics", "quantum chemistry"]  # Exclude these contexts
        },
        "quantum_sensing": {
            "core": ["quantum sensing", "quantum sensor", "quantum measurement"],
            "related": ["quantum detector", "quantum metrology", "atomic clock"],
            "negative": []
        },
        "artificial_intelligence": {
            "core": ["artificial intelligence", "deep learning", "neural network", "machine learning"],
            "related": ["ai", "ml", "computer vision", "natural language", "nlp", "reinforcement learning"],
            "negative": []
        },
        "biotechnology": {
            "core": ["biotechnology", "synthetic biology", "genetic engineering", "crispr"],
            "related": ["biotech", "genomics", "biomanufacturing", "protein engineering", "gene editing"],
            "negative": []
        },
        "hypersonics": {
            "core": ["hypersonic", "mach 5", "mach 6", "high-speed flight"],
            "related": ["supersonic", "scramjet", "ramjet"],
            "negative": []
        },
        "thermal_protection": {
            "core": ["thermal protection system", "heat shield", "tps"],
            "related": ["ablative", "thermal management", "re-entry"],
            "negative": []
        },
        "advanced_materials": {
            "core": ["metamaterial", "nanomaterial", "smart material", "advanced material"],
            "related": ["composite", "graphene", "carbon nanotube", "nanostructure"],
            "negative": []
        },
        "cybersecurity": {
            "core": ["cybersecurity", "information security", "network security"],
            "related": ["encryption", "cryptography", "cyber defense", "intrusion detection"],
            "negative": []
        },
        "autonomous_systems": {
            "core": ["autonomous system", "autonomous vehicle", "self-driving"],
            "related": ["autonomous", "drone", "uav", "unmanned", "robot", "robotics"],
            "negative": []
        },
        "semiconductors": {
            "core": ["semiconductor", "microelectronics", "integrated circuit"],
            "related": ["chip", "processor", "asic", "fpga", "transistor"],
            "negative": []
        },
        "space_technology": {
            "core": ["spacecraft", "satellite", "space mission"],
            "related": ["space", "orbital", "launch vehicle", "propulsion"],
            "negative": ["cyberspace", "workspace"]
        },
        "energy_storage": {
            "core": ["energy storage", "battery technology", "electrochemical storage"],
            "related": ["battery", "supercapacitor", "lithium-ion", "fuel cell"],
            "negative": []
        },
        "renewable_energy": {
            "core": ["renewable energy", "solar energy", "wind energy"],
            "related": ["solar", "wind", "photovoltaic", "solar cell", "wind turbine"],
            "negative": []
        },
        "medical_devices": {
            "core": ["medical device", "diagnostic device", "therapeutic device"],
            "related": ["diagnostic", "therapeutic", "healthcare device", "biomedical"],
            "negative": []
        },
    }

    # Classify each award with multi-label support
    assessments = []
    ingested_at = datetime.now(timezone.utc)

    for idx, row in awards_df.iterrows():
        abstract = str(row.get("abstract", "")).lower()
        title = str(row.get("title", "")).lower()

        # Weight title matches higher than abstract
        title_text = title * 2  # Title matches count double
        combined_text = f"{title_text} {abstract}"

        # Calculate scores for all CET areas
        cet_scores = {}

        for cet_id, keyword_dict in cet_keywords.items():
            score = 0

            # Core keywords (weight: 15 points each)
            for keyword in keyword_dict["core"]:
                if keyword in combined_text:
                    score += 15
                    # Bonus if in title
                    if keyword in title:
                        score += 10

            # Related keywords (weight: 5 points each)
            for keyword in keyword_dict["related"]:
                if keyword in combined_text:
                    score += 5

            # Negative keywords (penalize if present)
            for keyword in keyword_dict["negative"]:
                if keyword in combined_text:
                    score -= 10

            # Ensure non-negative
            score = max(0, score)

            if score > 0:
                cet_scores[cet_id] = score

        # If no matches, default to advanced_manufacturing
        if not cet_scores:
            cet_scores = {"advanced_manufacturing": 30}

        # Normalize scores to 0-100 range based on max possible score
        max_possible = 15 * 4 + 10  # 4 core keywords * 15 + title bonus
        cet_scores_normalized = {
            cet_id: min(100, int((score / max_possible) * 100))
            for cet_id, score in cet_scores.items()
        }

        # Select top 3 CET areas
        sorted_cets = sorted(cet_scores_normalized.items(), key=lambda x: x[1], reverse=True)
        top_cets = sorted_cets[:3]  # Top 3

        primary_cet_id, primary_score = top_cets[0]
        supporting_cet_ids = [cet_id for cet_id, score in top_cets[1:] if score >= 30]  # Only if score >= 30

        # Calculate classification band
        classification = band_for_score(primary_score)

        # Create weighted distribution (sums to 1.0)
        all_scores = [score for _, score in top_cets]
        total_score = sum(all_scores)
        cet_weights = {
            cet_id: round(score / total_score, 3) if total_score > 0 else 0.0
            for cet_id, score in top_cets
        }

        assessment = {
            "assessment_id": f"auto-{row['award_id']}",
            "award_id": row["award_id"],
            "taxonomy_version": "NSTC-2025Q1",
            "score": primary_score,
            "classification": classification,
            "primary_cet_id": primary_cet_id,
            "supporting_cet_ids": supporting_cet_ids,
            "cet_weights": cet_weights,  # NEW: Normalized weights
            "all_cet_scores": dict(sorted_cets[:5]),  # NEW: Top 5 raw scores
            "evidence_statements": [],
            "generation_method": "automated_v2_multi_label",
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

    # Print score statistics
    print(f"\n   Score Statistics:")
    print(f"      Min: {assessments_df['score'].min():.0f}")
    print(f"      Max: {assessments_df['score'].max():.0f}")
    print(f"      Mean: {assessments_df['score'].mean():.1f}")
    print(f"      Median: {assessments_df['score'].median():.0f}")

    # Count multi-label awards
    multi_label_count = assessments_df['supporting_cet_ids'].apply(lambda x: len(x) > 0).sum()
    print(f"\n   Multi-Label Classification:")
    print(f"      Awards with 2+ CET areas: {multi_label_count:,} ({multi_label_count/len(assessments_df)*100:.1f}%)")

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
