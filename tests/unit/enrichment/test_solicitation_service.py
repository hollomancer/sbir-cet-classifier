"""Tests for solicitation text retrieval service."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import date, datetime
from decimal import Decimal

from src.sbir_cet_classifier.data.enrichment.solicitation_service import SolicitationService
from src.sbir_cet_classifier.data.enrichment.models import Solicitation


class TestSolicitationService:
    """Test SolicitationService."""

    @pytest.fixture
    def mock_sam_client(self):
        """Mock SAM.gov API client."""
        client = Mock()
        client.get_solicitation_by_number = AsyncMock()
        client.search_solicitations = AsyncMock()
        return client

    @pytest.fixture
    def service(self, mock_sam_client):
        """Create SolicitationService with mocked client."""
        return SolicitationService(sam_client=mock_sam_client)

    @pytest.mark.asyncio
    async def test_get_solicitation_by_number_success(self, service, mock_sam_client):
        """Test successful solicitation retrieval by number."""
        # Mock API response
        mock_response = {
            "solicitation_id": "SOL-2024-001",
            "solicitation_number": "N00014-24-S-B001",
            "title": "Advanced Materials Research",
            "agency_code": "DON",
            "program_office_id": "ONR-001",
            "solicitation_type": "SBIR Phase I",
            "full_text": "Complete solicitation text...",
            "technical_requirements": "Technical requirements...",
            "evaluation_criteria": "Evaluation criteria...",
            "funding_range_min": "100000.00",
            "funding_range_max": "300000.00",
            "proposal_deadline": "2024-06-15",
            "performance_period": 12,
            "keywords": ["materials", "nanotechnology"],
            "cet_relevance_scores": {"advanced_materials": 0.95}
        }
        
        mock_sam_client.get_solicitation_by_number.return_value = mock_response
        
        result = await service.get_solicitation_by_number("N00014-24-S-B001")
        
        assert isinstance(result, Solicitation)
        assert result.solicitation_number == "N00014-24-S-B001"
        assert result.title == "Advanced Materials Research"
        assert len(result.keywords) == 2
        mock_sam_client.get_solicitation_by_number.assert_called_once_with("N00014-24-S-B001")

    @pytest.mark.asyncio
    async def test_get_solicitation_by_number_not_found(self, service, mock_sam_client):
        """Test solicitation not found."""
        mock_sam_client.get_solicitation_by_number.return_value = None
        
        result = await service.get_solicitation_by_number("NONEXISTENT")
        
        assert result is None
        mock_sam_client.get_solicitation_by_number.assert_called_once_with("NONEXISTENT")

    @pytest.mark.asyncio
    async def test_search_solicitations_by_agency(self, service, mock_sam_client):
        """Test searching solicitations by agency."""
        mock_response = [
            {
                "solicitation_id": "SOL-2024-001",
                "solicitation_number": "N00014-24-S-B001",
                "title": "Materials Research",
                "agency_code": "DON",
                "program_office_id": "ONR-001",
                "solicitation_type": "SBIR Phase I",
                "full_text": "Text 1",
                "technical_requirements": "Requirements 1",
                "evaluation_criteria": "Criteria 1",
                "funding_range_min": "100000.00",
                "funding_range_max": "300000.00",
                "proposal_deadline": "2024-06-15",
                "performance_period": 12,
                "keywords": ["materials"],
                "cet_relevance_scores": {"advanced_materials": 0.9}
            },
            {
                "solicitation_id": "SOL-2024-002",
                "solicitation_number": "N00014-24-S-B002",
                "title": "AI Research",
                "agency_code": "DON",
                "program_office_id": "ONR-002",
                "solicitation_type": "SBIR Phase II",
                "full_text": "Text 2",
                "technical_requirements": "Requirements 2",
                "evaluation_criteria": "Criteria 2",
                "funding_range_min": "500000.00",
                "funding_range_max": "1000000.00",
                "proposal_deadline": "2024-07-15",
                "performance_period": 24,
                "keywords": ["ai", "machine learning"],
                "cet_relevance_scores": {"artificial_intelligence": 0.95}
            }
        ]
        
        mock_sam_client.search_solicitations.return_value = mock_response
        
        results = await service.search_solicitations_by_agency("DON")
        
        assert len(results) == 2
        assert all(isinstance(sol, Solicitation) for sol in results)
        assert results[0].title == "Materials Research"
        assert results[1].title == "AI Research"
        mock_sam_client.search_solicitations.assert_called_once_with(agency_code="DON")

    @pytest.mark.asyncio
    async def test_get_solicitation_with_caching(self, service, mock_sam_client):
        """Test solicitation retrieval with caching."""
        mock_response = {
            "solicitation_id": "SOL-2024-001",
            "solicitation_number": "N00014-24-S-B001",
            "title": "Cached Solicitation",
            "agency_code": "DON",
            "program_office_id": "ONR-001",
            "solicitation_type": "SBIR Phase I",
            "full_text": "Cached text",
            "technical_requirements": "Cached requirements",
            "evaluation_criteria": "Cached criteria",
            "funding_range_min": "100000.00",
            "funding_range_max": "300000.00",
            "proposal_deadline": "2024-06-15",
            "performance_period": 12,
            "keywords": [],
            "cet_relevance_scores": {}
        }
        
        mock_sam_client.get_solicitation_by_number.return_value = mock_response
        
        # First call should hit API
        result1 = await service.get_solicitation_by_number("N00014-24-S-B001")
        
        # Second call should use cache
        result2 = await service.get_solicitation_by_number("N00014-24-S-B001")
        
        assert result1.title == result2.title
        # API should only be called once due to caching
        mock_sam_client.get_solicitation_by_number.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_technical_keywords(self, service):
        """Test technical keyword extraction from solicitation text."""
        solicitation_text = """
        This SBIR Phase I solicitation seeks innovative approaches to quantum computing,
        artificial intelligence, and advanced materials research. The technical approach
        should demonstrate machine learning algorithms, nanotechnology applications,
        and cybersecurity protocols.
        """
        
        keywords = await service.extract_technical_keywords(solicitation_text)
        
        expected_keywords = [
            "quantum computing", "artificial intelligence", "advanced materials",
            "machine learning", "nanotechnology", "cybersecurity"
        ]
        
        for keyword in expected_keywords:
            assert keyword in keywords

    @pytest.mark.asyncio
    async def test_calculate_cet_relevance_scores(self, service):
        """Test CET relevance score calculation."""
        solicitation_text = """
        Advanced quantum computing research with applications in cryptography
        and secure communications. The project will develop quantum algorithms
        for enhanced cybersecurity protocols.
        """
        
        scores = await service.calculate_cet_relevance_scores(solicitation_text)
        
        assert isinstance(scores, dict)
        assert "quantum_computing" in scores
        assert "cybersecurity" in scores
        assert all(0.0 <= score <= 1.0 for score in scores.values())
        assert scores["quantum_computing"] > 0.5  # Should be highly relevant

    @pytest.mark.asyncio
    async def test_service_error_handling(self, service, mock_sam_client):
        """Test service error handling."""
        mock_sam_client.get_solicitation_by_number.side_effect = Exception("API Error")
        
        with pytest.raises(Exception) as exc_info:
            await service.get_solicitation_by_number("N00014-24-S-B001")
        
        assert "API Error" in str(exc_info.value)

    def test_service_initialization(self):
        """Test service initialization."""
        mock_client = Mock()
        service = SolicitationService(sam_client=mock_client)
        
        assert service.sam_client == mock_client
        assert hasattr(service, '_cache')
