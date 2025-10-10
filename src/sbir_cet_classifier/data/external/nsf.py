"""NSF API client for solicitation enrichment.

This module provides a client for querying the NSF (National Science Foundation)
API to retrieve solicitation descriptions and technical topic keywords for SBIR awards.

Typical usage:
    from sbir_cet_classifier.data.external.nsf import NSFClient

    client = NSFClient()
    result = client.lookup_solicitation(program_element="1505")
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

# NSF API configuration
NSF_API_BASE = "https://api.nsf.gov/services/v1"
DEFAULT_TIMEOUT = 30.0  # seconds
MAX_RETRIES = 3


@dataclass
class SolicitationData:
    """Solicitation metadata returned from NSF API."""

    solicitation_id: str
    """Agency-specific solicitation identifier (e.g., program element code)."""

    description: str
    """Solicitation description text."""

    technical_keywords: list[str]
    """Technical topic keywords extracted from solicitation."""

    api_source: str = "nsf"
    """Source API identifier for cache keying."""


class NSFAPIError(Exception):
    """Raised when NSF API request fails."""


class NSFClient:
    """Client for NSF Awards API.

    Provides methods to lookup SBIR solicitation metadata by program element
    code or other NSF-specific identifiers, with graceful degradation when
    solicitations are unmatched.

    Attributes:
        base_url: Base URL for NSF API
        timeout: Request timeout in seconds
        client: HTTP client instance
    """

    def __init__(
        self,
        *,
        base_url: str = NSF_API_BASE,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize NSF API client.

        Args:
            base_url: Base URL for API (default: production endpoint)
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def __enter__(self) -> NSFClient:
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
        program_element: Optional[str] = None,
        topic_code: Optional[str] = None,
    ) -> Optional[SolicitationData]:
        """Look up solicitation metadata by program element or topic code.

        Args:
            program_element: NSF program element code (e.g., "1505" for SBIR)
            topic_code: Alternative topic identifier

        Returns:
            SolicitationData if found, None if not found or on timeout

        Raises:
            NSFAPIError: For API errors other than 404/timeout
            ValueError: If neither program_element nor topic_code provided

        Example:
            >>> client = NSFClient()
            >>> result = client.lookup_solicitation(program_element="1505")
            >>> if result:
            ...     print(result.description)

        Note:
            NSF API gracefully degrades when solicitations are unmatched,
            returning None rather than raising errors.
        """
        if not program_element and not topic_code:
            raise ValueError("Must provide either program_element or topic_code")

        query_id = program_element or topic_code
        assert query_id is not None  # For type checker

        logger.debug(
            "Looking up NSF solicitation",
            extra={"program_element": program_element, "topic_code": topic_code},
        )

        try:
            response = self._make_request(query_id)

            if response.status_code == 404:
                logger.info("Solicitation not found in NSF", extra={"query_id": query_id})
                return None

            if response.status_code != 200:
                # Log but don't raise - graceful degradation per FR-008
                logger.warning(
                    "NSF API returned non-200 status, gracefully degrading",
                    extra={"query_id": query_id, "status_code": response.status_code},
                )
                return None

            return self._parse_response(response.json(), query_id)

        except httpx.TimeoutException:
            logger.warning("NSF API timeout, gracefully degrading", extra={"query_id": query_id})
            return None

        except httpx.HTTPError as e:
            # Log but don't raise - graceful degradation
            logger.warning(
                "NSF API HTTP error, gracefully degrading",
                extra={"query_id": query_id, "error": str(e)},
            )
            return None

    def _make_request(self, query_id: str) -> httpx.Response:
        """Make HTTP request to NSF API.

        Args:
            query_id: Program element or topic identifier

        Returns:
            HTTP response object

        Raises:
            httpx.HTTPError: For network/HTTP errors
        """
        # NSF API endpoint structure for awards search
        endpoint = f"{self.base_url}/awards"

        # Query parameters for NSF API
        # The actual parameter names depend on NSF API documentation
        params = {
            "programElementCode": query_id,
            "printFields": "id,title,abstractText,fundProgramName,pdPIName,startDate,expDate",
            "offset": "1",
            "limit": "1",
        }

        logger.debug("Making NSF API request", extra={"endpoint": endpoint, "params": params})

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
            NSF API returns award data. We extract solicitation-level
            information from program metadata and abstracts.
        """
        try:
            # NSF API response structure typically has awards array
            awards = data.get("response", {}).get("award", [])

            if not awards:
                logger.info("No awards in NSF response", extra={"query_id": query_id})
                return None

            # If awards is a dict (single result), wrap in list
            if isinstance(awards, dict):
                awards = [awards]

            # Take first matching award
            award = awards[0]

            # Extract description from abstract
            abstract = award.get("abstractText", "")
            title = award.get("title", "")

            if not abstract and not title:
                logger.warning("No description in NSF response", extra={"query_id": query_id})
                return None

            # Combine title and abstract for full description
            description_parts = []
            if title:
                description_parts.append(str(title).strip())
            if abstract:
                description_parts.append(str(abstract).strip())

            description = " ".join(description_parts)

            # Extract keywords
            keywords = self._extract_keywords(award)

            return SolicitationData(
                solicitation_id=query_id,
                description=description,
                technical_keywords=keywords,
                api_source="nsf",
            )

        except (KeyError, ValueError, TypeError) as e:
            logger.warning(
                "Failed to parse NSF response, gracefully degrading",
                extra={"query_id": query_id, "error": str(e)},
            )
            return None

    def _extract_keywords(self, award: dict) -> list[str]:
        """Extract technical keywords from award data.

        Args:
            award: Parsed award object from API response

        Returns:
            List of technical keywords
        """
        keywords: list[str] = []

        # Extract program name
        program_name = award.get("fundProgramName")
        if program_name:
            keywords.append(str(program_name))

        # Extract directorate and division information
        directorate = award.get("directorate", {})
        if isinstance(directorate, dict):
            dir_name = directorate.get("name")
            if dir_name:
                keywords.append(str(dir_name))

        division = award.get("division", {})
        if isinstance(division, dict):
            div_name = division.get("name")
            if div_name:
                keywords.append(str(div_name))

        # Extract instrument type
        instrument = award.get("instrument", {})
        if isinstance(instrument, dict):
            inst_value = instrument.get("value")
            if inst_value:
                keywords.append(str(inst_value))

        # Extract program officer name as metadata
        po_name = award.get("programOfficer", {})
        if isinstance(po_name, dict):
            po_full_name = po_name.get("name")
            if po_full_name:
                keywords.append(f"PO:{po_full_name}")

        # Extract award type
        award_type = award.get("awardeeName")
        if award_type:
            keywords.append(str(award_type))

        # Deduplicate and clean
        return list(set(kw.strip() for kw in keywords if kw and str(kw).strip()))
