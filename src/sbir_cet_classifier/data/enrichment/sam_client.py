"""SAM.gov API client for award data enrichment."""

from typing import Any

import requests

from ...common.config import EnrichmentConfig
from .logging import enrichment_logger


class SAMAPIError(Exception):
    """Exception raised for SAM.gov API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class SAMClient:
    """Client for interacting with SAM.gov API."""

    def __init__(self, config: EnrichmentConfig):
        """Initialize SAM.gov API client.

        Args:
            config: Enrichment configuration with API credentials
        """
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-API-Key": config.api_key,
                "Accept": "application/json",
                "User-Agent": "SBIR-CET-Classifier/1.0",
            }
        )

    def _make_request(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make a request to SAM.gov API with retry logic.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response data

        Raises:
            SAMAPIError: If request fails after retries
        """
        url = f"{self.config.base_url}/{endpoint.lstrip('/')}"

        attempts = 0
        while True:
            try:
                response = self.session.get(url, params=params, timeout=self.config.timeout)

                if response.status_code == 404:
                    raise SAMAPIError("Award not found", status_code=404)
                elif response.status_code == 429:
                    raise SAMAPIError("Rate limit exceeded", status_code=429)

                response.raise_for_status()
                return response.json()
            except requests.HTTPError as e:
                attempts += 1
                if attempts >= self.config.max_retries:
                    enrichment_logger.logger.error(
                        f"SAM API request failed after {attempts} attempts: {e}"
                    )
                    raise SAMAPIError("Max retries exceeded")
                continue
            except requests.RequestException as e:
                attempts += 1
                if attempts >= self.config.max_retries:
                    enrichment_logger.logger.error(
                        f"SAM API request failed after {attempts} attempts: {e}"
                    )
                    raise SAMAPIError(f"Request failed: {e}")
                continue

    def get_award(self, award_id: str) -> dict[str, Any]:
        """Get detailed award information by ID.

        Args:
            award_id: SAM.gov award identifier

        Returns:
            Award details from SAM.gov

        Raises:
            SAMAPIError: If award not found or API error
        """
        return self._make_request(f"awards/{award_id}")

    def search_awards(
        self,
        award_number: str | None = None,
        recipient_name: str | None = None,
        recipient_uei: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Search for awards by criteria.

        Args:
            award_number: Specific award number to search
            recipient_name: Awardee organization name
            recipient_uei: Unique Entity Identifier
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Search results from SAM.gov
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if award_number:
            params["awardNumber"] = award_number
        if recipient_name:
            params["recipientName"] = recipient_name
        if recipient_uei:
            params["recipientUEI"] = recipient_uei

        return self._make_request("awards", params=params)

    def get_entity(self, uei_identifier: str) -> dict[str, Any]:
        """Get entity (awardee) information by UEI.

        Args:
            uei_identifier: Unique Entity Identifier

        Returns:
            Entity details from SAM.gov

        Raises:
            SAMAPIError: If entity not found or API error
        """
        params = {"ueiSAM": uei_identifier}
        return self._make_request("entities", params=params)

    def search_opportunities(
        self,
        solicitation_number: str | None = None,
        agency: str | None = None,
        naics_code: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Search for solicitation opportunities.

        Args:
            solicitation_number: Specific solicitation number
            agency: Agency code
            naics_code: NAICS industry code
            limit: Maximum number of results

        Returns:
            Opportunity search results from SAM.gov
        """
        params: dict[str, Any] = {"limit": limit}

        if solicitation_number:
            params["solicitationNumber"] = solicitation_number
        if agency:
            params["agency"] = agency
        if naics_code:
            params["naicsCode"] = naics_code

        return self._make_request("opportunities", params=params)

    def close(self):
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
