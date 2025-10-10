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
        project_number: str | None = None,
    ) -> SolicitationData | None:
        """Look up solicitation metadata by FOA, solicitation ID, or project number.

        Args:
            funding_opportunity: NIH FOA number (e.g., "PA-23-123", "RFA-CA-23-001")
            solicitation_id: Alternative solicitation identifier
            project_number: NIH project number (e.g., "4R44DE031461-02")

        Returns:
            SolicitationData if found, None if not found or on timeout

        Raises:
            NIHAPIError: For API errors other than 404/timeout
            ValueError: If no identifier provided

        Example:
            >>> client = NIHClient()
            >>> result = client.lookup_solicitation(project_number="4R44DE031461-02")
            >>> if result:
            ...     print(result.description)
            >>> result = client.lookup_solicitation(funding_opportunity="PA-23-123")
            >>> if result:
            ...     print(result.description)
        """
        if not funding_opportunity and not solicitation_id and not project_number:
            raise ValueError("Must provide funding_opportunity, solicitation_id, or project_number")

        query_id = funding_opportunity or solicitation_id or project_number
        search_type = "project" if project_number else "foa"
        assert query_id is not None  # For type checker

        logger.debug(
            "Looking up NIH solicitation",
            extra={
                "funding_opportunity": funding_opportunity,
                "solicitation_id": solicitation_id,
                "project_number": project_number,
                "search_type": search_type,
            },
        )

        try:
            response = self._make_request(query_id, search_type)

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

    def _make_request(self, query_id: str, search_type: str = "foa") -> httpx.Response:
        """Make HTTP request to NIH Reporter API.

        Args:
            query_id: Funding opportunity, solicitation, or project identifier
            search_type: "foa" for funding opportunity or "project" for project number

        Returns:
            HTTP response object

        Raises:
            httpx.HTTPError: For network/HTTP errors
        """
        endpoint = f"{self.base_url}/projects/search"

        # Build search criteria based on type
        if search_type == "project":
            criteria = {"project_nums": [query_id]}
        else:
            criteria = {"foa": [query_id]}

        payload = {
            "criteria": criteria,
            "include_fields": [
                "AbstractText",
                "ProjectTitle",
                "Terms",
                "ProjectNum",
                "PhrText",  # Public health relevance
                "PrefTerms",  # Preferred terms (comprehensive)
                "SpendingCategoriesDesc",  # Research categories
            ],
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

            # Extract description - combine abstract, PHR text, and spending categories
            abstract = project.get("abstract_text", "")
            title = project.get("project_title", "")
            phr_text = project.get("phr_text", "")
            spending_cats = project.get("spending_categories_desc", "")
            
            # Build comprehensive description
            description_parts = []
            if abstract:
                description_parts.append(abstract)
            elif title:
                description_parts.append(title)
            
            if phr_text:
                description_parts.append(phr_text)
            
            if spending_cats:
                description_parts.append(f"Research Categories: {spending_cats}")
            
            description = " ".join(description_parts)
            
            if not description:
                logger.warning("No description in NIH response", extra={"query_id": query_id})
                return None

            # Extract keywords from multiple sources
            keywords = []
            
            # 1. MeSH terms (original source)
            terms = project.get("terms", "")
            if terms:
                # Terms are angle-bracket delimited
                mesh_terms = [term.strip() for term in terms.replace("><", "|").strip("<>").split("|") if term.strip()]
                keywords.extend(mesh_terms[:10])
            
            # 2. Preferred terms (comprehensive, curated)
            pref_terms = project.get("pref_terms", "")
            if pref_terms:
                # Preferred terms are semicolon-delimited
                pref_list = [term.strip() for term in pref_terms.split(";") if term.strip()]
                # Add top 20 preferred terms (avoiding duplicates)
                for term in pref_list[:20]:
                    if term not in keywords:
                        keywords.append(term)
            
            # Limit total keywords to 30 for performance
            keywords = keywords[:30]

            return SolicitationData(
                solicitation_id=project.get("project_num", query_id),
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
