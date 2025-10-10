"""Tests for NIH matcher hybrid strategy."""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from sbir_cet_classifier.common.schemas import Award
from sbir_cet_classifier.data.external.nih_matcher import NIHMatcher


@pytest.fixture
def sample_award():
    """Create sample award for testing."""
    return Award(
        award_id="TEST-001",
        agency="HHS",
        firm_name="ACME BIOTECH INC",
        firm_city="Boston",
        firm_state="MA",
        award_amount=500000.0,
        award_date=date(2024, 1, 1),
        phase="I",
        topic_code="BT-001",
        abstract="Novel gene therapy approach for rare diseases",
        keywords=["gene therapy", "rare disease"],
        source_version="1.0",
        ingested_at=date(2024, 1, 1)
    )


@pytest.fixture
def mock_nih_response():
    """Create mock NIH API response."""
    return {
        'results': [{
            'project_num': '1R43GM123456-01',
            'organization': {'org_name': 'ACME BIOTECH INC'},
            'award_amount': 500000,
            'fiscal_year': 2024,
            'abstract_text': 'Novel gene therapy approach for rare diseases',
        }]
    }


class TestNIHMatcher:
    """Tests for NIHMatcher class."""
    
    def test_initialization(self):
        """Should initialize with default config."""
        matcher = NIHMatcher()
        assert matcher.base_url == "https://api.reporter.nih.gov/v2"
        assert matcher.timeout == 30.0
        assert matcher._cache == {}
        matcher.close()
    
    def test_context_manager(self):
        """Should work as context manager."""
        with NIHMatcher() as matcher:
            assert matcher.client is not None
    
    def test_exact_match_success(self, sample_award, mock_nih_response):
        """Should match by exact org + amount + year."""
        with patch('httpx.Client.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_nih_response
            mock_post.return_value = mock_response
            
            matcher = NIHMatcher()
            result = matcher.find_project(sample_award)
            
            assert result is not None
            assert result['project_num'] == '1R43GM123456-01'
            assert result['organization']['org_name'] == 'ACME BIOTECH INC'
            matcher.close()
    
    def test_fuzzy_match_success(self, sample_award, mock_nih_response):
        """Should match with fuzzy org name."""
        # Modify award to have suffix
        sample_award.firm_name = "ACME BIOTECH, INC."
        
        with patch('httpx.Client.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            
            # First call (exact) returns empty, second (fuzzy) returns match
            mock_response.json.side_effect = [
                {'results': []},  # Exact match fails
                mock_nih_response  # Fuzzy match succeeds
            ]
            mock_post.return_value = mock_response
            
            matcher = NIHMatcher()
            result = matcher.find_project(sample_award)
            
            assert result is not None
            assert result['project_num'] == '1R43GM123456-01'
            matcher.close()
    
    def test_similarity_match_success(self, sample_award):
        """Should match by abstract similarity."""
        with patch('httpx.Client.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            
            # Exact and fuzzy fail, similarity succeeds
            mock_response.json.side_effect = [
                {'results': []},  # Exact fails
                {'results': []},  # Fuzzy fails
                {'results': [{  # Similarity succeeds
                    'project_num': '1R43GM123456-01',
                    'organization': {'org_name': 'ACME BIOTECH INC'},
                    'award_amount': 500000,
                    'fiscal_year': 2024,
                    'abstract_text': 'Novel gene therapy approach for rare diseases',
                }]}
            ]
            mock_post.return_value = mock_response
            
            matcher = NIHMatcher()
            result = matcher.find_project(sample_award)
            
            assert result is not None
            assert result['project_num'] == '1R43GM123456-01'
            matcher.close()
    
    def test_no_match(self, sample_award):
        """Should return None when no match found."""
        with patch('httpx.Client.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'results': []}
            mock_post.return_value = mock_response
            
            matcher = NIHMatcher()
            result = matcher.find_project(sample_award)
            
            assert result is None
            matcher.close()
    
    def test_caching(self, sample_award, mock_nih_response):
        """Should cache API results."""
        with patch('httpx.Client.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_nih_response
            mock_post.return_value = mock_response
            
            matcher = NIHMatcher()
            
            # First call
            result1 = matcher.find_project(sample_award)
            assert result1 is not None
            
            # Second call should use cache
            result2 = matcher.find_project(sample_award)
            assert result2 is not None
            
            # Should only call API once
            assert mock_post.call_count == 1
            matcher.close()
    
    def test_api_error_handling(self, sample_award):
        """Should handle API errors gracefully."""
        with patch('httpx.Client.post') as mock_post:
            mock_post.side_effect = Exception("API Error")
            
            matcher = NIHMatcher()
            result = matcher.find_project(sample_award)
            
            assert result is None
            matcher.close()
    
    def test_amount_tolerance(self, sample_award, mock_nih_response):
        """Should use ±10% tolerance on amount."""
        with patch('httpx.Client.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_nih_response
            mock_post.return_value = mock_response
            
            matcher = NIHMatcher()
            matcher.find_project(sample_award)
            
            # Check that API was called with amount range
            call_args = mock_post.call_args
            criteria = call_args[1]['json']['criteria']
            
            assert 'award_amount_range' in criteria
            assert criteria['award_amount_range']['min_amount'] == 450000  # 90%
            assert criteria['award_amount_range']['max_amount'] == 550000  # 110%
            matcher.close()
    
    def test_enhanced_fields_requested(self, sample_award, mock_nih_response):
        """Should request enhanced fields from API."""
        with patch('httpx.Client.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_nih_response
            mock_post.return_value = mock_response
            
            matcher = NIHMatcher()
            matcher.find_project(sample_award)
            
            # Check that enhanced fields are requested
            call_args = mock_post.call_args
            include_fields = call_args[1]['json']['include_fields']
            
            assert 'AbstractText' in include_fields
            assert 'PhrText' in include_fields
            assert 'PrefTerms' in include_fields
            assert 'SpendingCategoriesDesc' in include_fields
            matcher.close()
