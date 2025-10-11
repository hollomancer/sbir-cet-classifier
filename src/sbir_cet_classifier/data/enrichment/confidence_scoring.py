"""Confidence scoring for awardee matches."""

from enum import Enum
from typing import Dict, Any
from dataclasses import dataclass


class MatchFactor(Enum):
    """Match factors for confidence scoring."""
    UEI_EXACT = "uei_exact"
    NAME_EXACT = "name_exact"
    NAME_SIMILARITY = "name_similarity"
    AWARD_NUMBER_EXACT = "award_number_exact"
    ADDRESS_SIMILARITY = "address_similarity"


@dataclass
class ScoreWeights:
    """Weights for confidence scoring factors."""
    uei_exact: float = 0.5
    name_exact: float = 0.3
    name_similarity: float = 0.2
    award_number_exact: float = 0.2
    address_similarity: float = 0.1
    
    def __post_init__(self):
        """Validate weights."""
        for field_name, value in self.__dict__.items():
            if value < 0.0 or value > 1.0:
                raise ValueError(f"Weight {field_name} must be between 0.0 and 1.0")


class ConfidenceScorer:
    """Confidence scorer for awardee matches."""
    
    def __init__(self, weights: ScoreWeights = None):
        """Initialize with scoring weights."""
        self.weights = weights or ScoreWeights()
        
        # Confidence level thresholds
        self.thresholds = {
            "high": 0.8,
            "medium": 0.5,
            "low": 0.0
        }
    
    def calculate_score(self, match_factors: Dict[MatchFactor, Any]) -> float:
        """Calculate confidence score from match factors."""
        score = 0.0
        
        # UEI exact match (highest confidence)
        if match_factors.get(MatchFactor.UEI_EXACT, False):
            score += self.weights.uei_exact
        
        # Name matching
        if match_factors.get(MatchFactor.NAME_EXACT, False):
            score += self.weights.name_exact
        else:
            # Partial credit for name similarity
            name_similarity = match_factors.get(MatchFactor.NAME_SIMILARITY, 0.0)
            score += name_similarity * self.weights.name_similarity
        
        # Award number exact match
        if match_factors.get(MatchFactor.AWARD_NUMBER_EXACT, False):
            score += self.weights.award_number_exact
        
        # Address similarity
        address_similarity = match_factors.get(MatchFactor.ADDRESS_SIMILARITY, 0.0)
        score += address_similarity * self.weights.address_similarity
        
        # Normalize score to [0, 1] range
        return min(score, 1.0)
    
    def get_confidence_level(self, score: float) -> str:
        """Get confidence level from score."""
        if score >= self.thresholds["high"]:
            return "high"
        elif score >= self.thresholds["medium"]:
            return "medium"
        else:
            return "low"
    
    def explain_score(self, match_factors: Dict[MatchFactor, Any]) -> Dict[str, Any]:
        """Explain how the confidence score was calculated."""
        explanation = {
            "total_score": 0.0,
            "components": {},
            "confidence_level": "low"
        }
        
        # Calculate component scores
        components = {}
        
        if match_factors.get(MatchFactor.UEI_EXACT, False):
            components["uei_exact"] = self.weights.uei_exact
        
        if match_factors.get(MatchFactor.NAME_EXACT, False):
            components["name_exact"] = self.weights.name_exact
        else:
            name_similarity = match_factors.get(MatchFactor.NAME_SIMILARITY, 0.0)
            if name_similarity > 0:
                components["name_similarity"] = name_similarity * self.weights.name_similarity
        
        if match_factors.get(MatchFactor.AWARD_NUMBER_EXACT, False):
            components["award_number_exact"] = self.weights.award_number_exact
        
        address_similarity = match_factors.get(MatchFactor.ADDRESS_SIMILARITY, 0.0)
        if address_similarity > 0:
            components["address_similarity"] = address_similarity * self.weights.address_similarity
        
        total_score = sum(components.values())
        total_score = min(total_score, 1.0)
        
        explanation["total_score"] = total_score
        explanation["components"] = components
        explanation["confidence_level"] = self.get_confidence_level(total_score)
        
        return explanation
    
    def set_thresholds(self, high: float, medium: float, low: float = 0.0) -> None:
        """Set custom confidence level thresholds."""
        if not (0.0 <= low <= medium <= high <= 1.0):
            raise ValueError("Thresholds must be in ascending order between 0.0 and 1.0")
        
        self.thresholds = {
            "high": high,
            "medium": medium,
            "low": low
        }
