#!/usr/bin/env python
"""Production classification of all NIH SBIR awards with enrichment and reporting."""

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


def load_nih_awards(csv_path: Path, limit: int = None):
    """Load NIH awards from bootstrap CSV."""
    print(f"=== Loading Awards from {csv_path} ===")
    
    result = load_bootstrap_csv(csv_path)
    
    # Filter to NIH awards only
    nih_awards = [
        award for award in result.awards
        if 'health' in award.agency.lower() or 'hhs' in award.agency.lower() or 'nih' in award.agency.lower()
    ]
    
    if limit:
        nih_awards = nih_awards[:limit]
    
    print(f"✓ Loaded {len(nih_awards)} NIH awards (from {len(result.awards)} total)")
    print(f"  Total rows: {result.total_rows}")
    print(f"  Loaded: {result.loaded_count}")
    print(f"  Skipped: {result.skipped_count}")
    
    return nih_awards, result


def enrich_awards_batch(awards, cache, client, use_api=True):
    """Enrich awards with NIH API or fallback."""
    print(f"\n=== Enriching {len(awards)} Awards ===")
    
    enriched = []
    stats = {
        'cache_hits': 0,
        'api_calls': 0,
        'api_success': 0,
        'fallback': 0,
        'total_enrichment_chars': 0,
    }
    
    for i, award in enumerate(awards):
        if (i + 1) % 100 == 0:
            print(f"  Progress: {i+1}/{len(awards)} awards...")
        
        # Build base text
        base_text = f"{award.abstract or ''} {' '.join(award.keywords)}"
        
        # Try enrichment if solicitation_id exists
        if use_api and award.solicitation_id:
            # Check cache
            cached = cache.get('nih', award.solicitation_id)
            if cached:
                enriched_text = f"{base_text} {cached.description} {' '.join(cached.technical_keywords)}"
                stats['cache_hits'] += 1
                stats['total_enrichment_chars'] += len(enriched_text) - len(base_text)
            else:
                # Try API
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
                    else:
                        # Fallback enrichment
                        enriched_text = enrich_with_fallback(award, base_text)
                        stats['fallback'] += 1
                        stats['total_enrichment_chars'] += len(enriched_text) - len(base_text)
                except Exception as e:
                    # Fallback on error
                    enriched_text = enrich_with_fallback(award, base_text)
                    stats['fallback'] += 1
        else:
            # Use fallback enrichment
            enriched_text = enrich_with_fallback(award, base_text)
            stats['fallback'] += 1
            stats['total_enrichment_chars'] += len(enriched_text) - len(base_text)
        
        enriched.append((award, enriched_text))
    
    print(f"\n✓ Enrichment complete:")
    print(f"  Cache hits: {stats['cache_hits']}")
    print(f"  API calls: {stats['api_calls']} (success: {stats['api_success']})")
    print(f"  Fallback: {stats['fallback']}")
    print(f"  Avg enrichment: {stats['total_enrichment_chars']/len(awards):.0f} chars/award")
    
    return enriched, stats


def train_classifier(enriched_awards, sample_size=1000):
    """Train classifier on sample of awards."""
    print(f"\n=== Training Classifier ===")
    
    # Use first N awards for training with mock labels
    # In production, these would come from existing classifications
    training_sample = enriched_awards[:min(sample_size, len(enriched_awards))]
    
    # Assign mock CET labels based on keywords (simplified for demo)
    cet_keywords = {
        'biotechnology': ['gene', 'biotech', 'protein', 'cell', 'dna', 'rna', 'biology'],
        'medical_devices': ['device', 'diagnostic', 'medical', 'clinical', 'patient', 'health'],
        'artificial_intelligence': ['ai', 'machine learning', 'neural', 'deep learning', 'algorithm'],
        'advanced_materials': ['material', 'nano', 'polymer', 'composite'],
        'data_analytics': ['data', 'analytics', 'visualization', 'database'],
    }
    
    training_examples = []
    for award, text in training_sample:
        # Simple keyword matching for demo
        text_lower = text.lower()
        scores = {cet: sum(1 for kw in keywords if kw in text_lower) 
                  for cet, keywords in cet_keywords.items()}
        cet_id = max(scores, key=scores.get) if max(scores.values()) > 0 else 'biotechnology'
        
        training_examples.append(TrainingExample(award.award_id, text, cet_id))
    
    model = ApplicabilityModel()
    start = time.time()
    model.fit(training_examples)
    train_time = time.time() - start
    
    print(f"✓ Model trained on {len(training_examples)} examples in {train_time:.2f}s")
    
    return model


def classify_awards_batch(model, enriched_awards):
    """Classify all awards."""
    print(f"\n=== Classifying {len(enriched_awards)} Awards ===")
    
    results = []
    start = time.time()
    
    for i, (award, text) in enumerate(enriched_awards):
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start
            rate = (i + 1) / elapsed
            print(f"  Progress: {i+1}/{len(enriched_awards)} ({rate:.0f} awards/sec)")
        
        prediction = model.predict(award.award_id, text)
        
        results.append({
            'award_id': award.award_id,
            'agency': award.agency,
            'firm_name': award.firm_name,
            'firm_state': award.firm_state,
            'award_amount': award.award_amount,
            'award_date': award.award_date.isoformat(),
            'award_year': award.award_date.year,
            'phase': award.phase,
            'topic_code': award.topic_code,
            'primary_cet': prediction.primary_cet_id,
            'primary_score': prediction.primary_score,
            'classification': prediction.classification,
            'supporting_cet_1': prediction.supporting_ranked[0][0] if len(prediction.supporting_ranked) > 0 else None,
            'supporting_score_1': prediction.supporting_ranked[0][1] if len(prediction.supporting_ranked) > 0 else None,
            'supporting_cet_2': prediction.supporting_ranked[1][0] if len(prediction.supporting_ranked) > 1 else None,
            'supporting_score_2': prediction.supporting_ranked[1][1] if len(prediction.supporting_ranked) > 1 else None,
            'text_length': len(text),
            'has_abstract': bool(award.abstract),
            'has_solicitation': bool(award.solicitation_id),
        })
    
    total_time = time.time() - start
    print(f"\n✓ Classification complete in {total_time:.2f}s ({len(results)/total_time:.0f} awards/sec)")
    
    return results, total_time


def generate_report(results, enrichment_stats, classification_time, output_dir: Path):
    """Generate comprehensive report."""
    print(f"\n=== Generating Report ===")
    
    df = pd.DataFrame(results)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save detailed results
    results_path = output_dir / f"nih_classification_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(results_path, index=False)
    print(f"✓ Saved detailed results: {results_path}")
    
    # Generate summary statistics
    report = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'total_awards': len(df),
            'classification_time_seconds': classification_time,
            'throughput_awards_per_second': len(df) / classification_time,
        },
        'enrichment': enrichment_stats,
        'classification_distribution': {
            'High': int((df['classification'] == 'High').sum()),
            'Medium': int((df['classification'] == 'Medium').sum()),
            'Low': int((df['classification'] == 'Low').sum()),
        },
        'cet_distribution': df['primary_cet'].value_counts().head(10).to_dict(),
        'score_statistics': {
            'mean': float(df['primary_score'].mean()),
            'median': float(df['primary_score'].median()),
            'std': float(df['primary_score'].std()),
            'min': float(df['primary_score'].min()),
            'max': float(df['primary_score'].max()),
        },
        'funding_by_cet': df.groupby('primary_cet')['award_amount'].sum().sort_values(ascending=False).head(10).to_dict(),
        'phase_distribution': df['phase'].value_counts().to_dict(),
        'year_distribution': df['award_year'].value_counts().sort_index().to_dict(),
        'state_distribution': df['firm_state'].value_counts().head(10).to_dict(),
        'data_quality': {
            'has_abstract': int(df['has_abstract'].sum()),
            'has_solicitation': int(df['has_solicitation'].sum()),
            'avg_text_length': float(df['text_length'].mean()),
        },
    }
    
    # Save JSON report
    report_path = output_dir / f"nih_classification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"✓ Saved JSON report: {report_path}")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"NIH SBIR CLASSIFICATION REPORT")
    print(f"{'='*60}")
    print(f"\nTotal Awards: {len(df):,}")
    print(f"Classification Time: {classification_time:.2f}s ({len(df)/classification_time:.0f} awards/sec)")
    print(f"\nClassification Distribution:")
    for level in ['High', 'Medium', 'Low']:
        count = report['classification_distribution'][level]
        pct = count / len(df) * 100
        print(f"  {level:8s}: {count:5,} ({pct:5.1f}%)")
    
    print(f"\nTop 10 CET Areas:")
    for cet, count in list(report['cet_distribution'].items())[:10]:
        pct = count / len(df) * 100
        funding = report['funding_by_cet'].get(cet, 0)
        print(f"  {cet:30s}: {count:5,} awards ({pct:5.1f}%) | ${funding/1e6:8.1f}M")
    
    print(f"\nScore Statistics:")
    print(f"  Mean:   {report['score_statistics']['mean']:.1f}")
    print(f"  Median: {report['score_statistics']['median']:.1f}")
    print(f"  Std:    {report['score_statistics']['std']:.1f}")
    print(f"  Range:  {report['score_statistics']['min']:.1f} - {report['score_statistics']['max']:.1f}")
    
    print(f"\nData Quality:")
    print(f"  Has abstract:      {report['data_quality']['has_abstract']:5,} ({report['data_quality']['has_abstract']/len(df)*100:.1f}%)")
    print(f"  Has solicitation:  {report['data_quality']['has_solicitation']:5,} ({report['data_quality']['has_solicitation']/len(df)*100:.1f}%)")
    print(f"  Avg text length:   {report['data_quality']['avg_text_length']:.0f} chars")
    
    print(f"\nEnrichment Stats:")
    print(f"  Cache hits:  {enrichment_stats['cache_hits']:5,}")
    print(f"  API calls:   {enrichment_stats['api_calls']:5,} (success: {enrichment_stats['api_success']})")
    print(f"  Fallback:    {enrichment_stats['fallback']:5,}")
    
    print(f"\n{'='*60}")
    
    return report


def main():
    """Run production NIH classification."""
    print("="*60)
    print("NIH SBIR PRODUCTION CLASSIFICATION")
    print("="*60)
    
    # Configuration
    csv_path = Path("award_data.csv")
    output_dir = Path("reports")
    limit = None  # Set to number to limit for testing, None for all
    use_api = False  # Set to False to skip API calls (faster for large batches)
    
    # Load awards
    awards, load_result = load_nih_awards(csv_path, limit=limit)
    
    if not awards:
        print("✗ No NIH awards found")
        return
    
    # Initialize enrichment
    cache = SolicitationCache()
    client = NIHClient() if use_api else None
    
    # Enrich awards
    enriched, enrichment_stats = enrich_awards_batch(awards, cache, client, use_api=use_api)
    
    # Train classifier
    model = train_classifier(enriched, sample_size=min(1000, len(enriched)))
    
    # Classify all awards
    results, classification_time = classify_awards_batch(model, enriched)
    
    # Generate report
    report = generate_report(results, enrichment_stats, classification_time, output_dir)
    
    # Cleanup
    cache.close()
    
    print(f"\n✓ Production classification complete")
    print(f"  Results: {output_dir}")


if __name__ == '__main__':
    main()
