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


def load_and_normalize_csv(csv_path: Path, max_rows: int = None) -> pd.DataFrame:
    """Load the award_data-3.csv and normalize it to the expected schema."""
    print(f"📂 Loading CSV from {csv_path}...")
    if max_rows:
        print(f"   (Limited to first {max_rows:,} rows for processing)")

    # Read CSV with optimized dtypes and row limit
    dtype_map = {
        "Company": "string",
        "Award Title": "string", 
        "Agency": "category",
        "Branch": "string",
        "Phase": "category",
        "Contract": "string",
        "Topic Code": "string",
        "State": "category",
        "City": "string",
        "Abstract": "string",
    }
    
    df = pd.read_csv(csv_path, dtype=dtype_map, nrows=max_rows)
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

    # Normalize data types efficiently
    df["sub_agency"] = df.get("sub_agency", "").fillna("").astype("string")
    df["topic_code"] = df.get("topic_code", "UNKNOWN").fillna("UNKNOWN").astype("string")
    df["abstract"] = df.get("abstract", "").fillna("").astype("string")
    df["firm_name"] = df.get("firm_name", "Unknown").fillna("Unknown").astype("string")
    df["firm_city"] = df.get("firm_city", "Unknown").fillna("Unknown").astype("string")
    df["firm_state"] = df.get("firm_state", "XX").fillna("XX").astype("category")
    df["award_amount"] = pd.to_numeric(df.get("award_amount", 0), errors="coerce").fillna(0)
    df["award_date"] = pd.to_datetime(df.get("award_date"), errors="coerce")
    df["fiscal_year"] = pd.to_numeric(df.get("fiscal_year"), errors="coerce").fillna(2025).astype("int16")

    # Normalize phase values
    phase_mapping = {
        "Phase I": "I",
        "Phase II": "II", 
        "Phase III": "III",
        "SBIR Phase I": "I",
        "SBIR Phase II": "II",
        "STTR Phase II": "II",
    }
    df["phase"] = df["phase"].map(lambda x: phase_mapping.get(x, "Other") if pd.notna(x) else "Other").astype("category")

    # Generate synthetic IDs for NULL/missing contracts
    null_mask = df["award_id"].isna() | (df["award_id"] == "")
    null_count = null_mask.sum()

    if null_count > 0:
        print(f"   Generating synthetic IDs for {null_count:,} awards with missing contracts...")
        
        def generate_synthetic_id(row):
            """Generate unique ID from award attributes."""
            composite = f"{row['firm_name']}|{row['title']}|{row['award_date']}|{row['award_amount']}|{row['agency']}"
            hash_val = hashlib.md5(composite.encode()).hexdigest()[:16]
            return f"SYNTH-{hash_val}"

        df.loc[null_mask, "award_id"] = df[null_mask].apply(generate_synthetic_id, axis=1)

    # Deduplicate efficiently
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
    """Classify awards against CET areas using multi-label weighted classification with context rules and agency/branch priors."""
    print(f"🤖 Classifying {len(awards_df):,} awards against CET taxonomy...")
    print(f"   Using v5 classifier with Agency/Branch priors, lower None score, and multi-label threshold (20)...")
    print(f"   (This will take approximately {len(awards_df) / 750:.0f} seconds...)")

    # Agency-based CET priors: boost CET scores based on funding agency
    AGENCY_CET_PRIORS = {
        "Department of Defense": {
            "hypersonics": 15,
            "autonomous_systems": 15,
            "directed_energy": 15,
            "advanced_materials": 10,
            "cybersecurity": 10,
            "semiconductors": 10,
            "advanced_communications": 10,
        },
        "Department of Health and Human Services": {
            "biotechnology": 20,
            "medical_devices": 20,
            "artificial_intelligence": 5,  # Medical AI is common
        },
        "National Aeronautics and Space Administration": {
            "space_technology": 25,
            "advanced_materials": 15,
            "autonomous_systems": 10,
            "renewable_energy": 10,  # Space solar
        },
        "Department of Energy": {
            "renewable_energy": 20,
            "energy_storage": 20,
            "quantum_computing": 15,
            "advanced_materials": 10,
            "semiconductors": 10,
        },
        "National Science Foundation": {
            # NSF funds all areas - give small boost to all non-none CETs
            "_all_cets": 5,
        },
        "Department of Agriculture": {
            "biotechnology": 15,
            "environmental_tech": 15,
        },
        "Environmental Protection Agency": {
            "environmental_tech": 25,
            "renewable_energy": 15,
        },
        "Department of Commerce": {
            "semiconductors": 15,
            "advanced_communications": 15,
            "quantum_computing": 10,
        },
    }

    # Branch-based CET priors: more specific than agency
    BRANCH_CET_PRIORS = {
        "National Institutes of Health": {
            "medical_devices": 25,
            "biotechnology": 25,
            "artificial_intelligence": 10,  # Medical AI
        },
        "Air Force": {
            "hypersonics": 20,
            "space_technology": 15,
            "autonomous_systems": 15,
            "directed_energy": 10,
            "advanced_materials": 10,
        },
        "Navy": {
            "autonomous_systems": 15,
            "advanced_materials": 15,
            "directed_energy": 10,
            "cybersecurity": 10,
        },
        "Army": {
            "autonomous_systems": 15,
            "cybersecurity": 15,
            "advanced_materials": 10,
            "medical_devices": 5,  # Combat medicine
        },
        "Missile Defense Agency": {
            "hypersonics": 25,
            "directed_energy": 20,
            "space_technology": 15,
        },
        "Defense Advanced Research Projects Agency": {
            "quantum_computing": 15,
            "artificial_intelligence": 15,
            "biotechnology": 15,
            "autonomous_systems": 15,
            "hypersonics": 15,
            "directed_energy": 15,
        },
        "Defense Health Agency": {
            "medical_devices": 25,
            "biotechnology": 20,
        },
    }

    def apply_agency_prior(cet_scores: dict, agency: str) -> dict:
        """Apply agency-based CET priors."""
        if agency in AGENCY_CET_PRIORS:
            priors = AGENCY_CET_PRIORS[agency]
            for cet_id, boost in priors.items():
                if cet_id == "_all_cets":
                    # Boost all CETs except none
                    for cet in cet_scores:
                        if cet != "none":
                            cet_scores[cet] = cet_scores.get(cet, 0) + boost
                else:
                    cet_scores[cet_id] = cet_scores.get(cet_id, 0) + boost
        return cet_scores

    def apply_branch_prior(cet_scores: dict, branch: str) -> dict:
        """Apply branch-based CET priors."""
        if pd.notna(branch) and branch in BRANCH_CET_PRIORS:
            priors = BRANCH_CET_PRIORS[branch]
            for cet_id, boost in priors.items():
                cet_scores[cet_id] = cet_scores.get(cet_id, 0) + boost
        return cet_scores

    # Enhanced keyword matching with weighted importance and negative keywords
    # Format: {cet_id: {"core": [...], "related": [...], "negative": [...]}}
    cet_keywords = {
        "quantum_computing": {
            "core": ["quantum computing", "quantum computer", "quantum algorithm", "quantum processor"],
            "related": ["qubit", "quantum gate", "quantum circuit", "quantum software"],
            "negative": ["quantum mechanics", "quantum chemistry", "quantum field theory", "quantum dot"]
        },
        "quantum_sensing": {
            "core": ["quantum sensing", "quantum sensor", "quantum measurement", "quantum metrology"],
            "related": ["quantum detector", "atomic clock", "quantum magnetometer"],
            "negative": []
        },
        "artificial_intelligence": {
            "core": ["artificial intelligence research", "deep learning framework", "neural network architecture", "ai system"],
            "related": ["convolutional neural", "recurrent neural", "transformer model", "generative adversarial"],
            "negative": [
                # Medical AI should go to medical_devices
                "ai-powered diagnostic", "ai-based diagnosis", "ai medical imaging",
                # Manufacturing AI should go to advanced_manufacturing
                "ai-optimized manufacturing", "ai process control", "ai quality control",
                # Generic tool usage (not AI focus)
                "using machine learning", "using ai", "leveraging ml", "ml-based analysis",
                "ai-assisted", "ai-enhanced", "ml-enabled"
            ]
        },
        "biotechnology": {
            "core": ["biotechnology", "synthetic biology", "genetic engineering", "crispr", "gene therapy"],
            "related": ["biotech", "genomics", "biomanufacturing", "protein engineering", "gene editing", "bioreactor"],
            "negative": ["biomedical device", "medical diagnostic"]
        },
        "hypersonics": {
            "core": ["hypersonic flight", "hypersonic vehicle", "hypersonic weapon", "mach 5"],
            "related": ["scramjet", "ramjet", "high-speed flight", "supersonic combustion"],
            "negative": ["supersonic aircraft", "subsonic"]
        },
        "thermal_protection": {
            "core": ["thermal protection system", "heat shield", "tps", "re-entry thermal"],
            "related": ["ablative material", "thermal barrier", "high-temperature protection"],
            "negative": ["thermal management", "cooling system", "thermal insulation"]
        },
        "advanced_materials": {
            "core": ["metamaterial", "nanomaterial", "smart material", "advanced composite material"],
            "related": ["graphene", "carbon nanotube", "nanostructure", "functionally graded", "shape memory alloy"],
            "negative": ["standard composite", "conventional material"]
        },
        "cybersecurity": {
            "core": ["cybersecurity", "information security", "network security", "cyber defense"],
            "related": ["encryption", "cryptography", "intrusion detection", "penetration testing", "vulnerability assessment"],
            "negative": ["physical security", "security system"]
        },
        "autonomous_systems": {
            "core": ["autonomous system", "autonomous vehicle", "self-driving", "autonomous navigation"],
            "related": ["unmanned aerial", "uav", "drone", "autonomous robot", "autonomous control"],
            "negative": ["remote control", "teleoperated", "manual control", "automated"]
        },
        "semiconductors": {
            "core": ["semiconductor manufacturing", "microelectronics", "integrated circuit", "chip fabrication"],
            "related": ["cmos", "transistor", "wafer", "asic", "fpga", "semiconductor device"],
            "negative": ["using semiconductor", "semiconductor-based sensor"]
        },
        "space_technology": {
            "core": ["spacecraft", "satellite system", "space mission", "orbital platform"],
            "related": ["space propulsion", "launch vehicle", "orbital mechanics", "space environment"],
            "negative": ["cyberspace", "workspace", "aerospace material", "space-based sensor"]
        },
        "energy_storage": {
            "core": ["energy storage system", "battery technology", "electrochemical storage", "grid storage"],
            "related": ["lithium-ion battery", "solid-state battery", "supercapacitor", "energy storage device"],
            "negative": ["data storage", "battery-powered", "using battery"]
        },
        "renewable_energy": {
            "core": ["renewable energy", "solar energy system", "wind energy system", "photovoltaic system"],
            "related": ["solar panel", "solar cell", "wind turbine", "renewable power", "clean energy"],
            "negative": ["solar radiation", "wind tunnel", "solar heating"]
        },
        "medical_devices": {
            "core": ["medical device", "diagnostic device", "therapeutic device", "medical imaging device"],
            "related": ["clinical diagnostic", "patient monitoring", "surgical instrument", "prosthetic", "implantable device"],
            "negative": ["medical research", "drug development", "pharmaceutical"]
        },
    }

    # Context rules: If certain keyword combinations exist, boost specific CET
    # Format: {cet_id: [(keywords_required, boost_points)]}
    context_rules = {
        "medical_devices": [
            (["ai", "diagnostic"], 20),      # AI + diagnostic → medical device
            (["ai", "medical"], 20),          # AI + medical → medical device
            (["machine learning", "clinical"], 20),  # ML + clinical → medical device
            (["neural network", "patient"], 20),     # NN + patient → medical device
        ],
        "advanced_manufacturing": [
            (["ai", "manufacturing"], 20),    # AI + manufacturing → manufacturing
            (["machine learning", "production"], 20),  # ML + production → manufacturing
            (["ai", "process control"], 20),  # AI + process control → manufacturing
        ],
        "autonomous_systems": [
            (["ai", "autonomous"], 15),       # AI + autonomous → autonomous systems
            (["machine learning", "robot"], 15),  # ML + robot → autonomous
        ],
    }

    # Classify each award with multi-label support and context rules
    assessments = []
    ingested_at = datetime.now(timezone.utc)
    context_rules_applied = 0

    for idx, row in awards_df.iterrows():
        abstract = str(row.get("abstract", "")).lower()
        title = str(row.get("title", "")).lower()
        agency = str(row.get("agency", ""))
        branch = str(row.get("sub_agency", ""))

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

        # Apply context rules to boost specific CETs when keyword combinations exist
        for cet_id, rules in context_rules.items():
            for required_keywords, boost_points in rules:
                if all(kw in combined_text for kw in required_keywords):
                    if cet_id in cet_scores:
                        cet_scores[cet_id] += boost_points
                    else:
                        cet_scores[cet_id] = boost_points
                    context_rules_applied += 1

        # Apply agency prior (NEW in v5)
        cet_scores = apply_agency_prior(cet_scores, agency)

        # Apply branch prior (NEW in v5)
        cet_scores = apply_branch_prior(cet_scores, branch)

        # If no matches, assign to None category (uncategorized) with lower score
        if not cet_scores:
            cet_scores = {"none": 20}  # CHANGED: Was 30, now 20 (will normalize to 33 instead of 42)

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
        supporting_cet_ids = [cet_id for cet_id, score in top_cets[1:] if score >= 20]  # Only if score >= 20 (lowered from 30)

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
            "generation_method": "automated_v5_with_context",
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

    print(f"\n   Context Rules Applied:")
    print(f"      Total rule activations: {context_rules_applied:,}")
    print(f"      Avg per award: {context_rules_applied/len(assessments_df):.3f}")

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
