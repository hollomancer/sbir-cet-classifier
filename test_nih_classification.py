#!/usr/bin/env python
"""Test classifier with NIH awards using real API enrichment."""

from datetime import date, datetime

import pandas as pd

from sbir_cet_classifier.common.schemas import Award
from sbir_cet_classifier.data.external.nih import NIHClient
from sbir_cet_classifier.data.solicitation_cache import SolicitationCache
from sbir_cet_classifier.models.applicability import ApplicabilityModel, TrainingExample


def create_nih_test_awards():
    """Create sample NIH SBIR awards for testing."""
    awards = [
        Award(
            award_id='NIH-001',
            agency='NIH',
            program='SBIR Phase II',
            topic_code='HC1',
            phase='II',
            award_year=2023,
            award_amount=1000000.0,
            firm_name='Medical Devices Inc',
            firm_city='Boston',
            firm_state='MA',
            abstract='Infant Head Malformation Detection System. Mobile app for detecting craniosynostosis in infants using computer vision.',
            keywords=['medical devices', 'pediatrics', 'computer vision'],
            solicitation_id='4R44DE031461-02',
            award_date=date(2023, 1, 1),
            is_export_controlled=False,
            source_version='test',
            ingested_at=datetime.now()
        ),
        Award(
            award_id='NIH-002',
            agency='NIH',
            program='SBIR Phase I',
            topic_code='BT1',
            phase='I',
            award_year=2023,
            award_amount=250000.0,
            firm_name='BioTech Solutions',
            firm_city='San Francisco',
            firm_state='CA',
            abstract='Gene Therapy Delivery Platform. Novel nanoparticle platform for targeted gene therapy delivery.',
            keywords=['biotechnology', 'gene therapy', 'nanotechnology'],
            solicitation_id='1R43GM123456-01',
            award_date=date(2023, 6, 1),
            is_export_controlled=False,
            source_version='test',
            ingested_at=datetime.now()
        ),
        Award(
            award_id='NIH-003',
            agency='NIH',
            program='SBIR Phase II',
            topic_code='AI1',
            phase='II',
            award_year=2023,
            award_amount=1500000.0,
            firm_name='AI Diagnostics Corp',
            firm_city='Seattle',
            firm_state='WA',
            abstract='AI-Powered Cancer Detection. Deep learning system for early cancer detection from medical imaging.',
            keywords=['artificial intelligence', 'medical imaging', 'cancer detection'],
            solicitation_id='2R44CA987654-02',
            award_date=date(2023, 3, 15),
            is_export_controlled=False,
            source_version='test',
            ingested_at=datetime.now()
        ),
    ]
    return awards


def enrich_awards(awards, cache):
    """Enrich awards with NIH API data."""
    client = NIHClient()
    enriched = []
    
    for award in awards:
        print(f"\n=== Enriching {award.award_id}: {award.firm_name} ===")
        
        # Check cache first
        cached = cache.get('nih', award.solicitation_id)
        if cached:
            print(f"✓ Found in cache: {len(cached.description)} chars")
            enriched_text = f"{award.abstract} {cached.description} {' '.join(cached.technical_keywords)}"
        else:
            # Try API
            result = client.lookup_solicitation(project_number=award.solicitation_id)
            if result:
                print(f"✓ Retrieved from API: {len(result.description)} chars")
                # Store in cache
                cache.put(
                    solicitation_id=award.solicitation_id,
                    api_source='nih',
                    description=result.description,
                    technical_keywords=result.technical_keywords
                )
                enriched_text = f"{award.abstract} {result.description} {' '.join(result.technical_keywords)}"
            else:
                print(f"✗ API returned no data, using award text only")
                enriched_text = f"{award.abstract} {' '.join(award.keywords)}"
        
        enriched.append((award, enriched_text))
    
    return enriched


def classify_awards(enriched_awards):
    """Classify awards using the applicability model."""
    print("\n=== Training Classifier ===")
    
    # Create training examples (mock labels for demo)
    # In production, these would come from existing classifications
    cet_mapping = {
        'HC1': 'medical_devices',
        'BT1': 'biotechnology',
        'AI1': 'artificial_intelligence',
    }
    
    training_examples = []
    for award, text in enriched_awards:
        cet_id = cet_mapping.get(award.topic_code, 'biotechnology')
        training_examples.append(TrainingExample(award.award_id, text, cet_id))
    
    # Train model
    model = ApplicabilityModel()
    model.fit(training_examples)
    print(f"✓ Model trained on {len(training_examples)} examples")
    
    # Classify each award
    print("\n=== Classification Results ===")
    results = []
    for award, text in enriched_awards:
        prediction = model.predict(award.award_id, text)
        
        results.append({
            'award_id': award.award_id,
            'firm': award.firm_name,
            'primary_cet': prediction.primary_cet_id,
            'score': prediction.primary_score,
            'classification': prediction.classification,
            'text_length': len(text),
        })
        
        print(f"\n{award.award_id}: {award.firm_name}")
        print(f"  Primary CET: {prediction.primary_cet_id}")
        print(f"  Score: {prediction.primary_score:.1f}")
        print(f"  Classification: {prediction.classification}")
        print(f"  Text length: {len(text)} chars")
        print(f"  Supporting CETs:")
        for cet_id, score in prediction.supporting_ranked[:3]:
            print(f"    - {cet_id}: {score:.1f}")
    
    return results


def main():
    """Run NIH classification test."""
    print("=== NIH Award Classification Test ===\n")
    
    # Create test awards
    awards = create_nih_test_awards()
    print(f"✓ Created {len(awards)} test NIH awards\n")
    
    # Enrich with NIH API
    cache = SolicitationCache()
    enriched = enrich_awards(awards, cache)
    cache.close()
    
    # Classify
    results = classify_awards(enriched)
    
    # Summary
    print("\n=== Summary ===")
    df = pd.DataFrame(results)
    print(f"\nTotal awards: {len(df)}")
    print(f"Average score: {df['score'].mean():.1f}")
    print(f"Average text length: {df['text_length'].mean():.0f} chars")
    print(f"\nClassification distribution:")
    print(df['classification'].value_counts())
    print(f"\nCET distribution:")
    print(df['primary_cet'].value_counts())
    
    print("\n✓ Test completed successfully")


if __name__ == '__main__':
    main()
