"""Grants.gov API client for solicitation enrichment.

This module provides a client for querying the Grants.gov API to retrieve
solicitation descriptions and technical topic keywords for SBIR awards.

Typical usage:
    from sbir_cet_classifier.data.external.grants_gov import GrantsGovClient

    client = GrantsGovClient()
    result = client.lookup_solicitation(
        topic_code="TOPIC-123",
        solicitation_number="SOL-2023-001"
    )
    if result:
        print(f"Description: {result.description}")
        print(f"Keywords: {result.technical_keywords}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Grants.gov API configuration
GRANTS_GOV_API_BASE = "https://www.grants.gov/grantsws/rest"
DEFAULT_TIMEOUT = 30.0  # seconds
MAX_RETRIES = 3


@dataclass
class SolicitationData:
    """Solicitation metadata returned from Grants.gov API."""

    solicitation_id: str
    """Agency-specific solicitation identifier."""

    description: str
    """Solicitation description text."""

    technical_keywords: list[str]
    """Technical topic keywords extracted from solicitation."""

    api_source: str = "grants.gov"
    """Source API identifier for cache keying."""


class GrantsGovAPIError(Exception):
    """Raised when Grants.gov API request fails."""


class GrantsGovClient:
    """Client for Grants.gov solicitation API.

    Provides methods to lookup SBIR solicitation metadata by topic code
    or solicitation number, with error handling for 404s and timeouts.

    Attributes:
        base_url: Base URL for Grants.gov REST API
        timeout: Request timeout in seconds
        client: HTTP client instance
    """

    def __init__(
        self,
        *,
        base_url: str = GRANTS_GOV_API_BASE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize Grants.gov API client.

        Args:
            base_url: Base URL for API (default: production endpoint)
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def __enter__(self) -> GrantsGovClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args: object) -> None:
        """Context manager exit - closes HTTP client."""
        self.close()

    def close(self) -> None:
        """Close HTTP client connection."""
        self.client.close()

    def lookup_solicitation(
        self,
        *,
        topic_code: Optional[str] = None,
        solicitation_number: Optional[str] = None,
    ) -> Optional[SolicitationData]:
        """Look up solicitation metadata by topic code or solicitation number.

        Args:
            topic_code: SBIR topic code (e.g., "AF241-001")
            solicitation_number: Full solicitation number (e.g., "HHS-NIH-NIDDK-2023-1")

        Returns:
            SolicitationData if found, None if not found (404) or on timeout

        Raises:
            GrantsGovAPIError: For API errors other than 404/timeout
            ValueError: If neither topic_code nor solicitation_number provided

        Example:
            >>> client = GrantsGovClient()
            >>> result = client.lookup_solicitation(topic_code="AF241-001")
            >>> if result:
            ...     print(result.description)
        """
        if not topic_code and not solicitation_number:
            raise ValueError("Must provide either topic_code or solicitation_number")

        # Construct query identifier
        query_id = topic_code or solicitation_number
        assert query_id is not None  # For type checker

        logger.debug(
            "Looking up Grants.gov solicitation",
            extra={"topic_code": topic_code, "solicitation_number": solicitation_number},
        )

        try:
            response = self._make_request(query_id)

            if response.status_code == 404:
                logger.info("Solicitation not found in Grants.gov", extra={"query_id": query_id})
                return None

            if response.status_code != 200:
                raise GrantsGovAPIError(
                    f"Grants.gov API returned status {response.status_code}: {response.text}"
                )

            return self._parse_response(response.json(), query_id)

        except httpx.TimeoutException:
            logger.warning("Grants.gov API timeout", extra={"query_id": query_id})
            return None

        except httpx.HTTPError as e:
            logger.error("Grants.gov API HTTP error", extra={"query_id": query_id, "error": str(e)})
            raise GrantsGovAPIError(f"HTTP error querying Grants.gov: {e}") from e

    def _make_request(self, query_id: str) -> httpx.Response:
        """Make HTTP request to Grants.gov API.

        Args:
            query_id: Solicitation identifier to query

        Returns:
            HTTP response object

        Raises:
            httpx.HTTPError: For network/HTTP errors
        """
        # Grants.gov API endpoint structure (example - adjust to actual API)
        # Real implementation would need actual Grants.gov API documentation
        endpoint = f"{self.base_url}/opportunities/search"
        params = {
            "keyword": query_id,
            "oppNum": query_id,
        }

        logger.debug("Making Grants.gov API request", extra={"endpoint": endpoint, "params": params})

        response = self.client.get(endpoint, params=params)
        return response

    def _parse_response(self, data: dict, query_id: str) -> Optional[SolicitationData]:
        """Parse API response into SolicitationData.

        Args:
            data: Parsed JSON response from API
            query_id: Original query identifier

        Returns:
            SolicitationData if parsing succeeds, None if data incomplete

        Note:
            This is a placeholder implementation. Actual parsing logic depends
            on the real Grants.gov API response structure.
        """
        try:
            # Example structure - adjust to actual Grants.gov API response
            # Real API likely returns an array of opportunities
            opportunities = data.get("oppHits", [])
            if not opportunities:
                logger.info("No opportunities in Grants.gov response", extra={"query_id": query_id})
                return None

            # Take first matching opportunity
            opp = opportunities[0]

            description = opp.get("synopsis", "") or opp.get("description", "")
            if not description:
                logger.warning("No description in Grants.gov response", extra={"query_id": query_id})
                return None

            # Extract keywords from various fields
            keywords = self._extract_keywords(opp)

            return SolicitationData(
                solicitation_id=query_id,
                description=description.strip(),
                technical_keywords=keywords,
                api_source="grants.gov",
            )

        except (KeyError, ValueError, TypeError) as e:
            logger.warning(
                "Failed to parse Grants.gov response",
                extra={"query_id": query_id, "error": str(e)},
            )
            return None

    def _extract_keywords(self, opportunity: dict) -> list[str]:
        """Extract technical keywords from opportunity data.

        Args:
            opportunity: Parsed opportunity object from API response

        Returns:
            List of technical keywords
        """
        keywords: list[str] = []

        # Example fields - adjust to actual API structure
        keyword_fields = [
            "fundingInstruments",
            "eligibleApplicants",
            "categories",
            "cfda",
        ]

        for field in keyword_fields:
            value = opportunity.get(field)
            if isinstance(value, list):
                keywords.extend(str(v) for v in value if v)
            elif isinstance(value, str) and value:
                keywords.append(value)

        # Also extract from additional details if present
        additional_info = opportunity.get("additionalInformation", {})
        if isinstance(additional_info, dict):
            tech_topics = additional_info.get("technicalTopics", [])
            if isinstance(tech_topics, list):
                keywords.extend(str(t) for t in tech_topics if t)

        # Deduplicate and clean
        return list(set(kw.strip() for kw in keywords if kw and str(kw).strip()))
