#!/usr/bin/env python
"""Test NIH API enrichment integration."""

from datetime import datetime

from sbir_cet_classifier.common.schemas import Award
from sbir_cet_classifier.data.external.nih import NIHClient
from sbir_cet_classifier.data.solicitation_cache import SolicitationCache


def test_nih_enrichment():
    """Test NIH API enrichment with real project data."""
    print("=== NIH API Enrichment Test ===\n")
    
    # Create test NIH award with project number as solicitation_id
    award = Award(
        award_id='TEST-NIH-001',
        agency='NIH',
        program='SBIR Phase II',
        topic_code='HC1',
        phase='II',
        award_year=2023,
        award_amount=1000000.0,
        firm_name='Test Company',
        firm_city='Boston',
        firm_state='MA',
        company_name='Test Company',
        project_title='Infant Head Malformation Detection',
        abstract='Mobile app for detecting craniosynostosis in infants.',
        keywords=['medical devices', 'pediatrics'],
        solicitation_id='4R44DE031461-02',  # NIH project number
        award_date=datetime(2023, 1, 1),
        is_export_controlled=False,
        source_version='test',
        ingested_at=datetime.now()
    )
    
    print(f"Test Award: {award.award_id}")
    print(f"Agency: {award.agency}")
    print(f"Solicitation ID: {award.solicitation_id}")
    print(f"Original abstract length: {len(award.abstract)} chars")
    print(f"Original keywords: {len(award.keywords)}\n")
    
    # Test NIH API lookup
    print("=== Testing NIH API Lookup ===")
    client = NIHClient()
    result = client.lookup_solicitation(project_number=award.solicitation_id)
    
    if result:
        print(f"✓ NIH API returned data")
        print(f"  Description length: {len(result.description)} chars")
        print(f"  Keywords: {len(result.technical_keywords)} terms")
        print(f"\n  First 200 chars:")
        print(f"  {result.description[:200]}...")
        print(f"\n  First 5 keywords:")
        for kw in result.technical_keywords[:5]:
            print(f"    - {kw}")
    else:
        print("✗ NIH API returned no data")
        return
    
    # Test cache integration
    print("\n=== Testing Cache Integration ===")
    cache = SolicitationCache()
    
    # Store in cache
    cache.put(
        solicitation_id=award.solicitation_id,
        api_source='nih',
        description=result.description,
        technical_keywords=result.technical_keywords
    )
    print(f"✓ Stored in cache")
    
    # Retrieve from cache
    cached = cache.get('nih', award.solicitation_id)
    if cached:
        print(f"✓ Retrieved from cache")
        print(f"  Description length: {len(cached.description)} chars")
        print(f"  Keywords: {len(cached.technical_keywords)} terms")
    else:
        print("✗ Cache retrieval failed")
    
    # Test enrichment
    print("\n=== Testing Text Enrichment ===")
    original_text = f"{award.abstract} {' '.join(award.keywords)}"
    enriched_text = f"{original_text} {result.description} {' '.join(result.technical_keywords)}"
    
    print(f"Original text length: {len(original_text)} chars")
    print(f"Enriched text length: {len(enriched_text)} chars")
    print(f"Enrichment added: {len(enriched_text) - len(original_text)} chars")
    print(f"Improvement: {((len(enriched_text) / len(original_text)) - 1) * 100:.1f}%")
    
    cache.close()
    print("\n✓ Test completed successfully")


if __name__ == '__main__':
    test_nih_enrichment()
