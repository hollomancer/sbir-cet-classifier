#!/usr/bin/env python
"""Test NIH classification with enhanced API enrichment on 100 awards."""

import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from sbir_cet_classifier.data.bootstrap import load_bootstrap_csv
from sbir_cet_classifier.data.external.nih import NIHClient
from sbir_cet_classifier.data.solicitation_cache import SolicitationCache
from sbir_cet_classifier.features.fallback_enrichment import enrich_with_fallback
from sbir_cet_classifier.models.applicability import ApplicabilityModel, TrainingExample


def main():
    """Run test classification on 100 NIH awards."""
    print("="*60)
    print("NIH SBIR TEST CLASSIFICATION (100 awards)")
    print("="*60)
    
    # Load awards
    print("\n=== Loading Awards ===")
    result = load_bootstrap_csv(Path("award_data.csv"))
    nih_awards = [
        award for award in result.awards
        if 'health' in award.agency.lower() or 'hhs' in award.agency.lower() or 'nih' in award.agency.lower()
    ][:100]
    
    print(f"✓ Loaded {len(nih_awards)} NIH awards")
    
    # Initialize enrichment
    cache = SolicitationCache()
    client = NIHClient()
    
    # Enrich awards
    print("\n=== Enriching Awards with NIH API ===")
    enriched = []
    stats = {
        'cache_hits': 0,
        'api_calls': 0,
        'api_success': 0,
        'fallback': 0,
        'total_enrichment_chars': 0,
    }
    
    for i, award in enumerate(nih_awards):
        base_text = f"{award.abstract or ''} {' '.join(award.keywords)}"
        
        # Try NIH API if solicitation_id exists
        if award.solicitation_id:
            cached = cache.get('nih', award.solicitation_id)
            if cached:
                enriched_text = f"{base_text} {cached.description} {' '.join(cached.technical_keywords)}"
                stats['cache_hits'] += 1
                stats['total_enrichment_chars'] += len(enriched_text) - len(base_text)
            else:
                try:
                    result = client.lookup_solicitation(project_number=award.solicitation_id)
                    stats['api_calls'] += 1
                    
                    if result:
                        cache.put(
                            solicitation_id=award.solicitation_id,
                            api_source='nih',
                            description=result.description,
                            technical_keywords=result.technical_keywords
                        )
                        enriched_text = f"{base_text} {result.description} {' '.join(result.technical_keywords)}"
                        stats['api_success'] += 1
                        stats['total_enrichment_chars'] += len(enriched_text) - len(base_text)
                        print(f"  [{i+1}/100] API success: {award.solicitation_id} (+{len(enriched_text)-len(base_text)} chars)")
                    else:
                        enriched_text = enrich_with_fallback(award, base_text)
                        stats['fallback'] += 1
                        stats['total_enrichment_chars'] += len(enriched_text) - len(base_text)
                except Exception as e:
                    enriched_text = enrich_with_fallback(award, base_text)
                    stats['fallback'] += 1
                    stats['total_enrichment_chars'] += len(enriched_text) - len(base_text)
        else:
            enriched_text = enrich_with_fallback(award, base_text)
            stats['fallback'] += 1
            stats['total_enrichment_chars'] += len(enriched_text) - len(base_text)
        
        enriched.append((award, enriched_text))
    
    print(f"\n✓ Enrichment complete:")
    print(f"  Cache hits: {stats['cache_hits']}")
    print(f"  API calls: {stats['api_calls']} (success: {stats['api_success']})")
    print(f"  Fallback: {stats['fallback']}")
    print(f"  Avg enrichment: {stats['total_enrichment_chars']/len(nih_awards):.0f} chars/award")
    
    # Train classifier
    print("\n=== Training Classifier ===")
    cet_keywords = {
        'biotechnology': ['gene', 'biotech', 'protein', 'cell', 'dna', 'rna', 'biology'],
        'medical_devices': ['device', 'diagnostic', 'medical', 'clinical', 'patient', 'health'],
        'artificial_intelligence': ['ai', 'machine learning', 'neural', 'deep learning', 'algorithm'],
    }
    
    training_examples = []
    for award, text in enriched[:100]:
        text_lower = text.lower()
        scores = {cet: sum(1 for kw in keywords if kw in text_lower) 
                  for cet, keywords in cet_keywords.items()}
        cet_id = max(scores, key=scores.get) if max(scores.values()) > 0 else 'biotechnology'
        training_examples.append(TrainingExample(award.award_id, text, cet_id))
    
    model = ApplicabilityModel()
    model.fit(training_examples)
    print(f"✓ Model trained on {len(training_examples)} examples")
    
    # Classify
    print("\n=== Classifying Awards ===")
    results = []
    for award, text in enriched:
        prediction = model.predict(award.award_id, text)
        results.append({
            'award_id': award.award_id,
            'primary_cet': prediction.primary_cet_id,
            'primary_score': prediction.primary_score,
            'classification': prediction.classification,
            'text_length': len(text),
        })
    
    df = pd.DataFrame(results)
    
    # Generate report
    report = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_awards': len(df),
        },
        'enrichment': stats,
        'classification_distribution': {
            'High': int((df['classification'] == 'High').sum()),
            'Medium': int((df['classification'] == 'Medium').sum()),
            'Low': int((df['classification'] == 'Low').sum()),
        },
        'cet_distribution': df['primary_cet'].value_counts().to_dict(),
        'score_statistics': {
            'mean': float(df['primary_score'].mean()),
            'median': float(df['primary_score'].median()),
            'std': float(df['primary_score'].std()),
            'min': float(df['primary_score'].min()),
            'max': float(df['primary_score'].max()),
        },
    }
    
    # Save report
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / f"nih_test_100_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"NIH TEST CLASSIFICATION REPORT (100 awards)")
    print(f"{'='*60}")
    print(f"\nEnrichment:")
    print(f"  API success: {stats['api_success']}/{stats['api_calls']} calls")
    print(f"  Avg enrichment: {stats['total_enrichment_chars']/len(nih_awards):.0f} chars/award")
    print(f"\nClassification Distribution:")
    for level in ['High', 'Medium', 'Low']:
        count = report['classification_distribution'][level]
        pct = count / len(df) * 100
        print(f"  {level:8s}: {count:3} ({pct:5.1f}%)")
    print(f"\nTop CET Areas:")
    for cet, count in list(report['cet_distribution'].items())[:5]:
        pct = count / len(df) * 100
        print(f"  {cet:30s}: {count:3} ({pct:5.1f}%)")
    print(f"\nScore Statistics:")
    print(f"  Mean:   {report['score_statistics']['mean']:.1f}")
    print(f"  Median: {report['score_statistics']['median']:.1f}")
    print(f"  Range:  {report['score_statistics']['min']:.1f} - {report['score_statistics']['max']:.1f}")
    print(f"\n{'='*60}")
    print(f"✓ Report saved: {report_path}")


if __name__ == "__main__":
    main()
