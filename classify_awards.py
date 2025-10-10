#!/usr/bin/env python
"""Classify SBIR awards with enrichment and measure impact."""

import time
from pathlib import Path

import pandas as pd

from sbir_cet_classifier.data.bootstrap import load_bootstrap_csv
from sbir_cet_classifier.features.fallback_enrichment import enrich_with_fallback
from sbir_cet_classifier.models.applicability import (
    ApplicabilityModel,
    TrainingExample,
)


def classify_with_enrichment(awards_path: Path, sample_size: int = 100):
    """Classify awards with and without enrichment to measure impact.
    
    Args:
        awards_path: Path to awards CSV
        sample_size: Number of awards to classify
    """
    print(f"=== Classification with Enrichment ===\n")
    print(f"Loading awards from {awards_path}...")
    
    # Load awards
    result = load_bootstrap_csv(awards_path)
    awards = result.awards[:sample_size]
    print(f"Loaded {len(awards)} awards\n")
    
    # Create training examples (using first 50 for training, rest for testing)
    train_size = min(50, len(awards) // 2)
    test_size = len(awards) - train_size
    
    print(f"Training set: {train_size} awards")
    print(f"Test set: {test_size} awards\n")
    
    # Assign mock CET labels for demonstration
    # In production, these would come from existing classifications
    cet_labels = ["ai", "quantum", "biotech", "energy", "materials", "cyber", "space", "manufacturing"]
    
    # Build training examples WITHOUT enrichment
    print("=== Training Model WITHOUT Enrichment ===")
    train_examples_baseline = []
    for i, award in enumerate(awards[:train_size]):
        text = f"{award.abstract or ''} {' '.join(award.keywords)}"
        cet_id = cet_labels[i % len(cet_labels)]  # Mock label
        train_examples_baseline.append(TrainingExample(award.award_id, text, cet_id))
    
    start = time.time()
    model_baseline = ApplicabilityModel()
    model_baseline.fit(train_examples_baseline)
    train_time_baseline = time.time() - start
    print(f"Training time: {train_time_baseline:.2f}s\n")
    
    # Build training examples WITH enrichment
    print("=== Training Model WITH Enrichment ===")
    train_examples_enriched = []
    for i, award in enumerate(awards[:train_size]):
        text = f"{award.abstract or ''} {' '.join(award.keywords)}"
        enriched_text = enrich_with_fallback(award, text)
        cet_id = cet_labels[i % len(cet_labels)]  # Same mock labels
        train_examples_enriched.append(TrainingExample(award.award_id, enriched_text, cet_id))
    
    start = time.time()
    model_enriched = ApplicabilityModel()
    model_enriched.fit(train_examples_enriched)
    train_time_enriched = time.time() - start
    print(f"Training time: {train_time_enriched:.2f}s\n")
    
    # Test on remaining awards
    print("=== Testing on Held-Out Awards ===\n")
    
    results_baseline = []
    results_enriched = []
    
    for award in awards[train_size:]:
        # Baseline prediction
        text = f"{award.abstract or ''} {' '.join(award.keywords)}"
        pred_baseline = model_baseline.predict(award.award_id, text)
        results_baseline.append({
            "award_id": award.award_id,
            "primary_cet": pred_baseline.primary_cet_id,
            "score": pred_baseline.primary_score,
            "classification": pred_baseline.classification,
            "text_length": len(text),
        })
        
        # Enriched prediction
        enriched_text = enrich_with_fallback(award, text)
        pred_enriched = model_enriched.predict(award.award_id, enriched_text)
        results_enriched.append({
            "award_id": award.award_id,
            "primary_cet": pred_enriched.primary_cet_id,
            "score": pred_enriched.primary_score,
            "classification": pred_enriched.classification,
            "text_length": len(enriched_text),
        })
    
    # Compare results
    df_baseline = pd.DataFrame(results_baseline)
    df_enriched = pd.DataFrame(results_enriched)
    
    print("=== Results Comparison ===\n")
    print("Baseline (Award-Only):")
    print(f"  Avg score: {df_baseline['score'].mean():.1f}")
    print(f"  High confidence: {(df_baseline['classification'] == 'High').sum()} ({(df_baseline['classification'] == 'High').sum()/len(df_baseline)*100:.1f}%)")
    print(f"  Medium confidence: {(df_baseline['classification'] == 'Medium').sum()} ({(df_baseline['classification'] == 'Medium').sum()/len(df_baseline)*100:.1f}%)")
    print(f"  Low confidence: {(df_baseline['classification'] == 'Low').sum()} ({(df_baseline['classification'] == 'Low').sum()/len(df_baseline)*100:.1f}%)")
    print(f"  Avg text length: {df_baseline['text_length'].mean():.0f} chars")
    print()
    
    print("Enriched (Award + Solicitation Context):")
    print(f"  Avg score: {df_enriched['score'].mean():.1f}")
    print(f"  High confidence: {(df_enriched['classification'] == 'High').sum()} ({(df_enriched['classification'] == 'High').sum()/len(df_enriched)*100:.1f}%)")
    print(f"  Medium confidence: {(df_enriched['classification'] == 'Medium').sum()} ({(df_enriched['classification'] == 'Medium').sum()/len(df_enriched)*100:.1f}%)")
    print(f"  Low confidence: {(df_enriched['classification'] == 'Low').sum()} ({(df_enriched['classification'] == 'Low').sum()/len(df_enriched)*100:.1f}%)")
    print(f"  Avg text length: {df_enriched['text_length'].mean():.0f} chars")
    print()
    
    # Calculate improvements
    score_improvement = df_enriched['score'].mean() - df_baseline['score'].mean()
    high_conf_improvement = (df_enriched['classification'] == 'High').sum() - (df_baseline['classification'] == 'High').sum()
    text_increase = df_enriched['text_length'].mean() - df_baseline['text_length'].mean()
    
    print("=== Impact Summary ===\n")
    print(f"Score improvement: {score_improvement:+.1f} points")
    print(f"High confidence increase: {high_conf_improvement:+d} awards")
    print(f"Text enrichment: {text_increase:+.0f} chars avg ({text_increase/df_baseline['text_length'].mean()*100:+.1f}%)")
    print()
    
    # Show sample predictions
    print("=== Sample Predictions ===\n")
    for i in range(min(5, len(df_baseline))):
        print(f"{i+1}. Award {df_baseline.iloc[i]['award_id']}")
        print(f"   Baseline: {df_baseline.iloc[i]['primary_cet']} ({df_baseline.iloc[i]['score']:.0f}) - {df_baseline.iloc[i]['classification']}")
        print(f"   Enriched: {df_enriched.iloc[i]['primary_cet']} ({df_enriched.iloc[i]['score']:.0f}) - {df_enriched.iloc[i]['classification']}")
        if df_baseline.iloc[i]['primary_cet'] != df_enriched.iloc[i]['primary_cet']:
            print(f"   ⚠️  CET changed!")
        print()
    
    print("✅ Classification with enrichment complete")
    
    return {
        "baseline": df_baseline,
        "enriched": df_enriched,
        "score_improvement": score_improvement,
        "high_conf_improvement": high_conf_improvement,
    }


if __name__ == "__main__":
    results = classify_with_enrichment(Path("award_data.csv"), sample_size=100)
