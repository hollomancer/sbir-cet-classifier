"""Integration tests for awardee enrichment functionality."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sbir_cet_classifier.data.enrichment.models import AwardeeProfile
from sbir_cet_classifier.data.enrichment.awardee_service import AwardeeHistoricalDataService
from sbir_cet_classifier.data.enrichment.awardee_matching import AwardeeDataMatcher, MatchStrategy
from sbir_cet_classifier.data.storage import AwardeeProfileWriter


class TestAwardeeEnrichmentIntegration:
    """Test end-to-end awardee enrichment integration."""
    
    @pytest.fixture
    def mock_sam_client(self):
        """Mock SAM.gov API client with realistic responses."""
        client = Mock()
        
        # Mock entity response
        client.get_entity_by_uei.return_value = {
            "ueiSAM": "ABC123DEF456",
            "legalBusinessName": "Tech Innovations LLC",
            "entityStatus": "Active",
            "registrationDate": "2018-01-01T00:00:00Z",
            "physicalAddress": {
                "city": "San Francisco",
                "stateOrProvinceCode": "CA",
                "zipCode": "94105"
            }
        }
        
        # Mock awards response
        client.get_awards_by_uei.return_value = {
            "awards": [
                {
                    "awardId": "AWARD-001",
                    "awardNumber": "1234567890",
                    "title": "AI Research for Autonomous Systems",
                    "awardAmount": 250000.00,
                    "startDate": "2020-01-01T00:00:00Z",
                    "endDate": "2020-12-31T23:59:59Z",
                    "fundingAgency": "NSF",
                    "programOffice": "CISE",
                    "awardStatus": "Completed"
                },
                {
                    "awardId": "AWARD-002",
                    "awardNumber": "0987654321",
                    "title": "Cybersecurity Framework Development",
                    "awardAmount": 500000.00,
                    "startDate": "2022-01-01T00:00:00Z",
                    "endDate": "2024-12-31T23:59:59Z",
                    "fundingAgency": "DOD",
                    "programOffice": "DARPA",
                    "awardStatus": "Active"
                }
            ],
            "totalRecords": 2
        }
        
        # Mock entity search response
        client.search_entities.return_value = {
            "entities": [
                {
                    "ueiSAM": "ABC123DEF456",
                    "legalBusinessName": "Tech Innovations LLC",
                    "entityStatus": "Active"
                }
            ]
        }
        
        return client
    
    @pytest.fixture
    def awardee_service(self, mock_sam_client):
        """Create awardee service with mocked client."""
        return AwardeeHistoricalDataService(mock_sam_client)
    
    @pytest.fixture
    def awardee_matcher(self, mock_sam_client):
        """Create awardee matcher with mocked client."""
        return AwardeeDataMatcher(mock_sam_client)
    
    def test_complete_awardee_enrichment_workflow(self, awardee_service, awardee_matcher):
        """Test complete awardee enrichment workflow."""
        # Step 1: Match award to awardee
        award_data = {
            "award_id": "AWARD-001",
            "awardee_name": "Tech Innovations LLC",
            "awardee_uei": "ABC123DEF456"
        }
        
        match_result = awardee_matcher.match_awardee(award_data, MatchStrategy.COMPREHENSIVE)
        
        assert match_result.is_match is True
        assert match_result.matched_uei == "ABC123DEF456"
        assert match_result.confidence_score >= 0.9
        
        # Step 2: Get awardee performance metrics
        metrics = awardee_service.get_awardee_performance_metrics("ABC123DEF456")
        
        assert metrics.uei == "ABC123DEF456"
        assert metrics.total_awards == 2
        assert metrics.total_funding == Decimal("750000.00")
        assert metrics.success_rate == 1.0  # Both awards successful
        assert "NSF" in metrics.primary_agencies
        assert "DOD" in metrics.primary_agencies
    
    def test_awardee_profile_storage_integration(self, awardee_service, tmp_path):
        """Test awardee profile storage integration."""
        # Get awardee metrics
        metrics = awardee_service.get_awardee_performance_metrics("ABC123DEF456")
        
        # Create awardee profile
        profile = AwardeeProfile(
            uei=metrics.uei,
            legal_name="Tech Innovations LLC",
            total_awards=metrics.total_awards,
            total_funding=metrics.total_funding,
            success_rate=metrics.success_rate,
            avg_award_amount=metrics.avg_award_amount,
            first_award_date=metrics.first_award_date,
            last_award_date=metrics.last_award_date,
            primary_agencies=metrics.primary_agencies,
            technology_areas=metrics.technology_areas or ["AI", "Cybersecurity"]
        )
        
        # Store profile
        storage_file = tmp_path / "awardee_profiles.parquet"
        writer = AwardeeProfileWriter(storage_file)
        writer.write([profile])
        
        # Verify storage
        assert storage_file.exists()
        
        # Read back and verify
        import pandas as pd
        df = pd.read_parquet(storage_file)
        
        assert len(df) == 1
        assert df.iloc[0]["uei"] == "ABC123DEF456"
        assert df.iloc[0]["total_awards"] == 2
        assert df.iloc[0]["success_rate"] == 1.0
    
    def test_batch_awardee_enrichment(self, awardee_matcher):
        """Test batch awardee enrichment."""
        awards = [
            {
                "award_id": "AWARD-001",
                "awardee_name": "Tech Innovations LLC",
                "awardee_uei": "ABC123DEF456"
            },
            {
                "award_id": "AWARD-002",
                "awardee_name": "Tech Innovations LLC",
                "awardee_uei": "ABC123DEF456"
            }
        ]
        
        results = awardee_matcher.batch_match_awardees(awards, MatchStrategy.UEI_FIRST)
        
        assert len(results) == 2
        assert all(result.is_match for result in results)
        assert all(result.matched_uei == "ABC123DEF456" for result in results)
    
    def test_error_handling_integration(self, mock_sam_client):
        """Test error handling in integration scenarios."""
        # Configure client to raise errors
        mock_sam_client.get_entity_by_uei.side_effect = Exception("API Error")
        
        matcher = AwardeeDataMatcher(mock_sam_client)
        
        award_data = {
            "award_id": "AWARD-001",
            "awardee_uei": "ABC123DEF456"
        }
        
        # Should handle error gracefully
        result = matcher.match_awardee(award_data, MatchStrategy.UEI_FIRST)
        
        assert result.is_match is False
        assert "error" in result.match_method.lower()
    
    def test_performance_integration(self, awardee_service, awardee_matcher):
        """Test performance of integrated operations."""
        import time
        
        # Test matching performance
        award_data = {
            "award_id": "AWARD-001",
            "awardee_uei": "ABC123DEF456"
        }
        
        start_time = time.time()
        match_result = awardee_matcher.match_awardee(award_data, MatchStrategy.COMPREHENSIVE)
        match_time = time.time() - start_time
        
        # Should complete quickly
        assert match_time < 1.0
        assert match_result.is_match is True
        
        # Test metrics calculation performance
        start_time = time.time()
        metrics = awardee_service.get_awardee_performance_metrics("ABC123DEF456")
        metrics_time = time.time() - start_time
        
        # Should complete quickly
        assert metrics_time < 2.0
        assert metrics.total_awards == 2
    
    def test_data_consistency_integration(self, awardee_service, mock_sam_client):
        """Test data consistency across integration."""
        # Get metrics
        metrics = awardee_service.get_awardee_performance_metrics("ABC123DEF456")
        
        # Verify consistency
        assert metrics.total_awards > 0
        assert metrics.total_funding > 0
        assert 0.0 <= metrics.success_rate <= 1.0
        assert metrics.first_award_date <= metrics.last_award_date
        
        # Verify calculated fields
        expected_avg = metrics.total_funding / metrics.total_awards
        assert abs(metrics.avg_award_amount - expected_avg) < Decimal("0.01")
    
    def test_technology_area_extraction_integration(self, awardee_service):
        """Test technology area extraction integration."""
        tech_areas = awardee_service.get_awardee_technology_areas("ABC123DEF456")
        
        # Should extract technology areas from award titles/abstracts
        assert len(tech_areas) > 0
        # Based on mock data, should identify AI and Cybersecurity
        assert any("AI" in area for area in tech_areas)
    
    def test_fallback_matching_integration(self, mock_sam_client):
        """Test fallback matching integration."""
        # Configure UEI lookup to fail
        mock_sam_client.get_entity_by_uei.return_value = None
        
        matcher = AwardeeDataMatcher(mock_sam_client)
        
        award_data = {
            "award_id": "AWARD-001",
            "awardee_name": "Tech Innovations LLC",
            "awardee_uei": "INVALID_UEI"
        }
        
        # Should fallback to name matching
        result = matcher.match_awardee(award_data, MatchStrategy.UEI_FIRST)
        
        assert result.is_match is True
        assert result.match_method == "fuzzy_name"
        assert result.matched_uei == "ABC123DEF456"


class TestAwardeeEnrichmentEdgeCases:
    """Test edge cases in awardee enrichment integration."""
    
    @pytest.fixture
    def empty_sam_client(self):
        """Mock SAM.gov client with empty responses."""
        client = Mock()
        client.get_entity_by_uei.return_value = None
        client.get_awards_by_uei.return_value = {"awards": [], "totalRecords": 0}
        client.search_entities.return_value = {"entities": []}
        return client
    
    def test_no_awardee_data_found(self, empty_sam_client):
        """Test handling when no awardee data is found."""
        service = AwardeeHistoricalDataService(empty_sam_client)
        matcher = AwardeeDataMatcher(empty_sam_client)
        
        # Test matching with no data
        award_data = {
            "award_id": "AWARD-001",
            "awardee_uei": "UNKNOWN_UEI"
        }
        
        result = matcher.match_awardee(award_data, MatchStrategy.COMPREHENSIVE)
        assert result.is_match is False
        
        # Test metrics with no data
        metrics = service.get_awardee_performance_metrics("UNKNOWN_UEI")
        assert metrics.total_awards == 0
        assert metrics.total_funding == Decimal("0.00")
    
    def test_partial_data_scenarios(self):
        """Test scenarios with partial data availability."""
        client = Mock()
        
        # Entity exists but no awards
        client.get_entity_by_uei.return_value = {
            "ueiSAM": "ABC123DEF456",
            "legalBusinessName": "New Company LLC"
        }
        client.get_awards_by_uei.return_value = {"awards": [], "totalRecords": 0}
        
        service = AwardeeHistoricalDataService(client)
        metrics = service.get_awardee_performance_metrics("ABC123DEF456")
        
        # Should handle gracefully
        assert metrics.total_awards == 0
        assert metrics.success_rate == 0.0
    
    def test_large_dataset_integration(self):
        """Test integration with large datasets."""
        client = Mock()
        
        # Mock large number of awards
        awards = []
        for i in range(500):
            awards.append({
                "awardId": f"AWARD-{i:03d}",
                "awardAmount": 100000.0 + (i * 1000),
                "startDate": f"202{i%5}-01-01T00:00:00Z",
                "fundingAgency": ["NSF", "DOD", "NIH"][i % 3],
                "awardStatus": ["Completed", "Active"][i % 2]
            })
        
        client.get_awards_by_uei.return_value = {"awards": awards, "totalRecords": 500}
        
        service = AwardeeHistoricalDataService(client)
        
        # Should handle large dataset efficiently
        import time
        start_time = time.time()
        metrics = service.get_awardee_performance_metrics("ABC123DEF456")
        processing_time = time.time() - start_time
        
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert metrics.total_awards == 500
        assert len(metrics.primary_agencies) == 3
