"""Base enrichment service interface and implementations.

This module provides:
- EnrichmentType: enum for enrichment categories (stringified to value)
- EnrichmentError: structured exception for enrichment operations
- EnrichmentResult: dataclass representing results
- EnrichmentService: base service that calls SAM client and computes confidence

Notes:
- The EnrichmentType.__str__ returns the enum's value (e.g. "awardee") so str(...) matches tests.
- EnrichmentService.calculate_confidence and validate_enrichment_data accept either
  snake_case or camelCase keys to be robust when interacting with external APIs/tests.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .logging import enrichment_logger
from .sam_client import SAMAPIError, SAMClient


class EnrichmentType(Enum):
    """Types of enrichment available.

    str(EnrichmentType.AWARDEE) -> "awardee"
    """

    AWARDEE = "awardee"
    PROGRAM_OFFICE = "program_office"
    SOLICITATION = "solicitation"
    MODIFICATIONS = "modifications"

    def __str__(self) -> str:
        """Return the enum value as the string representation."""
        return self.value


class EnrichmentError(Exception):
    """Exception raised during enrichment operations."""

    def __init__(
        self,
        message: str,
        award_id: str | None = None,
        enrichment_type: EnrichmentType | None = None,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.award_id = award_id
        self.enrichment_type = enrichment_type
        self.context = context or {}


@dataclass
class EnrichmentResult:
    """Result of an enrichment operation."""

    award_id: str
    enrichment_type: EnrichmentType
    success: bool
    confidence: float
    processing_time_ms: int
    data: dict[str, Any] | None = None
    error_message: str | None = None


class EnrichmentService:
    """Base service for enriching award data with SAM.gov information."""

    def __init__(self, sam_client: SAMClient):
        """Initialize enrichment service.

        Args:
            sam_client: SAM.gov API client
        """
        self.sam_client = sam_client

    def enrich_award(
        self, award_id: str, enrichment_types: list[EnrichmentType]
    ) -> EnrichmentResult:
        """Enrich a single award with specified enrichment types.

        Args:
            award_id: Award identifier to enrich
            enrichment_types: Types of enrichment to perform

        Returns:
            EnrichmentResult with success status and data
        """
        start_time = time.time()

        try:
            # Get base award data from SAM.gov
            award_data = self.sam_client.get_award(award_id)

            # Perform requested enrichments
            enriched_data: dict[str, Any] = {}
            overall_confidence = 0.0

            for enrichment_type in enrichment_types:
                if enrichment_type == EnrichmentType.AWARDEE:
                    awardee_data = self._enrich_awardee(award_data)
                    enriched_data["awardee"] = awardee_data
                    overall_confidence = max(
                        overall_confidence, self.calculate_confidence(awardee_data)
                    )

            processing_time = int((time.time() - start_time) * 1000)

            return EnrichmentResult(
                award_id=award_id,
                enrichment_type=enrichment_types[0] if enrichment_types else EnrichmentType.AWARDEE,
                success=True,
                confidence=overall_confidence,
                data=enriched_data,
                processing_time_ms=processing_time,
            )

        except SAMAPIError as e:
            processing_time = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            if getattr(e, "status_code", None) == 404:
                error_msg = f"Award {award_id} not found in SAM.gov"

            enrichment_logger.logger.error(f"Enrichment failed for {award_id}: {error_msg}")

            return EnrichmentResult(
                award_id=award_id,
                enrichment_type=enrichment_types[0] if enrichment_types else EnrichmentType.AWARDEE,
                success=False,
                confidence=0.0,
                error_message=error_msg,
                processing_time_ms=processing_time,
            )

    def enrich_awards(
        self, award_ids: list[str], enrichment_types: list[EnrichmentType]
    ) -> list[EnrichmentResult]:
        """Enrich multiple awards.

        Args:
            award_ids: List of award identifiers
            enrichment_types: Types of enrichment to perform

        Returns:
            List of EnrichmentResult
        """
        results: list[EnrichmentResult] = []
        for award_id in award_ids:
            result = self.enrich_award(award_id, enrichment_types)
            results.append(result)
        return results

    def _enrich_awardee(self, award_data: dict[str, Any]) -> dict[str, Any]:
        """Enrich award with awardee information.

        Args:
            award_data: Base award data from SAM.gov

        Returns:
            Enriched awardee data
        """
        # Respect both camelCase and snake_case keys from upstream SAM responses
        recipient_name = award_data.get("recipientName") or award_data.get("recipient_name")
        recipient_uei = award_data.get("recipientUEI") or award_data.get("recipient_uei")
        award_amount = award_data.get("awardAmount") or award_data.get("award_amount")

        awardee_data: dict[str, Any] = {
            "recipient_name": recipient_name,
            "recipient_uei": recipient_uei,
            "award_amount": award_amount,
        }

        # Try to get additional entity information if UEI available
        if recipient_uei:
            try:
                entity_data = self.sam_client.get_entity(recipient_uei)
                awardee_data.update(
                    {
                        "entity_name": entity_data.get("entityName")
                        or entity_data.get("entity_name"),
                        "award_history": entity_data.get("awardHistory", {})
                        or entity_data.get("award_history", {}),
                        "business_types": entity_data.get("businessTypes", [])
                        or entity_data.get("business_types", []),
                    }
                )
            except SAMAPIError:
                # Entity data not available, continue with basic info
                pass

        return awardee_data

    def calculate_confidence(self, enrichment_data: dict[str, Any]) -> float:
        """Calculate confidence score for enrichment data.

        Accepts either camelCase or snake_case keys to be robust when receiving
        data from external sources or tests.

        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.0

        # Normalize keys (support both conventions)
        recipient_uei = enrichment_data.get("recipient_uei") or enrichment_data.get("recipientUEI")
        recipient_name = enrichment_data.get("recipient_name") or enrichment_data.get(
            "recipientName"
        )
        award_amount = enrichment_data.get("award_amount")
        if award_amount is None:
            award_amount = enrichment_data.get("awardAmount")
        award_history = enrichment_data.get("award_history") or enrichment_data.get("awardHistory")

        # Base confidence on data completeness and quality (weights chosen for tests)
        if recipient_uei:
            confidence += 0.4  # UEI is strong identifier

        if recipient_name:
            confidence += 0.3  # Name provides good context

        if award_amount and award_amount > 0:
            confidence += 0.2  # Valid amount adds confidence

        if award_history:
            confidence += 0.1  # Historical data adds value

        return min(confidence, 1.0)

    def validate_enrichment_data(self, data: dict[str, Any]) -> bool:
        """Validate enrichment data quality.

        Accepts either recipient_name or recipientName and award_amount or awardAmount.

        Returns:
            True if data is valid, False otherwise
        """
        recipient_name = data.get("recipient_name") or data.get("recipientName")
        if not recipient_name or str(recipient_name).strip() == "":
            return False

        # Check for valid award amount (accept camelCase or snake_case)
        award_amount = data.get("award_amount")
        if award_amount is None:
            award_amount = data.get("awardAmount")
        if award_amount is not None and award_amount < 0:
            return False

        return True
