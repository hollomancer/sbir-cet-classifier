"""Awardee profile data validation."""

import re
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from dataclasses import dataclass, field

from .models import AwardeeProfile


@dataclass
class ValidationError:
    """Validation error or warning."""
    field: str
    message: str
    severity: str = "error"
    
    def __str__(self) -> str:
        return f"{self.severity.upper()}: {self.field} - {self.message}"


@dataclass
class ValidationResult:
    """Result of validation operation."""
    is_valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    
    def add_error(self, field: str, message: str) -> None:
        """Add validation error."""
        self.errors.append(ValidationError(field, message, "error"))
        self.is_valid = False
    
    def add_warning(self, field: str, message: str) -> None:
        """Add validation warning."""
        self.warnings.append(ValidationError(field, message, "warning"))
    
    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """Merge with another validation result."""
        merged = ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings
        )
        return merged


class AwardeeProfileValidator:
    """Validator for awardee profile data."""
    
    def __init__(self):
        """Initialize validator with known agency codes."""
        self.valid_agencies = {
            "NSF", "DOD", "NIH", "NASA", "DOE", "NOAA", "DHS", "USDA", 
            "DOT", "EPA", "HHS", "VA", "ARMY", "NAVY", "AF", "DARPA"
        }
        
        self.valid_tech_areas = {
            "AI", "Cybersecurity", "Robotics", "Biotech", "Materials", 
            "Energy", "Quantum", "Space", "Manufacturing", "Communications"
        }
    
    def validate_profile(self, profile: AwardeeProfile) -> ValidationResult:
        """Validate complete awardee profile."""
        result = ValidationResult()
        
        # Validate individual fields
        result = result.merge(self.validate_uei(profile.uei))
        result = result.merge(self.validate_business_name(profile.legal_name))
        result = result.merge(self.validate_funding_consistency(profile))
        result = result.merge(self.validate_date_consistency(profile))
        result = result.merge(self.validate_agency_codes(profile.primary_agencies))
        result = result.merge(self.validate_technology_areas(profile.technology_areas))
        
        # Cross-field validations
        result = result.merge(self._validate_cross_fields(profile))
        
        # Completeness checks
        result = result.merge(self._validate_completeness(profile))
        
        return result
    
    def validate_uei(self, uei: str) -> ValidationResult:
        """Validate UEI format."""
        result = ValidationResult()
        
        if not uei:
            result.add_error("uei", "UEI is required")
            return result
        
        if len(uei) != 12:
            result.add_error("uei", "UEI must be 12 characters long")
        
        if not uei.isalnum():
            result.add_error("uei", "UEI must contain only alphanumeric characters")
        
        return result
    
    def validate_business_name(self, name: str) -> ValidationResult:
        """Validate business name format."""
        result = ValidationResult()
        
        if not name:
            result.add_error("legal_name", "Business name is required")
            return result
        
        if len(name) < 2:
            result.add_error("legal_name", "Business name is too short")
        
        if len(name) > 150:
            result.add_error("legal_name", "Business name is too long")
        
        # Check for suspicious patterns
        if name.lower() in ["test", "example", "sample"]:
            result.add_warning("legal_name", "Business name appears to be a placeholder")
        
        return result
    
    def validate_funding_consistency(self, profile: AwardeeProfile) -> ValidationResult:
        """Validate funding amount consistency."""
        result = ValidationResult()
        
        if profile.total_awards > 0:
            expected_avg = profile.total_funding / profile.total_awards
            actual_avg = profile.avg_award_amount
            
            # Allow for small rounding differences
            if abs(expected_avg - actual_avg) > Decimal("1.00"):
                result.add_warning(
                    "avg_award_amount", 
                    f"Average award amount ({actual_avg}) doesn't match calculated average ({expected_avg})"
                )
        
        # Check for unrealistic values
        if profile.total_funding > Decimal("1000000000"):  # $1B
            result.add_warning("total_funding", "Total funding amount is unusually high")
        
        if profile.avg_award_amount > Decimal("50000000"):  # $50M
            result.add_warning("avg_award_amount", "Average award amount is unusually high")
        
        return result
    
    def validate_date_consistency(self, profile: AwardeeProfile) -> ValidationResult:
        """Validate date consistency."""
        result = ValidationResult()
        
        if profile.first_award_date > profile.last_award_date:
            result.add_error(
                "first_award_date", 
                "First award date cannot be after last award date"
            )
        
        # Check for future dates
        now = datetime.now()
        if profile.first_award_date > now:
            result.add_warning("first_award_date", "First award date is in the future")
        
        if profile.last_award_date > now:
            result.add_warning("last_award_date", "Last award date is in the future")
        
        # Check for very old dates
        if profile.first_award_date.year < 1980:
            result.add_warning("first_award_date", "First award date is unusually old")
        
        return result
    
    def validate_agency_codes(self, agencies: List[str]) -> ValidationResult:
        """Validate agency codes."""
        result = ValidationResult()
        
        for agency in agencies:
            if agency not in self.valid_agencies:
                result.add_warning("primary_agencies", f"Unknown agency code: {agency}")
        
        return result
    
    def validate_technology_areas(self, tech_areas: List[str]) -> ValidationResult:
        """Validate technology areas."""
        result = ValidationResult()
        
        if len(tech_areas) > 15:
            result.add_error("technology_areas", "Too many technology areas (maximum 15)")
        
        for area in tech_areas:
            if area not in self.valid_tech_areas:
                result.add_warning("technology_areas", f"Unknown technology area: {area}")
        
        return result
    
    def _validate_cross_fields(self, profile: AwardeeProfile) -> ValidationResult:
        """Validate cross-field relationships."""
        result = ValidationResult()
        
        # High success rate with very low funding might indicate data issues
        if profile.success_rate > 0.9 and profile.avg_award_amount < Decimal("10000"):
            result.add_warning(
                "success_rate", 
                "High success rate with very low average funding is unusual"
            )
        
        # Many awards with very high success rate might be suspicious
        if profile.total_awards > 50 and profile.success_rate > 0.95:
            result.add_warning(
                "success_rate", 
                "Very high success rate with many awards is unusual"
            )
        
        # Check for single-agency concentration
        if len(profile.primary_agencies) == 1 and profile.total_awards > 10:
            result.add_warning(
                "primary_agencies", 
                "High concentration with single agency might indicate limited diversification"
            )
        
        return result
    
    def _validate_completeness(self, profile: AwardeeProfile) -> ValidationResult:
        """Validate profile completeness."""
        result = ValidationResult()
        
        if not profile.primary_agencies:
            result.add_warning("primary_agencies", "No primary agencies specified")
        
        if not profile.technology_areas:
            result.add_warning("technology_areas", "No technology areas specified")
        
        if profile.total_awards == 0:
            result.add_warning("total_awards", "No awards recorded for this awardee")
        
        return result
