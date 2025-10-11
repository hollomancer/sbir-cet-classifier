"""Awardee data matching logic and strategies."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import re


class MatchStrategy(Enum):
    """Awardee matching strategies."""
    UEI_FIRST = "uei_first"
    NAME_ONLY = "name_only"
    COMPREHENSIVE = "comprehensive"


@dataclass
class MatchResult:
    """Result of awardee matching operation."""
    award_id: str
    is_match: bool
    confidence_score: float
    matched_uei: Optional[str] = None
    match_method: Optional[str] = None
    match_details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "award_id": self.award_id,
            "is_match": self.is_match,
            "confidence_score": self.confidence_score,
            "matched_uei": self.matched_uei,
            "match_method": self.match_method,
            "match_details": self.match_details or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MatchResult':
        """Create from dictionary."""
        return cls(
            award_id=data["award_id"],
            is_match=data["is_match"],
            confidence_score=data["confidence_score"],
            matched_uei=data.get("matched_uei"),
            match_method=data.get("match_method"),
            match_details=data.get("match_details", {})
        )


class BaseMatcher(ABC):
    """Base class for awardee matchers."""
    
    @abstractmethod
    def match(self, award_data: Dict[str, Any], sam_entity: Dict[str, Any]) -> MatchResult:
        """Match award data against SAM entity."""
        pass


class UEIMatcher(BaseMatcher):
    """UEI-based matching."""
    
    def match(self, award_data: Dict[str, Any], sam_entity: Dict[str, Any]) -> MatchResult:
        """Match based on UEI."""
        award_id = award_data.get("award_id", "")
        award_uei = award_data.get("awardee_uei")
        sam_uei = sam_entity.get("ueiSAM")
        
        if not award_uei or not sam_uei:
            return MatchResult(
                award_id=award_id,
                is_match=False,
                confidence_score=0.0,
                match_method="uei_missing"
            )
        
        if award_uei == sam_uei:
            return MatchResult(
                award_id=award_id,
                is_match=True,
                confidence_score=1.0,
                matched_uei=sam_uei,
                match_method="exact_uei",
                match_details={"uei_match": True}
            )
        
        return MatchResult(
            award_id=award_id,
            is_match=False,
            confidence_score=0.0,
            match_method="uei_mismatch"
        )


class FuzzyNameMatcher(BaseMatcher):
    """Fuzzy name matching."""
    
    def __init__(self, threshold: float = 0.8):
        """Initialize with similarity threshold."""
        self.threshold = threshold
    
    def match(self, award_data: Dict[str, Any], sam_entity: Dict[str, Any]) -> MatchResult:
        """Match based on fuzzy name similarity."""
        award_id = award_data.get("award_id", "")
        award_name = award_data.get("awardee_name")
        sam_name = sam_entity.get("legalBusinessName")
        
        if not award_name or not sam_name:
            return MatchResult(
                award_id=award_id,
                is_match=False,
                confidence_score=0.0,
                match_method="name_missing"
            )
        
        # Calculate similarity
        similarity = self._calculate_similarity(award_name, sam_name)
        
        if similarity == 1.0:
            match_method = "exact_name"
        elif similarity >= self.threshold:
            match_method = "fuzzy_name"
        else:
            match_method = "name_mismatch"
        
        is_match = similarity >= self.threshold
        
        return MatchResult(
            award_id=award_id,
            is_match=is_match,
            confidence_score=similarity,
            matched_uei=sam_entity.get("ueiSAM") if is_match else None,
            match_method=match_method,
            match_details={
                "name_similarity": similarity,
                "award_name": award_name,
                "sam_name": sam_name
            }
        )
    
    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        # Normalize names
        norm_name1 = self._normalize_name(name1)
        norm_name2 = self._normalize_name(name2)
        
        if norm_name1 == norm_name2:
            return 1.0
        
        # Use Jaccard similarity on word sets
        words1 = set(norm_name1.split())
        words2 = set(norm_name2.split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison."""
        if not name:
            return ""
        
        # Convert to lowercase
        name = name.lower()
        
        # Remove common business suffixes
        suffixes = [
            r'\binc\.?$', r'\bincorporated$', r'\bllc\.?$', r'\bcorp\.?$',
            r'\bco\.?$', r'\bltd\.?$', r'\blimited$', r'\bcompany$'
        ]
        
        for suffix in suffixes:
            name = re.sub(suffix, '', name)
        
        # Remove punctuation and extra spaces
        name = re.sub(r'[^\w\s]', ' ', name)
        name = re.sub(r'\s+', ' ', name)
        
        return name.strip()


class AwardNumberMatcher(BaseMatcher):
    """Award number matching."""
    
    def match(self, award_data: Dict[str, Any], sam_award: Dict[str, Any]) -> MatchResult:
        """Match based on award number."""
        award_id = award_data.get("award_id", "")
        award_number = award_data.get("award_number")
        sam_award_number = sam_award.get("awardNumber")
        
        if not award_number or not sam_award_number:
            return MatchResult(
                award_id=award_id,
                is_match=False,
                confidence_score=0.0,
                match_method="award_number_missing"
            )
        
        if award_number == sam_award_number:
            return MatchResult(
                award_id=award_id,
                is_match=True,
                confidence_score=1.0,
                match_method="exact_award_number",
                match_details={"award_number_match": True}
            )
        
        return MatchResult(
            award_id=award_id,
            is_match=False,
            confidence_score=0.0,
            match_method="award_number_mismatch"
        )


class AwardeeDataMatcher:
    """Comprehensive awardee data matching service."""
    
    def __init__(self, sam_client):
        """Initialize with SAM.gov API client."""
        self.sam_client = sam_client
        self.uei_matcher = UEIMatcher()
        self.name_matcher = FuzzyNameMatcher(threshold=0.8)
        self.award_matcher = AwardNumberMatcher()
    
    def match_awardee(self, award_data: Dict[str, Any], strategy: MatchStrategy = MatchStrategy.UEI_FIRST) -> MatchResult:
        """Match awardee using specified strategy."""
        award_id = award_data.get("award_id", "")
        
        if strategy == MatchStrategy.UEI_FIRST:
            return self._match_uei_first(award_data)
        elif strategy == MatchStrategy.NAME_ONLY:
            return self._match_name_only(award_data)
        elif strategy == MatchStrategy.COMPREHENSIVE:
            return self._match_comprehensive(award_data)
        else:
            return MatchResult(
                award_id=award_id,
                is_match=False,
                confidence_score=0.0,
                match_method="unknown_strategy"
            )
    
    def _match_uei_first(self, award_data: Dict[str, Any]) -> MatchResult:
        """Match using UEI first, fallback to name."""
        award_id = award_data.get("award_id", "")
        awardee_uei = award_data.get("awardee_uei")
        
        # Try UEI match first
        if awardee_uei:
            try:
                sam_entity = self.sam_client.get_entity_by_uei(awardee_uei)
                if sam_entity:
                    result = self.uei_matcher.match(award_data, sam_entity)
                    if result.is_match:
                        return result
            except Exception:
                pass
        
        # Fallback to name matching
        return self._match_name_only(award_data)
    
    def _match_name_only(self, award_data: Dict[str, Any]) -> MatchResult:
        """Match using name only."""
        award_id = award_data.get("award_id", "")
        awardee_name = award_data.get("awardee_name")
        
        if not awardee_name:
            return MatchResult(
                award_id=award_id,
                is_match=False,
                confidence_score=0.0,
                match_method="no_name_provided"
            )
        
        try:
            # Search for entities by name
            search_response = self.sam_client.search_entities(legal_business_name=awardee_name)
            entities = search_response.get("entities", [])
            
            if not entities:
                return MatchResult(
                    award_id=award_id,
                    is_match=False,
                    confidence_score=0.0,
                    match_method="no_entities_found"
                )
            
            # Find best match
            best_result = None
            best_score = 0.0
            
            for entity in entities:
                result = self.name_matcher.match(award_data, entity)
                if result.is_match and result.confidence_score > best_score:
                    best_result = result
                    best_score = result.confidence_score
            
            return best_result or MatchResult(
                award_id=award_id,
                is_match=False,
                confidence_score=0.0,
                match_method="no_name_match_above_threshold"
            )
            
        except Exception as e:
            return MatchResult(
                award_id=award_id,
                is_match=False,
                confidence_score=0.0,
                match_method="api_error",
                match_details={"error": str(e)}
            )
    
    def _match_comprehensive(self, award_data: Dict[str, Any]) -> MatchResult:
        """Comprehensive matching using multiple strategies."""
        award_id = award_data.get("award_id", "")
        
        # Start with UEI matching
        uei_result = self._match_uei_first(award_data)
        
        if not uei_result.is_match:
            return uei_result
        
        # If UEI matched, enhance with additional validation
        matched_uei = uei_result.matched_uei
        
        try:
            # Get entity details
            sam_entity = self.sam_client.get_entity_by_uei(matched_uei)
            if not sam_entity:
                return uei_result
            
            # Validate with name matching
            name_result = self.name_matcher.match(award_data, sam_entity)
            
            # Check award number if available
            award_number_match = False
            award_number = award_data.get("award_number")
            if award_number:
                try:
                    awards_response = self.sam_client.get_awards_by_uei(matched_uei)
                    sam_awards = awards_response.get("awards", [])
                    
                    for sam_award in sam_awards:
                        award_result = self.award_matcher.match(award_data, sam_award)
                        if award_result.is_match:
                            award_number_match = True
                            break
                except Exception:
                    pass
            
            # Calculate comprehensive confidence score
            match_details = {
                "uei_match": True,
                "name_match": name_result.is_match,
                "name_similarity": name_result.confidence_score,
                "award_number_match": award_number_match
            }
            
            confidence = self.calculate_confidence_score(match_details)
            
            return MatchResult(
                award_id=award_id,
                is_match=confidence >= 0.7,  # Threshold for comprehensive match
                confidence_score=confidence,
                matched_uei=matched_uei,
                match_method="comprehensive",
                match_details=match_details
            )
            
        except Exception as e:
            # Return UEI result if comprehensive validation fails
            return uei_result
    
    def calculate_confidence_score(self, match_details: Dict[str, Any]) -> float:
        """Calculate confidence score from match details."""
        score = 0.0
        
        # UEI match (highest weight)
        if match_details.get("uei_match"):
            score += 0.5
        
        # Name similarity
        name_similarity = match_details.get("name_similarity", 0.0)
        if match_details.get("name_match"):
            score += 0.3
        else:
            score += name_similarity * 0.2  # Partial credit for similarity
        
        # Award number match
        if match_details.get("award_number_match"):
            score += 0.2
        
        # Address similarity (if available)
        address_similarity = match_details.get("address_similarity", 0.0)
        score += address_similarity * 0.1
        
        return min(score, 1.0)
    
    def batch_match_awardees(self, awards: List[Dict[str, Any]], strategy: MatchStrategy = MatchStrategy.UEI_FIRST) -> List[MatchResult]:
        """Batch match multiple awards."""
        results = []
        
        for award in awards:
            try:
                result = self.match_awardee(award, strategy)
                results.append(result)
            except Exception as e:
                # Create error result
                award_id = award.get("award_id", "")
                error_result = MatchResult(
                    award_id=award_id,
                    is_match=False,
                    confidence_score=0.0,
                    match_method="batch_error",
                    match_details={"error": str(e)}
                )
                results.append(error_result)
        
        return results
