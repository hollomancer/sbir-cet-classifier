"""Tests for awardee historical data retrieval service."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from decimal import Decimal

from sbir_cet_classifier.data.enrichment.awardee_service import (
    AwardeeHistoricalDataService,
    AwardeeMetrics,
    AwardeePerformanceAnalyzer,
)


class TestAwardeeHistoricalDataService:
    """Test awardee historical data retrieval service."""
    
    @pytest.fixture
    def mock_sam_client(self):
        """Mock SAM.gov API client."""
        return Mock()
    
    @pytest.fixture
    def service(self, mock_sam_client):
        """Create awardee service instance."""
        return AwardeeHistoricalDataService(sam_client=mock_sam_client)
    
    def test_get_awardee_awards_history(self, service, mock_sam_client):
        """Test retrieving awardee awards history."""
        uei = "ABC123DEF456"
        
        # Mock SAM.gov API response
        mock_sam_client.get_awards_by_uei.return_value = {
            "awards": [
                {
                    "awardId": "AWARD-001",
                    "awardNumber": "1234567890",
                    "title": "AI Research Project",
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
                    "title": "Cybersecurity Framework",
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
        
        awards = service.get_awardee_awards_history(uei)
        
        assert len(awards) == 2
        assert awards[0]["awardId"] == "AWARD-001"
        assert awards[1]["awardId"] == "AWARD-002"
        mock_sam_client.get_awards_by_uei.assert_called_once_with(uei)
    
    def test_get_awardee_awards_with_date_filter(self, service, mock_sam_client):
        """Test retrieving awards with date filtering."""
        uei = "ABC123DEF456"
        start_date = datetime(2021, 1, 1)
        end_date = datetime(2023, 12, 31)
        
        # Mock filtered response
        mock_sam_client.get_awards_by_uei.return_value = {
            "awards": [
                {
                    "awardId": "AWARD-002",
                    "awardAmount": 500000.00,
                    "startDate": "2022-01-01T00:00:00Z",
                    "fundingAgency": "DOD"
                }
            ],
            "totalRecords": 1
        }
        
        awards = service.get_awardee_awards_history(
            uei, 
            start_date=start_date, 
            end_date=end_date
        )
        
        assert len(awards) == 1
        assert awards[0]["awardId"] == "AWARD-002"
        mock_sam_client.get_awards_by_uei.assert_called_once_with(
            uei, start_date=start_date, end_date=end_date
        )
    
    def test_get_awardee_performance_metrics(self, service, mock_sam_client):
        """Test calculating awardee performance metrics."""
        uei = "ABC123DEF456"
        
        # Mock awards data
        mock_sam_client.get_awards_by_uei.return_value = {
            "awards": [
                {
                    "awardId": "AWARD-001",
                    "awardAmount": 250000.00,
                    "startDate": "2020-01-01T00:00:00Z",
                    "endDate": "2020-12-31T23:59:59Z",
                    "fundingAgency": "NSF",
                    "awardStatus": "Completed"
                },
                {
                    "awardId": "AWARD-002",
                    "awardAmount": 500000.00,
                    "startDate": "2022-01-01T00:00:00Z",
                    "endDate": "2024-12-31T23:59:59Z",
                    "fundingAgency": "DOD",
                    "awardStatus": "Active"
                },
                {
                    "awardId": "AWARD-003",
                    "awardAmount": 150000.00,
                    "startDate": "2019-01-01T00:00:00Z",
                    "endDate": "2019-12-31T23:59:59Z",
                    "fundingAgency": "NIH",
                    "awardStatus": "Terminated"
                }
            ],
            "totalRecords": 3
        }
        
        metrics = service.get_awardee_performance_metrics(uei)
        
        assert metrics.total_awards == 3
        assert metrics.total_funding == Decimal("900000.00")
        assert metrics.success_rate == 2/3  # 2 successful out of 3
        assert metrics.avg_award_amount == Decimal("300000.00")
        assert len(metrics.primary_agencies) == 3
        assert "NSF" in metrics.primary_agencies
        assert "DOD" in metrics.primary_agencies
        assert "NIH" in metrics.primary_agencies
    
    def test_get_awardee_technology_areas(self, service, mock_sam_client):
        """Test extracting technology areas from awards."""
        uei = "ABC123DEF456"
        
        # Mock awards with technology keywords
        mock_sam_client.get_awards_by_uei.return_value = {
            "awards": [
                {
                    "awardId": "AWARD-001",
                    "title": "Machine Learning for Autonomous Systems",
                    "abstract": "Research in artificial intelligence and robotics",
                    "keywords": ["AI", "Machine Learning", "Robotics"]
                },
                {
                    "awardId": "AWARD-002",
                    "title": "Cybersecurity Framework Development",
                    "abstract": "Advanced cybersecurity protocols",
                    "keywords": ["Cybersecurity", "Network Security"]
                }
            ]
        }
        
        tech_areas = service.get_awardee_technology_areas(uei)
        
        assert "AI" in tech_areas
        assert "Cybersecurity" in tech_areas
        assert "Robotics" in tech_areas
    
    def test_handle_no_awards_found(self, service, mock_sam_client):
        """Test handling when no awards are found for awardee."""
        uei = "UNKNOWN_UEI"
        
        # Mock empty response
        mock_sam_client.get_awards_by_uei.return_value = {
            "awards": [],
            "totalRecords": 0
        }
        
        awards = service.get_awardee_awards_history(uei)
        metrics = service.get_awardee_performance_metrics(uei)
        
        assert len(awards) == 0
        assert metrics.total_awards == 0
        assert metrics.total_funding == Decimal("0.00")
        assert metrics.success_rate == 0.0
    
    def test_handle_api_error(self, service, mock_sam_client):
        """Test handling SAM.gov API errors."""
        uei = "ABC123DEF456"
        
        # Mock API error
        mock_sam_client.get_awards_by_uei.side_effect = Exception("API Error")
        
        with pytest.raises(Exception):
            service.get_awardee_awards_history(uei)
    
    def test_paginated_results(self, service, mock_sam_client):
        """Test handling paginated results from SAM.gov API."""
        uei = "ABC123DEF456"
        
        # Mock paginated responses
        def mock_paginated_call(uei, offset=0, limit=100):
            if offset == 0:
                return {
                    "awards": [{"awardId": f"AWARD-{i}"} for i in range(100)],
                    "totalRecords": 150
                }
            elif offset == 100:
                return {
                    "awards": [{"awardId": f"AWARD-{i}"} for i in range(100, 150)],
                    "totalRecords": 150
                }
            return {"awards": [], "totalRecords": 150}
        
        mock_sam_client.get_awards_by_uei.side_effect = mock_paginated_call
        
        awards = service.get_awardee_awards_history(uei, fetch_all=True)
        
        assert len(awards) == 150
        assert mock_sam_client.get_awards_by_uei.call_count == 2


class TestAwardeeMetrics:
    """Test AwardeeMetrics data model."""
    
    def test_create_metrics(self):
        """Test creating awardee metrics."""
        metrics = AwardeeMetrics(
            uei="ABC123DEF456",
            total_awards=10,
            total_funding=Decimal("2000000.00"),
            success_rate=0.8,
            avg_award_amount=Decimal("200000.00"),
            first_award_date=datetime(2018, 1, 1),
            last_award_date=datetime(2024, 1, 1),
            primary_agencies=["NSF", "DOD"],
            technology_areas=["AI", "Cybersecurity"],
            award_size_distribution={
                "small": 3,    # < $100k
                "medium": 5,   # $100k - $500k
                "large": 2     # > $500k
            }
        )
        
        assert metrics.uei == "ABC123DEF456"
        assert metrics.total_awards == 10
        assert metrics.success_rate == 0.8
        assert len(metrics.primary_agencies) == 2
        assert len(metrics.technology_areas) == 2
    
    def test_metrics_validation(self):
        """Test metrics field validation."""
        # Test negative total awards
        with pytest.raises(ValueError):
            AwardeeMetrics(
                uei="ABC123DEF456",
                total_awards=-1,
                total_funding=Decimal("1000000.00"),
                success_rate=0.8,
                avg_award_amount=Decimal("100000.00"),
                first_award_date=datetime(2020, 1, 1),
                last_award_date=datetime(2024, 1, 1),
                primary_agencies=["NSF"],
                technology_areas=["AI"]
            )
    
    def test_calculate_years_active(self):
        """Test calculating years active."""
        metrics = AwardeeMetrics(
            uei="ABC123DEF456",
            total_awards=5,
            total_funding=Decimal("1000000.00"),
            success_rate=0.8,
            avg_award_amount=Decimal("200000.00"),
            first_award_date=datetime(2020, 1, 1),
            last_award_date=datetime(2024, 1, 1),
            primary_agencies=["NSF"],
            technology_areas=["AI"]
        )
        
        years_active = metrics.calculate_years_active()
        assert years_active == 4  # 2020 to 2024


class TestAwardeePerformanceAnalyzer:
    """Test awardee performance analysis functionality."""
    
    @pytest.fixture
    def analyzer(self):
        """Create performance analyzer instance."""
        return AwardeePerformanceAnalyzer()
    
    def test_calculate_success_rate(self, analyzer):
        """Test success rate calculation."""
        awards = [
            {"awardStatus": "Completed"},
            {"awardStatus": "Active"},
            {"awardStatus": "Terminated"},
            {"awardStatus": "Completed"}
        ]
        
        success_rate = analyzer.calculate_success_rate(awards)
        
        # 3 successful (Completed + Active) out of 4 total
        assert success_rate == 0.75
    
    def test_analyze_funding_trends(self, analyzer):
        """Test funding trend analysis."""
        awards = [
            {
                "awardAmount": 100000.00,
                "startDate": "2020-01-01T00:00:00Z"
            },
            {
                "awardAmount": 200000.00,
                "startDate": "2021-01-01T00:00:00Z"
            },
            {
                "awardAmount": 300000.00,
                "startDate": "2022-01-01T00:00:00Z"
            }
        ]
        
        trends = analyzer.analyze_funding_trends(awards)
        
        assert trends["trend"] == "increasing"
        assert trends["total_growth"] == 200000.00  # From 100k to 300k
        assert trends["avg_annual_growth"] > 0
    
    def test_identify_expertise_areas(self, analyzer):
        """Test expertise area identification."""
        awards = [
            {
                "title": "Machine Learning Research",
                "abstract": "Advanced AI algorithms",
                "keywords": ["AI", "Machine Learning"]
            },
            {
                "title": "Cybersecurity Framework",
                "abstract": "Network security protocols",
                "keywords": ["Cybersecurity", "Network Security"]
            },
            {
                "title": "AI-Powered Robotics",
                "abstract": "Autonomous robot systems",
                "keywords": ["AI", "Robotics", "Autonomous Systems"]
            }
        ]
        
        expertise = analyzer.identify_expertise_areas(awards)
        
        # AI should be most frequent
        assert expertise[0]["area"] == "AI"
        assert expertise[0]["frequency"] == 2
        assert any(area["area"] == "Cybersecurity" for area in expertise)
    
    def test_calculate_agency_diversity(self, analyzer):
        """Test agency diversity calculation."""
        awards = [
            {"fundingAgency": "NSF"},
            {"fundingAgency": "NSF"},
            {"fundingAgency": "DOD"},
            {"fundingAgency": "NIH"}
        ]
        
        diversity = analyzer.calculate_agency_diversity(awards)
        
        # 3 unique agencies out of 4 awards
        assert diversity["unique_agencies"] == 3
        assert diversity["diversity_score"] == 0.75  # 3/4
        assert "NSF" in diversity["agency_distribution"]
        assert diversity["agency_distribution"]["NSF"] == 2
    
    def test_performance_benchmarking(self, analyzer):
        """Test performance benchmarking against industry standards."""
        metrics = AwardeeMetrics(
            uei="ABC123DEF456",
            total_awards=15,
            total_funding=Decimal("3000000.00"),
            success_rate=0.85,
            avg_award_amount=Decimal("200000.00"),
            first_award_date=datetime(2018, 1, 1),
            last_award_date=datetime(2024, 1, 1),
            primary_agencies=["NSF", "DOD"],
            technology_areas=["AI", "Cybersecurity"]
        )
        
        benchmark = analyzer.benchmark_performance(metrics)
        
        assert "success_rate_percentile" in benchmark
        assert "funding_level_category" in benchmark
        assert "experience_level" in benchmark
        
        # High success rate should be in upper percentiles
        assert benchmark["success_rate_percentile"] > 70
    
    def test_risk_assessment(self, analyzer):
        """Test awardee risk assessment."""
        awards = [
            {
                "awardStatus": "Completed",
                "awardAmount": 250000.00,
                "startDate": "2020-01-01T00:00:00Z",
                "endDate": "2020-12-31T23:59:59Z"
            },
            {
                "awardStatus": "Terminated",
                "awardAmount": 500000.00,
                "startDate": "2021-01-01T00:00:00Z",
                "endDate": "2021-06-30T23:59:59Z"
            }
        ]
        
        risk_assessment = analyzer.assess_risk(awards)
        
        assert "risk_score" in risk_assessment
        assert "risk_factors" in risk_assessment
        assert "mitigation_recommendations" in risk_assessment
        
        # Should identify termination as risk factor
        assert any("termination" in factor.lower() for factor in risk_assessment["risk_factors"])
