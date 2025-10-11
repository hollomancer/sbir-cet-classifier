"""Tests for SAM.gov API client."""

from unittest.mock import Mock, patch

import pytest
import requests

from sbir_cet_classifier.common.config import EnrichmentConfig
from sbir_cet_classifier.data.enrichment.sam_client import SAMAPIError, SAMClient


class TestSAMClient:
    """Test cases for SAM.gov API client."""
    
    @pytest.fixture
    def config(self):
        """Test configuration."""
        return EnrichmentConfig(
            api_key="test-key",
            base_url="https://api.sam.gov/test",
            rate_limit=100,
            timeout=30,
            max_retries=3
        )
    
    @pytest.fixture
    def client(self, config):
        """Test client instance."""
        return SAMClient(config)
    
    def test_client_initialization(self, config):
        """Test client initializes with correct configuration."""
        client = SAMClient(config)
        assert client.config == config
        assert client.session is not None
        assert client.session.headers["X-API-Key"] == "test-key"
    
    def test_get_award_success(self, client):
        """Test successful award retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "awardId": "AWARD123",
            "title": "Test Award",
            "recipientName": "Test Company"
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client.get_award("AWARD123")
            
        assert result["awardId"] == "AWARD123"
        assert result["title"] == "Test Award"
    
    def test_get_award_not_found(self, client):
        """Test award not found handling."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")
        mock_response.status_code = 404
        
        with patch.object(client.session, 'get', return_value=mock_response):
            with pytest.raises(SAMAPIError, match="Award not found"):
                client.get_award("NONEXISTENT")
    
    def test_search_awards_success(self, client):
        """Test successful award search."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "totalRecords": 2,
            "awards": [
                {"awardId": "AWARD1", "title": "Award 1"},
                {"awardId": "AWARD2", "title": "Award 2"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client.search_awards(recipient_name="Test Company")
            
        assert result["totalRecords"] == 2
        assert len(result["awards"]) == 2
    
    def test_get_entity_success(self, client):
        """Test successful entity retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "ueiSAM": "TEST123456789",
            "entityName": "Test Company",
            "awardHistory": {"totalAwards": 5}
        }
        mock_response.raise_for_status.return_value = None
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client.get_entity("TEST123456789")
            
        assert result["ueiSAM"] == "TEST123456789"
        assert result["awardHistory"]["totalAwards"] == 5
    
    def test_rate_limiting(self, client):
        """Test rate limiting behavior."""
        # This test would verify rate limiting is applied
        # Implementation depends on the actual rate limiting mechanism
        pass
    
    def test_retry_on_failure(self, client):
        """Test retry mechanism on API failures."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = [
            requests.HTTPError("500"),
            requests.HTTPError("500"),
            None  # Success on third try
        ]
        mock_response.json.return_value = {"awardId": "AWARD123"}
        
        with patch.object(client.session, 'get', return_value=mock_response):
            result = client.get_award("AWARD123")
            
        assert result["awardId"] == "AWARD123"
        assert mock_response.raise_for_status.call_count == 3
    
    def test_max_retries_exceeded(self, client):
        """Test behavior when max retries exceeded."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500")
        mock_response.status_code = 500
        
        with patch.object(client.session, 'get', return_value=mock_response):
            with pytest.raises(SAMAPIError, match="Max retries exceeded"):
                client.get_award("AWARD123")


class TestSAMAPIError:
    """Test cases for SAM API error handling."""
    
    def test_error_creation(self):
        """Test SAM API error creation."""
        error = SAMAPIError("Test error", status_code=404)
        assert str(error) == "Test error"
        assert error.status_code == 404
    
    def test_error_without_status_code(self):
        """Test SAM API error without status code."""
        error = SAMAPIError("Test error")
        assert str(error) == "Test error"
        assert error.status_code is None
