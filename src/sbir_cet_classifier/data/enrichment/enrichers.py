"""Base enrichment service interface and implementations."""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional

from .sam_client import SAMClient, SAMAPIError
from .logging import enrichment_logger


class EnrichmentType(Enum):
    """Types of enrichment available."""
    AWARDEE = "awardee"
    PROGRAM_OFFICE = "program_office"
    SOLICITATION = "solicitation"
    MODIFICATIONS = "modifications"


class EnrichmentError(Exception):
    """Exception raised during enrichment operations."""
    
    def __init__(self, message: str, award_id: Optional[str] = None, 
                 enrichment_type: Optional[EnrichmentType] = None,
                 context: Optional[Dict[str, Any]] = None):
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
    data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class EnrichmentService:
    """Base service for enriching award data with SAM.gov information."""
    
    def __init__(self, sam_client: SAMClient):
        """Initialize enrichment service.
        
        Args:
            sam_client: SAM.gov API client
        """
        self.sam_client = sam_client
    
    def enrich_award(self, award_id: str, 
                    enrichment_types: List[EnrichmentType]) -> EnrichmentResult:
        """Enrich a single award with specified enrichment types.
        
        Args:
            award_id: Award identifier to enrich
            enrichment_types: Types of enrichment to perform
            
        Returns:
            Enrichment result with success status and data
        """
        start_time = time.time()
        
        try:
            # Get base award data from SAM.gov
            award_data = self.sam_client.get_award(award_id)
            
            # Perform requested enrichments
            enriched_data = {}
            overall_confidence = 0.0
            
            for enrichment_type in enrichment_types:
                if enrichment_type == EnrichmentType.AWARDEE:
                    awardee_data = self._enrich_awardee(award_data)
                    enriched_data["awardee"] = awardee_data
                    overall_confidence = max(overall_confidence, 
                                           self.calculate_confidence(awardee_data))
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return EnrichmentResult(
                award_id=award_id,
                enrichment_type=enrichment_types[0],  # Primary type
                success=True,
                confidence=overall_confidence,
                data=enriched_data,
                processing_time_ms=processing_time
            )
            
        except SAMAPIError as e:
            processing_time = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            if e.status_code == 404:
                error_msg = f"Award {award_id} not found in SAM.gov"
            
            enrichment_logger.logger.error(f"Enrichment failed for {award_id}: {error_msg}")
            
            return EnrichmentResult(
                award_id=award_id,
                enrichment_type=enrichment_types[0],
                success=False,
                confidence=0.0,
                error_message=error_msg,
                processing_time_ms=processing_time
            )
    
    def enrich_awards(self, award_ids: List[str], 
                     enrichment_types: List[EnrichmentType]) -> List[EnrichmentResult]:
        """Enrich multiple awards.
        
        Args:
            award_ids: List of award identifiers
            enrichment_types: Types of enrichment to perform
            
        Returns:
            List of enrichment results
        """
        results = []
        
        for award_id in award_ids:
            result = self.enrich_award(award_id, enrichment_types)
            results.append(result)
        
        return results
    
    def _enrich_awardee(self, award_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich award with awardee information.
        
        Args:
            award_data: Base award data from SAM.gov
            
        Returns:
            Enriched awardee data
        """
        awardee_data = {
            "recipient_name": award_data.get("recipientName"),
            "recipient_uei": award_data.get("recipientUEI"),
            "award_amount": award_data.get("awardAmount")
        }
        
        # Try to get additional entity information if UEI available
        if award_data.get("recipientUEI"):
            try:
                entity_data = self.sam_client.get_entity(award_data["recipientUEI"])
                awardee_data.update({
                    "entity_name": entity_data.get("entityName"),
                    "award_history": entity_data.get("awardHistory", {}),
                    "business_types": entity_data.get("businessTypes", [])
                })
            except SAMAPIError:
                # Entity data not available, continue with basic info
                pass
        
        return awardee_data
    
    def calculate_confidence(self, enrichment_data: Dict[str, Any]) -> float:
        """Calculate confidence score for enrichment data.
        
        Args:
            enrichment_data: Enriched data to score
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        confidence = 0.0
        
        # Base confidence on data completeness and quality
        if enrichment_data.get("recipient_uei"):
            confidence += 0.4  # UEI is strong identifier
        
        if enrichment_data.get("recipient_name"):
            confidence += 0.3  # Name provides good context
        
        if enrichment_data.get("award_amount") and enrichment_data["award_amount"] > 0:
            confidence += 0.2  # Valid amount adds confidence
        
        if enrichment_data.get("award_history"):
            confidence += 0.1  # Historical data adds value
        
        return min(confidence, 1.0)
    
    def validate_enrichment_data(self, data: Dict[str, Any]) -> bool:
        """Validate enrichment data quality.
        
        Args:
            data: Enrichment data to validate
            
        Returns:
            True if data is valid, False otherwise
        """
        # Check for required fields
        if not data.get("recipient_name") or data["recipient_name"].strip() == "":
            return False
        
        # Check for valid award amount
        if "award_amount" in data and data["award_amount"] < 0:
            return False
        
        return True
