"""Pydantic schemas for SAM.gov API responses and enrichment data models."""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class EnrichmentType(str, Enum):
    """Types of enrichment available."""

    AWARDEE = "awardee"
    PROGRAM_OFFICE = "program_office"
    SOLICITATION = "solicitation"
    MODIFICATIONS = "modifications"


class StatusState(str, Enum):
    """Enrichment status states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# SAM.gov API Response Schemas


class OfficeAddress(BaseModel):
    """Office address information."""

    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None
    country: Optional[str] = None


class SAMOpportunityResponse(BaseModel):
    """SAM.gov opportunities API response schema."""

    model_config = ConfigDict(populate_by_name=True)

    opportunity_id: str = Field(..., alias="opportunityId")
    title: str
    description: Optional[str] = None
    posted_date: Optional[datetime] = Field(None, alias="postedDate")
    close_date: Optional[datetime] = Field(None, alias="closeDate")
    total_estimated_value: Optional[Decimal] = Field(None, alias="totalEstimatedValue")
    award_ceiling: Optional[Decimal] = Field(None, alias="awardCeiling")
    award_floor: Optional[Decimal] = Field(None, alias="awardFloor")
    organization_name: Optional[str] = Field(None, alias="organizationName")
    office_address: Optional[OfficeAddress] = Field(None, alias="officeAddress")


class SAMAwardResponse(BaseModel):
    """SAM.gov awards API response schema."""

    model_config = ConfigDict(populate_by_name=True)

    award_id: str = Field(..., alias="awardId")
    award_number: str = Field(..., alias="awardNumber")
    title: str
    award_amount: Decimal = Field(..., alias="awardAmount")
    start_date: Optional[datetime] = Field(None, alias="startDate")
    end_date: Optional[datetime] = Field(None, alias="endDate")
    recipient_name: Optional[str] = Field(None, alias="recipientName")
    recipient_uei: Optional[str] = Field(None, alias="recipientUEI")
    funding_agency: Optional[str] = Field(None, alias="fundingAgency")
    program_office: Optional[str] = Field(None, alias="programOffice")
    primary_place_of_performance: Optional[OfficeAddress] = Field(
        None, alias="primaryPlaceOfPerformance"
    )


class PhysicalAddress(BaseModel):
    """Physical address information."""

    model_config = ConfigDict(populate_by_name=True)

    address_line1: Optional[str] = Field(None, alias="addressLine1")
    address_line2: Optional[str] = Field(None, alias="addressLine2")
    city: Optional[str] = None
    state_or_province: Optional[str] = Field(None, alias="stateOrProvince")
    zip_code: Optional[str] = Field(None, alias="zipCode")
    country_code: Optional[str] = Field(None, alias="countryCode")


class SAMEntityResponse(BaseModel):
    """SAM.gov entity information API response schema."""

    entity_id: str = Field(..., alias="entityId")
    legal_business_name: str = Field(..., alias="legalBusinessName")
    uei_sam: Optional[str] = Field(None, alias="ueiSAM")
    duns: Optional[str] = None
    entity_status: Optional[str] = Field(None, alias="entityStatus")
    registration_date: Optional[datetime] = Field(None, alias="registrationDate")
    last_update_date: Optional[datetime] = Field(None, alias="lastUpdateDate")
    physical_address: Optional[PhysicalAddress] = Field(None, alias="physicalAddress")
    business_types: Optional[List[str]] = Field(default_factory=list, alias="businessTypes")

    model_config = ConfigDict(populate_by_name=True)


# Enrichment Data Models


class AwardeeProfile(BaseModel):
    """Awardee profile enrichment data."""

    uei: str = Field(..., description="Unique Entity Identifier")
    legal_name: str = Field(..., description="Legal business name")
    total_awards: int = Field(..., ge=0, description="Total number of awards received")
    total_funding: Decimal = Field(..., ge=0, description="Total funding amount received")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Success rate (0.0 to 1.0)")
    avg_award_amount: Decimal = Field(..., ge=0, description="Average award amount")
    first_award_date: datetime = Field(..., description="Date of first award")
    last_award_date: datetime = Field(..., description="Date of most recent award")
    primary_agencies: List[str] = Field(
        default_factory=list, description="Primary funding agencies"
    )
    technology_areas: List[str] = Field(
        default_factory=list, description="Primary technology areas"
    )

    @field_validator("avg_award_amount")
    @classmethod
    def validate_avg_award_amount(cls, v, info):
        """Validate that average award amount is consistent with totals."""
        if info.data and "total_awards" in info.data and "total_funding" in info.data:
            total_awards = info.data["total_awards"]
            total_funding = info.data["total_funding"]
            if total_awards > 0:
                expected_avg = total_funding / total_awards
                # Allow for small rounding differences
                if abs(v - expected_avg) > Decimal("0.01"):
                    return expected_avg
        return v


class ProgramOffice(BaseModel):
    """Program office enrichment data."""

    agency: str = Field(..., description="Agency acronym (e.g., NSF, DOD)")
    office_name: str = Field(..., description="Full office name")
    office_code: Optional[str] = Field(None, description="Office code or abbreviation")
    contact_email: Optional[str] = Field(None, description="Contact email address")
    contact_phone: Optional[str] = Field(None, description="Contact phone number")
    strategic_focus: List[str] = Field(default_factory=list, description="Strategic focus areas")
    annual_budget: Optional[Decimal] = Field(None, ge=0, description="Annual budget")
    active_programs: Optional[int] = Field(None, ge=0, description="Number of active programs")


class Solicitation(BaseModel):
    """Solicitation enrichment data."""

    solicitation_id: str = Field(..., description="Unique solicitation identifier")
    title: str = Field(..., description="Solicitation title")
    full_text: str = Field(..., description="Complete solicitation text")
    technical_requirements: List[str] = Field(
        default_factory=list, description="Technical requirements"
    )
    evaluation_criteria: List[str] = Field(default_factory=list, description="Evaluation criteria")
    topic_areas: List[str] = Field(default_factory=list, description="Topic areas covered")
    funding_range_min: Optional[Decimal] = Field(None, ge=0, description="Minimum funding amount")
    funding_range_max: Optional[Decimal] = Field(None, ge=0, description="Maximum funding amount")
    submission_deadline: Optional[datetime] = Field(None, description="Submission deadline")

    @field_validator("funding_range_max")
    @classmethod
    def validate_funding_range(cls, v, info):
        """Validate that max funding is greater than min funding."""
        if v is not None and info.data and "funding_range_min" in info.data:
            min_funding = info.data["funding_range_min"]
            if min_funding is not None and v < min_funding:
                raise ValueError("Maximum funding must be greater than minimum funding")
        return v


class AwardModification(BaseModel):
    """Award modification enrichment data."""

    modification_id: str = Field(..., description="Unique modification identifier")
    award_id: str = Field(..., description="Associated award identifier")
    modification_type: str = Field(..., description="Type of modification")
    modification_date: datetime = Field(..., description="Date of modification")
    funding_change: Optional[Decimal] = Field(
        None, description="Funding amount change (can be negative)"
    )
    scope_change: Optional[str] = Field(None, description="Description of scope changes")
    new_end_date: Optional[datetime] = Field(None, description="New award end date")
    justification: Optional[str] = Field(None, description="Justification for modification")


class EnrichmentStatus(BaseModel):
    """Enrichment status tracking."""

    award_id: str = Field(..., description="Award identifier")
    enrichment_types: List[EnrichmentType] = Field(..., description="Types of enrichment performed")
    status: StatusState = Field(..., description="Current enrichment status")
    confidence_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    data_sources: List[str] = Field(default_factory=list, description="Data sources used")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "award_id": self.award_id,
            "enrichment_types": [et.value for et in self.enrichment_types],
            "status": self.status.value,
            "confidence_score": self.confidence_score,
            "last_updated": self.last_updated.isoformat(),
            "error_message": self.error_message,
            "data_sources": self.data_sources,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnrichmentStatus":
        """Create from dictionary."""
        # Convert string values back to enums
        enrichment_types = [EnrichmentType(et) for et in data["enrichment_types"]]
        status = StatusState(data["status"])
        last_updated = datetime.fromisoformat(data["last_updated"])

        return cls(
            award_id=data["award_id"],
            enrichment_types=enrichment_types,
            status=status,
            confidence_score=data["confidence_score"],
            last_updated=last_updated,
            error_message=data.get("error_message"),
            data_sources=data.get("data_sources", []),
        )


# API Response Container Models


class OpportunityData(BaseModel):
    """Container for opportunity data from SAM.gov API."""

    model_config = ConfigDict(populate_by_name=True)

    opportunities: List[SAMOpportunityResponse] = Field(default_factory=list)
    total_records: int = Field(0, alias="totalRecords")


class AwardData(BaseModel):
    """Container for award data from SAM.gov API."""

    model_config = ConfigDict(populate_by_name=True)

    awards: List[SAMAwardResponse] = Field(default_factory=list)
    total_records: int = Field(0, alias="totalRecords")


class EntityData(BaseModel):
    """Container for entity data from SAM.gov API."""

    model_config = ConfigDict(populate_by_name=True)

    entities: List[SAMEntityResponse] = Field(default_factory=list)
    total_records: int = Field(0, alias="totalRecords")


# Validation Helper Functions


def validate_uei_format(uei: str) -> bool:
    """Validate UEI format (12 alphanumeric characters)."""
    if not uei or len(uei) != 12:
        return False
    return uei.isalnum()


def validate_duns_format(duns: str) -> bool:
    """Validate DUNS format (9 digits)."""
    if not duns or len(duns) != 9:
        return False
    return duns.isdigit()


def validate_award_number_format(award_number: str) -> bool:
    """Validate award number format (basic validation)."""
    if not award_number or len(award_number) < 5:
        return False
    return True


# Custom Validators


class StrictDecimal(Decimal):
    """Strict decimal validation for financial amounts."""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, (int, float)):
            v = str(v)
        if isinstance(v, str):
            try:
                return Decimal(v)
            except:
                raise ValueError("Invalid decimal format")
        if isinstance(v, Decimal):
            return v
        raise ValueError("Invalid decimal type")


# Configuration Models


class SAMAPIConfig(BaseModel):
    """SAM.gov API configuration."""

    base_url: str = "https://api.sam.gov"
    api_key: str
    timeout: int = 30
    max_retries: int = 3
    rate_limit: int = 100  # requests per minute

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v):
        """Validate base URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Base URL must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("rate_limit")
    @classmethod
    def validate_rate_limit(cls, v):
        """Validate rate limit is reasonable."""
        if v <= 0 or v > 1000:
            raise ValueError("Rate limit must be between 1 and 1000 requests per minute")
        return v


class EnrichmentConfig(BaseModel):
    """Enrichment configuration."""

    batch_size: int = Field(50, ge=1, le=1000)
    max_concurrent_requests: int = Field(5, ge=1, le=20)
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0)
    enable_caching: bool = True
    cache_ttl_seconds: int = Field(3600, ge=0)  # 1 hour default

    @field_validator("batch_size")
    @classmethod
    def validate_batch_size(cls, v):
        """Validate batch size is reasonable."""
        if v > 1000:
            raise ValueError("Batch size should not exceed 1000 for performance reasons")
        return v
