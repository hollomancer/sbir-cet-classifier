"""NIH API client for solicitation enrichment.

This module provides a client for querying the NIH (National Institutes of Health)
API to retrieve solicitation descriptions and technical topic keywords for SBIR awards.

Typical usage:
    from sbir_cet_classifier.data.external.nih import NIHClient

    client = NIHClient()
    result = client.lookup_solicitation(funding_opportunity="PA-23-123")
    if result:
        print(f"Description: {result.description}")
        print(f"Keywords: {result.technical_keywords}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# NIH API configuration
NIH_API_BASE = "https://api.reporter.nih.gov/v2"
DEFAULT_TIMEOUT = 30.0  # seconds
MAX_RETRIES = 3


@dataclass
class SolicitationData:
    """Solicitation metadata returned from NIH API."""

    solicitation_id: str
    """Agency-specific solicitation identifier (e.g., FOA number)."""

    description: str
    """Solicitation description text."""

    technical_keywords: list[str]
    """Technical topic keywords extracted from solicitation."""

    api_source: str = "nih"
    """Source API identifier for cache keying."""


class NIHAPIError(Exception):
    """Raised when NIH API request fails."""


class NIHClient:
    """Client for NIH Reporter API.

    Provides methods to lookup SBIR solicitation metadata by funding
    opportunity announcement (FOA) number or other NIH-specific identifiers.

    Attributes:
        base_url: Base URL for NIH Reporter API
        timeout: Request timeout in seconds
        client: HTTP client instance
    """

    def __init__(
        self,
        *,
        base_url: str = NIH_API_BASE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize NIH API client.

        Args:
            base_url: Base URL for API (default: production endpoint)
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def __enter__(self) -> NIHClient:
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
        funding_opportunity: str | None = None,
        solicitation_id: str | None = None,
    ) -> SolicitationData | None:
        """Look up solicitation metadata by FOA or solicitation ID.

        Args:
            funding_opportunity: NIH FOA number (e.g., "PA-23-123", "RFA-CA-23-001")
            solicitation_id: Alternative solicitation identifier

        Returns:
            SolicitationData if found, None if not found or on timeout

        Raises:
            NIHAPIError: For API errors other than 404/timeout
            ValueError: If neither funding_opportunity nor solicitation_id provided

        Example:
            >>> client = NIHClient()
            >>> result = client.lookup_solicitation(funding_opportunity="PA-23-123")
            >>> if result:
            ...     print(result.description)
        """
        if not funding_opportunity and not solicitation_id:
            raise ValueError("Must provide either funding_opportunity or solicitation_id")

        query_id = funding_opportunity or solicitation_id
        assert query_id is not None  # For type checker

        logger.debug(
            "Looking up NIH solicitation",
            extra={"funding_opportunity": funding_opportunity, "solicitation_id": solicitation_id},
        )

        try:
            response = self._make_request(query_id)

            if response.status_code == 404:
                logger.info("Solicitation not found in NIH", extra={"query_id": query_id})
                return None

            if response.status_code != 200:
                raise NIHAPIError(f"NIH API returned status {response.status_code}: {response.text}")

            return self._parse_response(response.json(), query_id)

        except httpx.TimeoutException:
            logger.warning("NIH API timeout", extra={"query_id": query_id})
            return None

        except httpx.HTTPError as e:
            logger.error("NIH API HTTP error", extra={"query_id": query_id, "error": str(e)})
            raise NIHAPIError(f"HTTP error querying NIH: {e}") from e

    def _make_request(self, query_id: str) -> httpx.Response:
        """Make HTTP request to NIH Reporter API.

        Args:
            query_id: Funding opportunity or solicitation identifier

        Returns:
            HTTP response object

        Raises:
            httpx.HTTPError: For network/HTTP errors
        """
        # NIH Reporter API endpoint structure
        # The actual endpoint depends on whether we're searching projects or FOAs
        # For solicitations/FOAs, we'd use a different endpoint than project data
        endpoint = f"{self.base_url}/projects/search"

        # Search criteria for NIH Reporter API
        payload = {
            "criteria": {
                "foa": [query_id],  # Funding opportunity announcement number
            },
            "offset": 0,
            "limit": 1,
        }

        logger.debug("Making NIH API request", extra={"endpoint": endpoint, "payload": payload})

        response = self.client.post(endpoint, json=payload)
        return response

    def _parse_response(self, data: dict, query_id: str) -> SolicitationData | None:
        """Parse API response into SolicitationData.

        Args:
            data: Parsed JSON response from API
            query_id: Original query identifier

        Returns:
            SolicitationData if parsing succeeds, None if data incomplete

        Note:
            NIH Reporter API returns project data. For solicitation details,
            we extract relevant fields from the FOA metadata.
        """
        try:
            # NIH Reporter API response structure
            results = data.get("results", [])
            if not results:
                logger.info("No results in NIH response", extra={"query_id": query_id})
                return None

            # Take first matching result
            project = results[0]

            # Extract description from various fields
            description_fields = [
                "project_title",
                "abstract_text",
                "phr_text",  # Public health relevance
            ]

            description_parts = []
            for field in description_fields:
                value = project.get(field)
                if value and isinstance(value, str):
                    description_parts.append(value.strip())

            if not description_parts:
                logger.warning("No description in NIH response", extra={"query_id": query_id})
                return None

            description = " ".join(description_parts)

            # Extract keywords
            keywords = self._extract_keywords(project)

            return SolicitationData(
                solicitation_id=query_id,
                description=description,
                technical_keywords=keywords,
                api_source="nih",
            )

        except (KeyError, ValueError, TypeError) as e:
            logger.warning(
                "Failed to parse NIH response",
                extra={"query_id": query_id, "error": str(e)},
            )
            return None

    def _extract_keywords(self, project: dict) -> list[str]:
        """Extract technical keywords from project data.

        Args:
            project: Parsed project object from API response

        Returns:
            List of technical keywords
        """
        keywords: list[str] = []

        # Extract from project terms (MeSH terms, etc.)
        project_terms = project.get("project_terms", [])
        if isinstance(project_terms, list):
            keywords.extend(str(term) for term in project_terms if term)

        # Extract from agencies and activity codes
        agency = project.get("agency_ic_admin", {})
        if isinstance(agency, dict):
            agency_name = agency.get("name")
            if agency_name:
                keywords.append(str(agency_name))

        # Activity code provides program type information
        activity_code = project.get("activity_code")
        if activity_code:
            keywords.append(str(activity_code))

        # Extract from award notice date year for temporal context
        fiscal_year = project.get("fiscal_year")
        if fiscal_year:
            keywords.append(f"FY{fiscal_year}")

        # Deduplicate and clean
        return list(set(kw.strip() for kw in keywords if kw and str(kw).strip()))
