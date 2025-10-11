"""Program office data retrieval service."""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal

from .models import ProgramOffice


class ProgramOfficeService:
    """Service for retrieving and processing program office data."""
    
    def __init__(self, sam_client):
        """Initialize with SAM.gov API client."""
        self.sam_client = sam_client
        self._cache = {}
    
    async def get_program_office_by_agency(self, agency_code: str) -> List[ProgramOffice]:
        """Retrieve program offices for an agency."""
        if agency_code in self._cache:
            return self._cache[agency_code]
        
        try:
            response = await self.sam_client.get_program_offices(agency_code=agency_code)
            if not response:
                return []
            
            offices = []
            for office_data in response:
                office = self._parse_program_office_response(office_data)
                offices.append(office)
            
            self._cache[agency_code] = offices
            return offices
            
        except Exception as e:
            raise Exception(f"Failed to retrieve program offices for {agency_code}: {str(e)}")
    
    async def get_program_office_by_id(self, office_id: str) -> Optional[ProgramOffice]:
        """Retrieve specific program office by ID."""
        try:
            response = await self.sam_client.get_program_office_details(office_id)
            if not response:
                return None
            
            return self._parse_program_office_response(response)
            
        except Exception as e:
            raise Exception(f"Failed to retrieve program office {office_id}: {str(e)}")
    
    async def discover_related_opportunities(self, office_id: str) -> List[Dict[str, Any]]:
        """Discover related opportunities for a program office."""
        try:
            response = await self.sam_client.get_opportunities_by_office(office_id)
            return response.get("opportunities", [])
            
        except Exception as e:
            raise Exception(f"Failed to discover opportunities for {office_id}: {str(e)}")
    
    def _parse_program_office_response(self, response: Dict[str, Any]) -> ProgramOffice:
        """Parse SAM.gov API response into ProgramOffice model."""
        return ProgramOffice(
            office_id=response.get("office_id", ""),
            agency_code=response.get("agency_code", ""),
            agency_name=response.get("agency_name", ""),
            office_name=response.get("office_name", ""),
            office_description=response.get("description", ""),
            contact_email=response.get("contact_email"),
            contact_phone=response.get("contact_phone"),
            website_url=response.get("website_url"),
            strategic_focus_areas=response.get("focus_areas", []),
            annual_budget=Decimal(str(response.get("annual_budget", 0))) if response.get("annual_budget") else None,
            active_solicitations_count=int(response.get("active_solicitations", 0)),
            total_awards_managed=int(response.get("total_awards", 0)),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
