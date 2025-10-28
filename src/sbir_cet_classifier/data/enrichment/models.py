"""Enrichment data models and entities."""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class Solicitation(BaseModel):
    """Solicitation entity model for SAM.gov solicitation data."""

    solicitation_id: str = Field(..., description="Unique solicitation identifier")
    solicitation_number: str = Field(..., description="Official solicitation number")
    title: str = Field(..., description="Solicitation title")
    agency_code: str = Field(..., description="Issuing agency code")
    program_office_id: str = Field(..., description="Program office identifier")
    solicitation_type: str = Field(..., description="Type (SBIR Phase I/II, STTR, etc.)")
    topic_number: Optional[str] = Field(None, description="Specific topic number")
    full_text: str = Field(..., description="Complete solicitation text")
    technical_requirements: str = Field(..., description="Extracted technical requirements")
    evaluation_criteria: str = Field(..., description="Award evaluation criteria")
    funding_range_min: Decimal = Field(..., ge=0, description="Minimum funding amount")
    funding_range_max: Decimal = Field(..., ge=0, description="Maximum funding amount")
    proposal_deadline: date = Field(..., description="Proposal submission deadline")
    award_start_date: Optional[date] = Field(None, description="Expected award start date")
    performance_period: int = Field(..., gt=0, description="Performance period in months")
    keywords: List[str] = Field(default_factory=list, description="Extracted technical keywords")
    cet_relevance_scores: Dict[str, float] = Field(
        default_factory=dict, description="Pre-computed CET category relevance"
    )
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_validator("funding_range_max")
    @classmethod
    def validate_funding_range(cls, v, info):
        """Validate that funding_range_max >= funding_range_min."""
        if info.data and "funding_range_min" in info.data and v < info.data["funding_range_min"]:
            raise ValueError("funding_range_min must be <= funding_range_max")
        return v

    @field_validator("performance_period")
    @classmethod
    def validate_performance_period(cls, v):
        """Validate that performance period is positive."""
        if v <= 0:
            raise ValueError("performance_period must be positive")
        return v

    @field_validator("cet_relevance_scores")
    @classmethod
    def validate_cet_scores(cls, v):
        """Validate that CET relevance scores are between 0 and 1."""
        for category, score in v.items():
            if not isinstance(score, (int, float)) or not (0.0 <= score <= 1.0):
                raise ValueError(f"CET relevance score for {category} must be between 0.0 and 1.0")
        return v


class ProgramOffice(BaseModel):
    """Program office entity model for agency program information."""

    office_id: str = Field(..., description="Unique program office identifier")
    agency_code: str = Field(..., description="Parent agency code")
    agency_name: str = Field(..., description="Full agency name")
    office_name: str = Field(..., description="Program office name")
    office_description: str = Field(..., description="Office mission and focus areas")
    contact_email: Optional[str] = Field(None, description="Primary contact email")
    contact_phone: Optional[str] = Field(None, description="Primary contact phone")
    website_url: Optional[str] = Field(None, description="Office website URL")
    strategic_focus_areas: List[str] = Field(
        default_factory=list, description="Key technology/research areas"
    )
    annual_budget: Optional[Decimal] = Field(None, ge=0, description="Annual program budget")
    active_solicitations_count: int = Field(..., ge=0, description="Number of active solicitations")
    total_awards_managed: int = Field(..., ge=0, description="Total awards under management")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @field_validator("contact_email")
    @classmethod
    def validate_email_format(cls, v):
        """Validate email format if provided."""
        if v is not None:
            import re

            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_pattern, v):
                raise ValueError("value is not a valid email address")
        return v

    @field_validator("website_url")
    @classmethod
    def validate_url_format(cls, v):
        """Validate URL format if provided."""
        if v is not None:
            import re

            url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
            if not re.match(url_pattern, v):
                raise ValueError("value is not a valid URL")
        return v


class AwardModification(BaseModel):
    """Award modification entity model for tracking award changes."""

    modification_id: str = Field(..., description="Unique modification identifier")
    award_id: str = Field(..., description="Parent award identifier")
    modification_number: str = Field(..., description="Sequential modification number")
    modification_type: str = Field(..., description="Type (funding change, scope, timeline, etc.)")
    modification_date: date = Field(..., description="Date modification was executed")
    description: str = Field(..., description="Modification description")
    funding_change: Optional[Decimal] = Field(None, description="Change in funding amount")
    new_end_date: Optional[date] = Field(None, description="Updated award end date")
    scope_changes: Optional[str] = Field(None, description="Description of scope changes")
    justification: str = Field(..., description="Modification justification")
    approving_official: str = Field(..., description="Name of approving official")
    created_at: datetime = Field(..., description="Record creation timestamp")

    @field_validator("modification_date")
    @classmethod
    def validate_modification_date(cls, v):
        """Validate modification date is not in future."""
        if v > date.today():
            raise ValueError("Modification date cannot be in the future")
        return v


class AwardeeProfile(BaseModel):
    """Awardee profile enrichment data model."""

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


class AwardeeMatchResult(BaseModel):
    """Result of awardee matching operation."""

    award_id: str = Field(..., description="Award identifier")
    matched_uei: Optional[str] = Field(None, description="Matched UEI if found")
    confidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Match confidence (0.0 to 1.0)"
    )
    match_method: str = Field(..., description="Method used for matching")
    match_details: Dict[str, Any] = Field(
        default_factory=dict, description="Detailed match information"
    )

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, v):
        """Validate confidence score bounds."""
        if v < 0.0 or v > 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        return v


class AwardeeMetrics(BaseModel):
    """Awardee performance metrics."""

    uei: str = Field(..., description="Unique Entity Identifier")
    total_awards: int = Field(..., ge=0, description="Total number of awards")
    total_funding: Decimal = Field(..., ge=0, description="Total funding received")
    success_rate: float = Field(..., ge=0.0, le=1.0, description="Success rate")
    avg_award_amount: Decimal = Field(..., ge=0, description="Average award amount")
    first_award_date: datetime = Field(..., description="First award date")
    last_award_date: datetime = Field(..., description="Last award date")
    primary_agencies: List[str] = Field(default_factory=list, description="Primary agencies")
    technology_areas: List[str] = Field(default_factory=list, description="Technology areas")
    award_size_distribution: Optional[Dict[str, int]] = Field(
        None, description="Award size distribution"
    )

    def calculate_years_active(self) -> int:
        """Calculate years active based on first and last award dates."""
        if self.first_award_date and self.last_award_date:
            return self.last_award_date.year - self.first_award_date.year
        return 0


class AwardeeEnrichmentService:
    """Service for enriching awardee data."""

    def __init__(self, sam_client):
        """Initialize with SAM.gov API client."""
        self.sam_client = sam_client

    def find_awardee_by_uei(self, uei: str) -> Optional[Dict[str, Any]]:
        """Find awardee by UEI."""
        try:
            return self.sam_client.get_entity_by_uei(uei)
        except Exception:
            return None

    def find_awardee_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Find awardee by name with fuzzy matching."""
        try:
            response = self.sam_client.search_entities(legal_business_name=name)
            return response.get("entities", [])
        except Exception:
            return []

    def match_award_to_awardee(self, award_data: Dict[str, Any]) -> Optional[AwardeeMatchResult]:
        """Match award to awardee with confidence scoring."""
        award_id = award_data.get("award_id")
        awardee_uei = award_data.get("awardee_uei")
        awardee_name = award_data.get("awardee_name")

        # Try UEI match first
        if awardee_uei:
            entity = self.find_awardee_by_uei(awardee_uei)
            if entity:
                return AwardeeMatchResult(
                    award_id=award_id,
                    matched_uei=awardee_uei,
                    confidence_score=0.95,
                    match_method="exact_uei",
                    match_details={"uei_match": True},
                )

        # Fallback to name matching
        if awardee_name:
            entities = self.find_awardee_by_name(awardee_name)
            if entities:
                best_match = entities[0]  # Take first result for now
                confidence = self._calculate_name_similarity(
                    awardee_name, best_match.get("legalBusinessName", "")
                )

                if confidence > 0.7:
                    return AwardeeMatchResult(
                        award_id=award_id,
                        matched_uei=best_match.get("ueiSAM"),
                        confidence_score=confidence,
                        match_method="fuzzy_name",
                        match_details={"name_similarity": confidence},
                    )

        return None

    def enrich_awardee_profile(self, uei: str) -> Optional[AwardeeProfile]:
        """Enrich awardee profile with historical data."""
        # Get entity information
        entity = self.find_awardee_by_uei(uei)
        if not entity:
            return None

        # Get awards history
        try:
            awards_response = self.sam_client.get_awards_by_uei(uei)
            awards = awards_response.get("awards", [])
        except Exception:
            awards = []

        if not awards:
            return None

        # Calculate metrics
        total_awards = len(awards)
        total_funding = sum(Decimal(str(award.get("awardAmount", 0))) for award in awards)
        avg_award_amount = total_funding / total_awards if total_awards > 0 else Decimal("0")

        # Calculate success rate (completed + active awards)
        successful_statuses = ["Completed", "Active"]
        successful_awards = [a for a in awards if a.get("awardStatus") in successful_statuses]
        success_rate = len(successful_awards) / total_awards if total_awards > 0 else 0.0

        # Extract dates
        award_dates = []
        for award in awards:
            start_date_str = award.get("startDate")
            if start_date_str:
                try:
                    award_dates.append(
                        datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
                    )
                except:
                    pass

        first_award_date = min(award_dates) if award_dates else datetime.now()
        last_award_date = max(award_dates) if award_dates else datetime.now()

        # Extract agencies and technology areas
        primary_agencies = list(
            set(award.get("fundingAgency") for award in awards if award.get("fundingAgency"))
        )
        technology_areas = self._extract_technology_areas(awards)

        return AwardeeProfile(
            uei=uei,
            legal_name=entity.get("legalBusinessName", ""),
            total_awards=total_awards,
            total_funding=total_funding,
            success_rate=success_rate,
            avg_award_amount=avg_award_amount,
            first_award_date=first_award_date,
            last_award_date=last_award_date,
            primary_agencies=primary_agencies,
            technology_areas=technology_areas,
        )

    def calculate_confidence_score(self, match_data: Dict[str, Any]) -> float:
        """Calculate confidence score based on match data."""
        score = 0.0

        # UEI match is highest confidence
        if match_data.get("uei_match"):
            score += 0.5

        # Name similarity
        name_sim = match_data.get("name_similarity", 0.0)
        score += name_sim * 0.3

        # Award number match
        if match_data.get("award_number_match"):
            score += 0.2

        return min(score, 1.0)

    def batch_enrich_awards(self, awards: List[Dict[str, Any]]) -> List[AwardeeMatchResult]:
        """Batch enrich multiple awards."""
        results = []
        for award in awards:
            result = self.match_award_to_awardee(award)
            if result:
                results.append(result)
        return results

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        # Simple implementation - could use more sophisticated algorithms
        name1_clean = self._normalize_name(name1)
        name2_clean = self._normalize_name(name2)

        if name1_clean == name2_clean:
            return 1.0

        # Simple character-based similarity
        common_chars = set(name1_clean) & set(name2_clean)
        total_chars = set(name1_clean) | set(name2_clean)

        if not total_chars:
            return 0.0

        return len(common_chars) / len(total_chars)

    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison."""
        if not name:
            return ""

        # Convert to lowercase and remove common suffixes
        name = name.lower()
        suffixes = [" inc", " llc", " corp", " co", " ltd", " incorporated", ",", "."]

        for suffix in suffixes:
            name = name.replace(suffix, "")

        return name.strip()

    def _extract_technology_areas(self, awards: List[Dict[str, Any]]) -> List[str]:
        """Extract technology areas from awards."""
        tech_areas = set()

        # Technology keywords mapping
        tech_keywords = {
            "AI": ["artificial intelligence", "machine learning", "ai", "ml", "neural network"],
            "Cybersecurity": ["cybersecurity", "security", "cyber", "encryption", "firewall"],
            "Robotics": ["robotics", "robot", "autonomous", "automation"],
            "Biotech": ["biotechnology", "biotech", "biology", "medical", "pharmaceutical"],
            "Materials": ["materials", "nanotechnology", "composites", "advanced materials"],
            "Energy": ["energy", "renewable", "solar", "battery", "fuel cell"],
            "Quantum": ["quantum", "quantum computing", "quantum sensing"],
            "Space": ["space", "satellite", "aerospace", "orbital"],
        }

        for award in awards:
            title = award.get("title", "").lower()
            abstract = award.get("abstract", "").lower()
            keywords = award.get("keywords", [])

            text_content = f"{title} {abstract} {' '.join(keywords)}".lower()

            for tech_area, keywords_list in tech_keywords.items():
                if any(keyword in text_content for keyword in keywords_list):
                    tech_areas.add(tech_area)

        return list(tech_areas)
