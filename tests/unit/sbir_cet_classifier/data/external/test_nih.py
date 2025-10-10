"""Unit tests for NIH API client with mocked responses."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from sbir_cet_classifier.data.external.nih import (
    NIHAPIError,
    NIHClient,
    SolicitationData,
)


class TestNIHClient:
    """Tests for NIHClient initialization and lifecycle."""

    def test_client_initialization_defaults(self) -> None:
        """Should initialize with default configuration."""
        client = NIHClient()

        assert client.base_url == "https://api.reporter.nih.gov/v2"
        assert client.timeout == 30.0
        assert client.client is not None

        client.close()

    def test_client_initialization_custom_config(self) -> None:
        """Should initialize with custom configuration."""
        client = NIHClient(
            base_url="https://test.nih.gov/api",
            timeout=45.0,
        )

        assert client.base_url == "https://test.nih.gov/api"
        assert client.timeout == 45.0

        client.close()

    def test_client_context_manager(self) -> None:
        """Should work as context manager."""
        with NIHClient() as client:
            assert client.client is not None

    def test_client_close(self) -> None:
        """Should close HTTP client cleanly."""
        client = NIHClient()
        client.close()

        # Should not raise exception on double close
        client.close()


class TestLookupSolicitation:
    """Tests for lookup_solicitation method."""

    def test_lookup_by_funding_opportunity_success(self) -> None:
        """Should successfully lookup solicitation by FOA number."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "project_title": "Cancer Immunotherapy Research",
                    "abstract_text": "Novel approaches to cancer treatment",
                    "phr_text": "Public health relevance statement",
                    "project_terms": ["cancer", "immunotherapy", "oncology"],
                    "agency_ic_admin": {"name": "NCI"},
                    "activity_code": "R43",
                    "fiscal_year": 2023,
                }
            ]
        }

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="PA-23-123")

            assert result is not None
            assert isinstance(result, SolicitationData)
            assert result.solicitation_id == "PA-23-123"
            assert "Cancer Immunotherapy" in result.description
            assert "cancer" in result.technical_keywords
            assert "immunotherapy" in result.technical_keywords
            assert result.api_source == "nih"

            client.close()

    def test_lookup_by_solicitation_id_success(self) -> None:
        """Should successfully lookup solicitation by alternative ID."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "project_title": "Biomedical Research",
                    "abstract_text": "Advanced biomedical studies",
                    "project_terms": ["biomedical", "research"],
                    "agency_ic_admin": {"name": "NIAID"},
                    "fiscal_year": 2024,
                }
            ]
        }

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(solicitation_id="RFA-AI-24-001")

            assert result is not None
            assert result.solicitation_id == "RFA-AI-24-001"
            assert "Biomedical Research" in result.description

            client.close()

    def test_lookup_returns_none_on_404(self) -> None:
        """Should return None when solicitation not found (404)."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="NONEXISTENT")

            assert result is None

            client.close()

    def test_lookup_returns_none_on_timeout(self) -> None:
        """Should return None on request timeout."""
        with patch.object(httpx.Client, "post", side_effect=httpx.TimeoutException("Timeout")):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="PA-23-123")

            assert result is None

            client.close()

    def test_lookup_raises_on_non_404_error(self) -> None:
        """Should raise NIHAPIError on non-404 HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()

            with pytest.raises(NIHAPIError, match="status 503"):
                client.lookup_solicitation(funding_opportunity="PA-23-123")

            client.close()

    def test_lookup_raises_on_http_error(self) -> None:
        """Should raise NIHAPIError on HTTP errors."""
        with patch.object(
            httpx.Client,
            "post",
            side_effect=httpx.HTTPError("Network error"),
        ):
            client = NIHClient()

            with pytest.raises(NIHAPIError, match="HTTP error"):
                client.lookup_solicitation(funding_opportunity="PA-23-123")

            client.close()

    def test_lookup_requires_identifier(self) -> None:
        """Should raise ValueError if no identifier provided."""
        client = NIHClient()

        with pytest.raises(ValueError, match="Must provide either"):
            client.lookup_solicitation()

        client.close()

    def test_lookup_with_empty_results(self) -> None:
        """Should return None when API returns no results."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="PA-23-123")

            assert result is None

            client.close()

    def test_lookup_with_missing_description_fields(self) -> None:
        """Should return None when project has no description fields."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "project_title": "",
                    "abstract_text": "",
                    "phr_text": "",
                    "project_terms": ["term1"],
                }
            ]
        }

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="PA-23-123")

            assert result is None

            client.close()


class TestParseResponse:
    """Tests for response parsing logic."""

    def test_parse_combines_title_and_abstract(self) -> None:
        """Should combine title and abstract in description."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "project_title": "Cancer Research",
                    "abstract_text": "Detailed abstract about cancer research",
                    "project_terms": ["cancer"],
                    "fiscal_year": 2023,
                }
            ]
        }

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="PA-23-123")

            assert result is not None
            assert "Cancer Research" in result.description
            assert "Detailed abstract" in result.description

            client.close()

    def test_parse_includes_phr_text(self) -> None:
        """Should include public health relevance in description."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "project_title": "Research Title",
                    "abstract_text": "Abstract text",
                    "phr_text": "Public health relevance statement",
                    "project_terms": ["research"],
                    "fiscal_year": 2023,
                }
            ]
        }

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="PA-23-123")

            assert result is not None
            assert "Public health relevance" in result.description

            client.close()

    def test_parse_with_malformed_data(self) -> None:
        """Should return None when parsing fails."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    # Missing required fields
                }
            ]
        }

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="PA-23-123")

            assert result is None

            client.close()


class TestExtractKeywords:
    """Tests for keyword extraction logic."""

    def test_extract_keywords_from_project_terms(self) -> None:
        """Should extract keywords from project terms."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "project_title": "Test Project",
                    "project_terms": ["cancer", "immunotherapy", "biomarkers"],
                    "fiscal_year": 2023,
                }
            ]
        }

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="PA-23-123")

            assert result is not None
            assert "cancer" in result.technical_keywords
            assert "immunotherapy" in result.technical_keywords
            assert "biomarkers" in result.technical_keywords

            client.close()

    def test_extract_keywords_from_agency(self) -> None:
        """Should extract keywords from agency information."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "project_title": "Test Project",
                    "project_terms": [],
                    "agency_ic_admin": {"name": "National Cancer Institute"},
                    "activity_code": "R43",
                    "fiscal_year": 2023,
                }
            ]
        }

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="PA-23-123")

            assert result is not None
            assert "National Cancer Institute" in result.technical_keywords
            assert "R43" in result.technical_keywords
            assert "FY2023" in result.technical_keywords

            client.close()

    def test_extract_keywords_deduplication(self) -> None:
        """Should deduplicate keywords."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "project_title": "Test Project",
                    "project_terms": ["cancer", "cancer", "research"],
                    "fiscal_year": 2023,
                }
            ]
        }

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="PA-23-123")

            assert result is not None
            keyword_counts = sum(1 for kw in result.technical_keywords if kw == "cancer")
            assert keyword_counts == 1

            client.close()

    def test_extract_keywords_with_empty_terms(self) -> None:
        """Should handle empty project terms gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "project_title": "Test Project",
                    "project_terms": [],
                    "fiscal_year": 2023,
                }
            ]
        }

        with patch.object(httpx.Client, "post", return_value=mock_response):
            client = NIHClient()
            result = client.lookup_solicitation(funding_opportunity="PA-23-123")

            assert result is not None
            assert isinstance(result.technical_keywords, list)

            client.close()


class TestMakeRequest:
    """Tests for request construction."""

    def test_request_uses_post_method(self) -> None:
        """Should use POST method for NIH Reporter API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}

        with patch.object(httpx.Client, "post", return_value=mock_response) as mock_post:
            client = NIHClient()
            client.lookup_solicitation(funding_opportunity="PA-23-123")

            # Verify POST was called
            mock_post.assert_called_once()

            # Verify payload structure
            call_kwargs = mock_post.call_args
            assert "json" in call_kwargs.kwargs
            payload = call_kwargs.kwargs["json"]
            assert "criteria" in payload
            assert "foa" in payload["criteria"]
            assert "PA-23-123" in payload["criteria"]["foa"]

            client.close()
