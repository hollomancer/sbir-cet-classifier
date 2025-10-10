"""Unit tests for NSF API client with mocked responses."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from sbir_cet_classifier.data.external.nsf import (
    NSFClient,
    SolicitationData,
)


class TestNSFClient:
    """Tests for NSFClient initialization and lifecycle."""

    def test_client_initialization_defaults(self) -> None:
        """Should initialize with default configuration."""
        client = NSFClient()

        assert client.base_url == "https://api.nsf.gov/services/v1"
        assert client.timeout == 30.0
        assert client.client is not None

        client.close()

    def test_client_initialization_custom_config(self) -> None:
        """Should initialize with custom configuration."""
        client = NSFClient(
            base_url="https://test.nsf.gov/api",
            timeout=50.0,
        )

        assert client.base_url == "https://test.nsf.gov/api"
        assert client.timeout == 50.0

        client.close()

    def test_client_context_manager(self) -> None:
        """Should work as context manager."""
        with NSFClient() as client:
            assert client.client is not None

    def test_client_close(self) -> None:
        """Should close HTTP client cleanly."""
        client = NSFClient()
        client.close()

        # Should not raise exception on double close
        client.close()


class TestLookupSolicitation:
    """Tests for lookup_solicitation method."""

    def test_lookup_by_program_element_success(self) -> None:
        """Should successfully lookup solicitation by program element code."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": [
                    {
                        "title": "Sustainable Energy Technologies",
                        "abstractText": "Research in renewable energy solutions",
                        "fundProgramName": "SBIR Phase I",
                        "directorate": {"name": "Engineering"},
                        "division": {"name": "Industrial Innovation"},
                        "instrument": {"value": "Standard Grant"},
                    }
                ]
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is not None
            assert isinstance(result, SolicitationData)
            assert result.solicitation_id == "1505"
            assert "Sustainable Energy" in result.description
            assert "SBIR Phase I" in result.technical_keywords
            assert result.api_source == "nsf"

            client.close()

    def test_lookup_by_topic_code_success(self) -> None:
        """Should successfully lookup solicitation by topic code."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": {
                    "title": "Advanced Manufacturing",
                    "abstractText": "Manufacturing innovation research",
                    "fundProgramName": "SBIR",
                }
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(topic_code="NSF-24-001")

            assert result is not None
            assert result.solicitation_id == "NSF-24-001"
            assert "Advanced Manufacturing" in result.description

            client.close()

    def test_lookup_returns_none_on_404(self) -> None:
        """Should return None when solicitation not found (404)."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="9999")

            assert result is None

            client.close()

    def test_lookup_returns_none_on_timeout(self) -> None:
        """Should return None on request timeout (graceful degradation)."""
        with patch.object(httpx.Client, "get", side_effect=httpx.TimeoutException("Timeout")):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is None

            client.close()

    def test_lookup_returns_none_on_non_200_status(self) -> None:
        """Should return None on non-200 status (graceful degradation)."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            # NSF client gracefully degrades instead of raising
            assert result is None

            client.close()

    def test_lookup_returns_none_on_http_error(self) -> None:
        """Should return None on HTTP errors (graceful degradation)."""
        with patch.object(
            httpx.Client,
            "get",
            side_effect=httpx.HTTPError("Connection error"),
        ):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            # NSF client gracefully degrades
            assert result is None

            client.close()

    def test_lookup_requires_identifier(self) -> None:
        """Should raise ValueError if no identifier provided."""
        client = NSFClient()

        with pytest.raises(ValueError, match="Must provide either"):
            client.lookup_solicitation()

        client.close()

    def test_lookup_with_empty_awards(self) -> None:
        """Should return None when API returns no awards."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"award": []}}

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is None

            client.close()

    def test_lookup_with_missing_title_and_abstract(self) -> None:
        """Should return None when award has no title or abstract."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": [
                    {
                        "title": "",
                        "abstractText": "",
                        "fundProgramName": "SBIR",
                    }
                ]
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is None

            client.close()


class TestParseResponse:
    """Tests for response parsing logic."""

    def test_parse_combines_title_and_abstract(self) -> None:
        """Should combine title and abstract in description."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": [
                    {
                        "title": "Energy Research Project",
                        "abstractText": "Detailed description of energy research",
                        "fundProgramName": "SBIR",
                    }
                ]
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is not None
            assert "Energy Research Project" in result.description
            assert "Detailed description" in result.description

            client.close()

    def test_parse_handles_single_award_as_dict(self) -> None:
        """Should handle single award returned as dict instead of list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": {  # Single dict, not list
                    "title": "Single Award",
                    "abstractText": "Single award description",
                    "fundProgramName": "SBIR",
                }
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is not None
            assert "Single Award" in result.description

            client.close()

    def test_parse_with_malformed_data_gracefully_degrades(self) -> None:
        """Should return None when parsing fails (graceful degradation)."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": [
                    {
                        # Missing required fields
                    }
                ]
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            # Gracefully degrades
            assert result is None

            client.close()


class TestExtractKeywords:
    """Tests for keyword extraction logic."""

    def test_extract_keywords_from_program_name(self) -> None:
        """Should extract keywords from program name."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": [
                    {
                        "title": "Test Project",
                        "abstractText": "Test abstract",
                        "fundProgramName": "SBIR Phase I",
                    }
                ]
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is not None
            assert "SBIR Phase I" in result.technical_keywords

            client.close()

    def test_extract_keywords_from_directorate_and_division(self) -> None:
        """Should extract keywords from directorate and division."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": [
                    {
                        "title": "Test Project",
                        "abstractText": "Test abstract",
                        "directorate": {"name": "Engineering"},
                        "division": {"name": "Industrial Innovation"},
                    }
                ]
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is not None
            assert "Engineering" in result.technical_keywords
            assert "Industrial Innovation" in result.technical_keywords

            client.close()

    def test_extract_keywords_from_instrument(self) -> None:
        """Should extract keywords from instrument type."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": [
                    {
                        "title": "Test Project",
                        "abstractText": "Test abstract",
                        "instrument": {"value": "Standard Grant"},
                    }
                ]
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is not None
            assert "Standard Grant" in result.technical_keywords

            client.close()

    def test_extract_keywords_from_program_officer(self) -> None:
        """Should extract program officer as metadata."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": [
                    {
                        "title": "Test Project",
                        "abstractText": "Test abstract",
                        "programOfficer": {"name": "John Smith"},
                    }
                ]
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is not None
            assert "PO:John Smith" in result.technical_keywords

            client.close()

    def test_extract_keywords_deduplication(self) -> None:
        """Should deduplicate keywords."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": [
                    {
                        "title": "Test Project",
                        "abstractText": "Test abstract",
                        "fundProgramName": "SBIR",
                        "awardeeName": "SBIR",  # Duplicate
                    }
                ]
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is not None
            keyword_counts = sum(1 for kw in result.technical_keywords if kw == "SBIR")
            assert keyword_counts == 1

            client.close()

    def test_extract_keywords_with_empty_fields(self) -> None:
        """Should handle empty keyword fields gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "award": [
                    {
                        "title": "Test Project",
                        "abstractText": "Test abstract",
                        "fundProgramName": None,
                        "directorate": {},
                    }
                ]
            }
        }

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()
            result = client.lookup_solicitation(program_element="1505")

            assert result is not None
            assert isinstance(result.technical_keywords, list)

            client.close()


class TestMakeRequest:
    """Tests for request construction."""

    def test_request_uses_get_method(self) -> None:
        """Should use GET method for NSF Awards API."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"award": []}}

        with patch.object(httpx.Client, "get", return_value=mock_response) as mock_get:
            client = NSFClient()
            client.lookup_solicitation(program_element="1505")

            # Verify GET was called
            mock_get.assert_called_once()

            # Verify query parameters
            call_kwargs = mock_get.call_args
            assert "params" in call_kwargs.kwargs
            params = call_kwargs.kwargs["params"]
            assert "programElementCode" in params
            assert params["programElementCode"] == "1505"

            client.close()


class TestGracefulDegradation:
    """Tests for NSF-specific graceful degradation behavior."""

    def test_logs_warning_on_non_200_status(self) -> None:
        """Should log warning but not raise on non-200 status."""
        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch.object(httpx.Client, "get", return_value=mock_response):
            client = NSFClient()

            # Should not raise, just return None
            result = client.lookup_solicitation(program_element="1505")
            assert result is None

            client.close()

    def test_logs_warning_on_http_error(self) -> None:
        """Should log warning but not raise on HTTP errors."""
        with patch.object(httpx.Client, "get", side_effect=httpx.HTTPError("Error")):
            client = NSFClient()

            # Should not raise, just return None
            result = client.lookup_solicitation(program_element="1505")
            assert result is None

            client.close()

    def test_logs_warning_on_timeout(self) -> None:
        """Should log warning but not raise on timeout."""
        with patch.object(httpx.Client, "get", side_effect=httpx.TimeoutException("Timeout")):
            client = NSFClient()

            # Should not raise, just return None
            result = client.lookup_solicitation(program_element="1505")
            assert result is None

            client.close()
