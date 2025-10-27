"""Solicitation text retrieval service."""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal

from .models import Solicitation
from .text_processing import TechnicalKeywordExtractor
from sbir_cet_classifier.models.cet_relevance_scorer import CETRelevanceScorer


class SolicitationService:
    """Service for retrieving and processing solicitation data."""

    def __init__(self, sam_client):
        """Initialize with SAM.gov API client."""
        self.sam_client = sam_client
        self._cache = {}
        self.keyword_extractor = TechnicalKeywordExtractor()
        self.cet_scorer = CETRelevanceScorer()

    async def get_solicitation_by_number(self, solicitation_number: str) -> Optional[Solicitation]:
        """Retrieve solicitation by number."""
        # Check cache first
        if solicitation_number in self._cache:
            return self._cache[solicitation_number]

        try:
            response = await self.sam_client.get_solicitation_by_number(solicitation_number)
            if not response:
                return None

            solicitation = self._parse_solicitation_response(response)

            # Cache the result
            self._cache[solicitation_number] = solicitation

            return solicitation

        except Exception as e:
            raise Exception(f"Failed to retrieve solicitation {solicitation_number}: {str(e)}")

    async def search_solicitations_by_agency(self, agency_code: str) -> List[Solicitation]:
        """Search solicitations by agency code."""
        try:
            response = await self.sam_client.search_solicitations(agency_code=agency_code)
            if not response:
                return []

            solicitations = []
            for item in response:
                solicitation = self._parse_solicitation_response(item)
                solicitations.append(solicitation)

            return solicitations

        except Exception as e:
            raise Exception(f"Failed to search solicitations for agency {agency_code}: {str(e)}")

    async def extract_technical_keywords(self, solicitation_text: str) -> List[str]:
        """Extract technical keywords from solicitation text."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.keyword_extractor.extract_cet_keywords, solicitation_text
        )

    async def calculate_cet_relevance_scores(self, solicitation_text: str) -> Dict[str, float]:
        """Calculate CET relevance scores for solicitation text."""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.cet_scorer.calculate_relevance_scores, solicitation_text
        )

    def _parse_solicitation_response(self, response: Dict[str, Any]) -> Solicitation:
        """Parse SAM.gov API response into Solicitation model."""
        # Extract and process technical keywords
        full_text = response.get("full_text", "")
        keywords = self.keyword_extractor.extract_cet_keywords(full_text)

        # Calculate CET relevance scores
        cet_scores = self.cet_scorer.calculate_relevance_scores(full_text)

        return Solicitation(
            solicitation_id=response.get("solicitation_id", ""),
            solicitation_number=response.get("solicitation_number", ""),
            title=response.get("title", ""),
            agency_code=response.get("agency_code", ""),
            program_office_id=response.get("program_office_id", ""),
            solicitation_type=response.get("solicitation_type", ""),
            topic_number=response.get("topic_number"),
            full_text=full_text,
            technical_requirements=response.get("technical_requirements", ""),
            evaluation_criteria=response.get("evaluation_criteria", ""),
            funding_range_min=Decimal(str(response.get("funding_range_min", "0"))),
            funding_range_max=Decimal(str(response.get("funding_range_max", "0"))),
            proposal_deadline=self._parse_date(response.get("proposal_deadline")),
            award_start_date=self._parse_date(response.get("award_start_date")),
            performance_period=int(response.get("performance_period", 12)),
            keywords=keywords,
            cet_relevance_scores=cet_scores,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None

        try:
            # Try different date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue

            # If no format matches, return None
            return None

        except Exception:
            return None
