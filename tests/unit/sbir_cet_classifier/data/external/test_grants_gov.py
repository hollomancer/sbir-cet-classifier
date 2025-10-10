"""Unit tests for Grants.gov API client with mocked responses."""

from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock, patch

import httpx
import pytest

from sbir_cet_classifier.data.external.grants_gov import (
    GrantsGovAPIError,
    GrantsGovClient,
    SolicitationData,
)


class TestGrantsGovClient:
    """Tests for GrantsGovClient initialization and lifecycle."""

    def test_client_initialization_defaults(self) -> None:
        """Should initialize with default configuration."""
        client = GrantsGovClient()

        assert client.base_url == "https://www.grants.gov/grantsws/rest"
        assert client.timeout == 30.0
        assert client.client is not None

        client.close()

    def test_client_initialization_custom_config(self) -> None:
        """Should initialize with custom configuration."""
        client = GrantsGovClient(
            base_url="https://test.grants.gov/api",
            timeout=60.0,
        )

        assert client.base_url == "https://test.grants.gov/api"
        assert client.timeout == 60.0

        client.close()

    def test_client_context_manager(self) -> None:
        """Should work as context manager."""
        with GrantsGovClient() as client:
            assert client.client is not None

        # Client should be closed after context exit
        # (httpx.Client.is_closed doesn't exist, so we just verify no exception)

    def test_client_close(self) -> None:
        """Should close HTTP client cleanly."""
        client = GrantsGovClient()
        client.close()

        # Should not raise exception on double close
        client.close()


class TestLookupSolicitation:
    """Tests for lookup_solicitation method."""

    def test_lookup_by_topic_code_success(self) -> None:
        """Should successfully lookup solicitation by topic code."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "oppHits": [
                {
                    "synopsis": "SBIR Phase I: Advanced AI Technologies",
                    "description": "Research in artificial intelligence",
                    "fundingInstruments": ["Grant"],
                    "categories": ["Science and Technology"],
                    "additionalInformation": {
                        "technicalTopics": ["AI", "Machine Learning"],
                    },
                }
            ]
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="AF241-001")

            assert result is not None
            assert isinstance(result, SolicitationData)
            assert result.solicitation_id == "AF241-001"
            assert "Advanced AI" in result.description
            assert "AI" in result.technical_keywords
            assert result.api_source == "grants.gov"

            client.close()

    def test_lookup_by_solicitation_number_success(self) -> None:
        """Should successfully lookup solicitation by solicitation number."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "oppHits": [
                {
                    "synopsis": "SBIR Solicitation 2024-001",
                    "description": "Technology development",
                    "fundingInstruments": ["Cooperative Agreement"],
                }
            ]
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(solicitation_number="SOL-2024-001")

            assert result is not None
            assert result.solicitation_id == "SOL-2024-001"
            assert "Technology development" in result.description

            client.close()

    def test_lookup_returns_none_on_404(self) -> None:
        """Should return None when solicitation not found (404)."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="NONEXISTENT")

            assert result is None

            client.close()

    def test_lookup_returns_none_on_timeout(self) -> None:
        """Should return None on request timeout."""
        with patch.object(httpx.Client, "get", side_effect=httpx.TimeoutException("Timeout")):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="AF241-001")

            assert result is None

            client.close()

    def test_lookup_raises_on_non_404_error(self) -> None:
        """Should raise GrantsGovAPIError on non-404 HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()

            with pytest.raises(GrantsGovAPIError, match="status 500"):
                client.lookup_solicitation(topic_code="AF241-001")

            client.close()

    def test_lookup_raises_on_http_error(self) -> None:
        """Should raise GrantsGovAPIError on HTTP errors."""
        with patch.object(
            httpx.Client,
            "get",
            side_effect=httpx.HTTPError("Connection error"),
        ):
            client = GrantsGovClient()

            with pytest.raises(GrantsGovAPIError, match="HTTP error"):
                client.lookup_solicitation(topic_code="AF241-001")

            client.close()

    def test_lookup_requires_identifier(self) -> None:
        """Should raise ValueError if no identifier provided."""
        client = GrantsGovClient()

        with pytest.raises(ValueError, match="Must provide either"):
            client.lookup_solicitation()

        client.close()

    def test_lookup_with_empty_response(self) -> None:
        """Should return None when API returns empty opportunities."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"oppHits": []}

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="AF241-001")

            assert result is None

            client.close()

    def test_lookup_with_missing_description(self) -> None:
        """Should return None when opportunity has no description."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "oppHits": [
                {
                    "synopsis": "",
                    "description": "",
                    "fundingInstruments": ["Grant"],
                }
            ]
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="AF241-001")

            assert result is None

            client.close()


class TestParseResponse:
    """Tests for response parsing logic."""

    def test_parse_response_with_synopsis(self) -> None:
        """Should parse response using synopsis field."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "oppHits": [
                {
                    "synopsis": "SBIR Phase I Research",
                    "fundingInstruments": ["Grant"],
                }
            ]
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="TEST-001")

            assert result is not None
            assert "SBIR Phase I Research" in result.description

            client.close()

    def test_parse_response_with_description_fallback(self) -> None:
        """Should fallback to description field if synopsis empty."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "oppHits": [
                {
                    "synopsis": "",
                    "description": "Full description text",
                    "fundingInstruments": ["Grant"],
                }
            ]
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="TEST-001")

            assert result is not None
            assert "Full description text" in result.description

            client.close()

    def test_parse_response_with_malformed_data(self) -> None:
        """Should return None when response parsing fails."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "oppHits": [
                {
                    # Missing required fields
                }
            ]
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="TEST-001")

            assert result is None

            client.close()


class TestExtractKeywords:
    """Tests for keyword extraction logic."""

    def test_extract_keywords_from_funding_instruments(self) -> None:
        """Should extract keywords from funding instruments."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "oppHits": [
                {
                    "synopsis": "Test solicitation",
                    "fundingInstruments": ["Grant", "Cooperative Agreement"],
                    "categories": ["Science"],
                }
            ]
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="TEST-001")

            assert result is not None
            assert "Grant" in result.technical_keywords
            assert "Cooperative Agreement" in result.technical_keywords
            assert "Science" in result.technical_keywords

            client.close()

    def test_extract_keywords_from_technical_topics(self) -> None:
        """Should extract keywords from technical topics in additional info."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "oppHits": [
                {
                    "synopsis": "Test solicitation",
                    "additionalInformation": {
                        "technicalTopics": ["AI", "Robotics", "Machine Learning"],
                    },
                }
            ]
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="TEST-001")

            assert result is not None
            assert "AI" in result.technical_keywords
            assert "Robotics" in result.technical_keywords
            assert "Machine Learning" in result.technical_keywords

            client.close()

    def test_extract_keywords_deduplication(self) -> None:
        """Should deduplicate keywords."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "oppHits": [
                {
                    "synopsis": "Test solicitation",
                    "fundingInstruments": ["Grant", "Grant"],  # Duplicate
                    "categories": ["Grant"],  # Duplicate across fields
                }
            ]
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="TEST-001")

            assert result is not None
            # Should only have one "Grant" despite duplicates
            keyword_counts = sum(1 for kw in result.technical_keywords if kw == "Grant")
            assert keyword_counts == 1

            client.close()

    def test_extract_keywords_with_empty_fields(self) -> None:
        """Should handle empty keyword fields gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "oppHits": [
                {
                    "synopsis": "Test solicitation",
                    "fundingInstruments": [],
                    "categories": None,
                    "additionalInformation": {},
                }
            ]
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = GrantsGovClient()
            result = client.lookup_solicitation(topic_code="TEST-001")

            assert result is not None
            assert isinstance(result.technical_keywords, list)
            # May be empty or have minimal keywords

            client.close()
