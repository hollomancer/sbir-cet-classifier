"""Integration tests for NIH matcher with real API calls."""

from datetime import date, datetime

import pytest

from sbir_cet_classifier.common.schemas import Award
from sbir_cet_classifier.data.external.nih_matcher import NIHMatcher


@pytest.fixture
def real_nih_award():
    """Create award based on known NIH project."""
    return Award(
        award_id="TEST-REAL-001",
        agency="HHS",
        firm_name="HUMAN CELL CO",
        firm_city="Boston",
        firm_state="MA",
        award_amount=360897.0,
        award_date=date(2024, 1, 1),
        phase="I",
        topic_code="EY-001",
        abstract="Infant head malformation detection",
        keywords=["medical device", "pediatrics"],
        source_version="1.0",
        ingested_at=datetime.now()
    )


class TestNIHMatcherIntegration:
    """Integration tests with real NIH API."""
    
    def test_real_api_exact_match(self, real_nih_award):
        """Should match real NIH award by exact criteria."""
        with NIHMatcher() as matcher:
            result = matcher.find_project(real_nih_award)
            
            assert result is not None
            assert 'project_num' in result
            assert result['project_num'].startswith('1R43')  # Phase I SBIR
            assert result['organization']['org_name'] == 'HUMAN CELL CO'
            assert abs(result['award_amount'] - 360897) < 1000
    
    def test_real_api_fuzzy_match(self):
        """Should match with fuzzy org name."""
        # Award with punctuation variations
        award = Award(
            award_id="TEST-FUZZY-001",
            agency="HHS",
            firm_name="Zeteo Tech, Inc.",  # Note: comma and period
            firm_city="Boston",
            firm_state="MA",
            award_amount=271495.0,
            award_date=date(2024, 1, 1),
            phase="I",
            topic_code="GM-001",
            abstract="Protein analysis technology",
            keywords=["protein", "analysis"],
            source_version="1.0",
            ingested_at=datetime.now()
        )
        
        with NIHMatcher() as matcher:
            result = matcher.find_project(award)
            
            assert result is not None
            assert 'project_num' in result
            # NIH has "ZETEO TECH, INC." (uppercase, different punctuation)
            assert 'ZETEO' in result['organization']['org_name'].upper()
    
    def test_real_api_caching(self, real_nih_award):
        """Should cache results across multiple calls."""
        with NIHMatcher() as matcher:
            # First call
            result1 = matcher.find_project(real_nih_award)
            cache_size_1 = len(matcher._cache)
            
            # Second call (should use cache)
            result2 = matcher.find_project(real_nih_award)
            cache_size_2 = len(matcher._cache)
            
            assert result1 is not None
            assert result2 is not None
            assert result1['project_num'] == result2['project_num']
            assert cache_size_1 == cache_size_2  # No new cache entries
    
    def test_real_api_enhanced_fields(self, real_nih_award):
        """Should retrieve enhanced fields from API."""
        with NIHMatcher() as matcher:
            result = matcher.find_project(real_nih_award)
            
            assert result is not None
            
            # Check for enhanced fields
            assert 'abstract_text' in result
            assert len(result['abstract_text']) > 1000  # Should have full abstract
            
            # May have PHR text and preferred terms
            if 'phr_text' in result:
                assert len(result['phr_text']) > 0
            
            if 'pref_terms' in result:
                assert len(result['pref_terms']) > 0
    
    def test_real_api_no_match(self):
        """Should return None for non-existent award."""
        fake_award = Award(
            award_id="TEST-FAKE-001",
            agency="HHS",
            firm_name="NONEXISTENT COMPANY XYZ123",
            firm_city="Nowhere",
            firm_state="XX",
            award_amount=999999999.0,
            award_date=date(1900, 1, 1),
            phase="I",
            topic_code="XX-001",
            abstract="This should not match anything",
            keywords=["fake"],
            source_version="1.0",
            ingested_at=datetime.now()
        )
        
        with NIHMatcher() as matcher:
            result = matcher.find_project(fake_award)
            
            assert result is None
    
    def test_real_api_performance(self, real_nih_award):
        """Should complete match in reasonable time."""
        import time
        
        with NIHMatcher() as matcher:
            start = time.time()
            result = matcher.find_project(real_nih_award)
            elapsed = time.time() - start
            
            assert result is not None
            assert elapsed < 2.0  # Should complete in under 2 seconds (first call)
