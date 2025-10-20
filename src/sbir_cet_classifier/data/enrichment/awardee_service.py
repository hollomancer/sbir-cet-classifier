"""Awardee historical data retrieval service."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
from collections import Counter

from .models import AwardeeMetrics


@dataclass
class AwardeeHistoricalDataService:
    """Service for retrieving awardee historical data."""
    
    def __init__(self, sam_client):
        """Initialize with SAM.gov API client."""
        self.sam_client = sam_client
        self.performance_analyzer = AwardeePerformanceAnalyzer()
    
    def get_awardee_awards_history(
        self, 
        uei: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        fetch_all: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve awardee awards history."""
        try:
            if fetch_all:
                return self._fetch_all_awards(uei, start_date, end_date)
            else:
                response = self.sam_client.get_awards_by_uei(
                    uei, 
                    start_date=start_date, 
                    end_date=end_date
                )
                return response.get("awards", [])
        except Exception as e:
            raise Exception(f"Failed to retrieve awards history for UEI {uei}: {str(e)}")
    
    def _fetch_all_awards(
        self, 
        uei: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all awards using pagination."""
        all_awards = []
        offset = 0
        limit = 100
        
        while True:
            try:
                response = self.sam_client.get_awards_by_uei(
                    uei, 
                    start_date=start_date, 
                    end_date=end_date,
                    offset=offset,
                    limit=limit
                )
                
                awards = response.get("awards", [])
                if not awards:
                    break
                
                all_awards.extend(awards)
                
                # Check if we've fetched all records
                total_records = response.get("totalRecords", 0)
                if len(all_awards) >= total_records:
                    break
                
                offset += limit
                
            except Exception as e:
                # Log error but continue with what we have
                break
        
        return all_awards
    
    def get_awardee_performance_metrics(self, uei: str) -> AwardeeMetrics:
        """Calculate awardee performance metrics."""
        awards = self.get_awardee_awards_history(uei, fetch_all=True)
        
        if not awards:
            return AwardeeMetrics(
                uei=uei,
                total_awards=0,
                total_funding=Decimal("0.00"),
                success_rate=0.0,
                avg_award_amount=Decimal("0.00"),
                first_award_date=datetime.now(),
                last_award_date=datetime.now(),
                primary_agencies=[],
                technology_areas=[]
            )
        
        # Calculate basic metrics
        total_awards = len(awards)
        total_funding = sum(Decimal(str(award.get("awardAmount", 0))) for award in awards)
        avg_award_amount = total_funding / total_awards if total_awards > 0 else Decimal("0")
        
        # Calculate success rate
        success_rate = self.performance_analyzer.calculate_success_rate(awards)
        
        # Extract dates
        award_dates = self._extract_award_dates(awards)
        first_award_date = min(award_dates) if award_dates else datetime.now()
        last_award_date = max(award_dates) if award_dates else datetime.now()
        
        # Extract agencies
        primary_agencies = list(set(
            award.get("fundingAgency") 
            for award in awards 
            if award.get("fundingAgency")
        ))
        
        # Extract technology areas
        technology_areas = self.get_awardee_technology_areas(uei)
        
        # Calculate award size distribution
        award_size_distribution = self._calculate_award_size_distribution(awards)
        
        return AwardeeMetrics(
            uei=uei,
            total_awards=total_awards,
            total_funding=total_funding,
            success_rate=success_rate,
            avg_award_amount=avg_award_amount,
            first_award_date=first_award_date,
            last_award_date=last_award_date,
            primary_agencies=primary_agencies,
            technology_areas=technology_areas,
            award_size_distribution=award_size_distribution
        )
    
    def get_awardee_technology_areas(self, uei: str) -> List[str]:
        """Extract technology areas from awardee's awards."""
        awards = self.get_awardee_awards_history(uei)
        return self.performance_analyzer.identify_expertise_areas(awards)
    
    def _extract_award_dates(self, awards: List[Dict[str, Any]]) -> List[datetime]:
        """Extract award dates from awards list."""
        dates = []
        
        for award in awards:
            start_date_str = award.get("startDate")
            if start_date_str:
                try:
                    # Handle different date formats
                    if start_date_str.endswith('Z'):
                        date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                    else:
                        date = datetime.fromisoformat(start_date_str)
                    dates.append(date.replace(tzinfo=None))  # Remove timezone for consistency
                except ValueError:
                    continue
        
        return dates
    
    def _calculate_award_size_distribution(self, awards: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate distribution of award sizes."""
        distribution = {"small": 0, "medium": 0, "large": 0}
        
        for award in awards:
            amount = award.get("awardAmount", 0)
            if amount < 100000:
                distribution["small"] += 1
            elif amount <= 500000:
                distribution["medium"] += 1
            else:
                distribution["large"] += 1
        
        return distribution


class AwardeePerformanceAnalyzer:
    """Analyzer for awardee performance metrics."""
    
    def calculate_success_rate(self, awards: List[Dict[str, Any]]) -> float:
        """Calculate success rate based on award statuses."""
        if not awards:
            return 0.0
        
        successful_statuses = {"Completed", "Active", "Ongoing"}
        successful_count = sum(
            1 for award in awards 
            if award.get("awardStatus") in successful_statuses
        )
        
        return successful_count / len(awards)
    
    def analyze_funding_trends(self, awards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze funding trends over time."""
        if not awards:
            return {"trend": "no_data", "total_growth": 0.0, "avg_annual_growth": 0.0}
        
        # Sort awards by start date
        dated_awards = []
        for award in awards:
            start_date_str = award.get("startDate")
            if start_date_str:
                try:
                    if start_date_str.endswith('Z'):
                        date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                    else:
                        date = datetime.fromisoformat(start_date_str)
                    dated_awards.append((date, award.get("awardAmount", 0)))
                except ValueError:
                    continue
        
        if len(dated_awards) < 2:
            return {"trend": "insufficient_data", "total_growth": 0.0, "avg_annual_growth": 0.0}
        
        dated_awards.sort(key=lambda x: x[0])
        
        first_amount = dated_awards[0][1]
        last_amount = dated_awards[-1][1]
        first_date = dated_awards[0][0]
        last_date = dated_awards[-1][0]
        
        total_growth = last_amount - first_amount
        years_span = (last_date - first_date).days / 365.25
        
        if years_span > 0:
            avg_annual_growth = total_growth / years_span
        else:
            avg_annual_growth = 0.0
        
        # Determine trend
        if total_growth > 0:
            trend = "increasing"
        elif total_growth < 0:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "total_growth": total_growth,
            "avg_annual_growth": avg_annual_growth,
            "years_span": years_span
        }
    
    def identify_expertise_areas(self, awards: List[Dict[str, Any]]) -> List[str]:
        """Identify expertise areas from awards."""
        # Technology keywords mapping
        tech_keywords = {
            "AI": ["artificial intelligence", "machine learning", "ai", "ml", "neural network", "deep learning"],
            "Cybersecurity": ["cybersecurity", "security", "cyber", "encryption", "firewall", "network security"],
            "Robotics": ["robotics", "robot", "autonomous", "automation", "robotic"],
            "Biotech": ["biotechnology", "biotech", "biology", "medical", "pharmaceutical", "biomedical"],
            "Materials": ["materials", "nanotechnology", "composites", "advanced materials", "nanomaterials"],
            "Energy": ["energy", "renewable", "solar", "battery", "fuel cell", "wind", "power"],
            "Quantum": ["quantum", "quantum computing", "quantum sensing", "quantum mechanics"],
            "Space": ["space", "satellite", "aerospace", "orbital", "spacecraft"],
            "Manufacturing": ["manufacturing", "3d printing", "additive", "production", "fabrication"],
            "Communications": ["communications", "wireless", "5g", "networking", "telecommunications"]
        }
        
        tech_area_counts = Counter()
        
        for award in awards:
            title = award.get("title", "").lower()
            abstract = award.get("abstract", "").lower()
            keywords = award.get("keywords", [])
            
            # Combine all text content
            text_content = f"{title} {abstract} {' '.join(str(k).lower() for k in keywords)}"
            
            # Count occurrences of each technology area
            for tech_area, keywords_list in tech_keywords.items():
                if any(keyword in text_content for keyword in keywords_list):
                    tech_area_counts[tech_area] += 1
        
        # Return areas sorted by frequency
        return [area for area, count in tech_area_counts.most_common()]
    
    def calculate_agency_diversity(self, awards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate agency diversity metrics."""
        if not awards:
            return {
                "unique_agencies": 0,
                "diversity_score": 0.0,
                "agency_distribution": {}
            }
        
        agencies = [award.get("fundingAgency") for award in awards if award.get("fundingAgency")]
        agency_counts = Counter(agencies)
        
        unique_agencies = len(agency_counts)
        total_awards = len(agencies)
        diversity_score = unique_agencies / total_awards if total_awards > 0 else 0.0
        
        return {
            "unique_agencies": unique_agencies,
            "diversity_score": diversity_score,
            "agency_distribution": dict(agency_counts)
        }
    
    def benchmark_performance(self, metrics: AwardeeMetrics) -> Dict[str, Any]:
        """Benchmark performance against industry standards."""
        # Industry benchmarks (these would typically come from a database)
        benchmarks = {
            "success_rate_percentiles": {
                0.9: 90,
                0.8: 75,
                0.7: 60,
                0.6: 40,
                0.5: 25
            },
            "funding_categories": {
                "startup": (0, 500000),
                "small": (500000, 2000000),
                "medium": (2000000, 10000000),
                "large": (10000000, float('inf'))
            }
        }
        
        # Calculate success rate percentile
        success_rate_percentile = 0
        for rate, percentile in benchmarks["success_rate_percentiles"].items():
            if metrics.success_rate >= rate:
                success_rate_percentile = percentile
                break
        
        # Determine funding level category
        funding_level_category = "startup"
        total_funding_float = float(metrics.total_funding)
        for category, (min_val, max_val) in benchmarks["funding_categories"].items():
            if min_val <= total_funding_float < max_val:
                funding_level_category = category
                break
        
        # Determine experience level
        years_active = metrics.calculate_years_active()
        if years_active >= 10:
            experience_level = "veteran"
        elif years_active >= 5:
            experience_level = "experienced"
        elif years_active >= 2:
            experience_level = "emerging"
        else:
            experience_level = "new"
        
        return {
            "success_rate_percentile": success_rate_percentile,
            "funding_level_category": funding_level_category,
            "experience_level": experience_level,
            "years_active": years_active
        }
    
    def assess_risk(self, awards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess risk factors for awardee."""
        risk_factors = []
        risk_score = 0.0
        
        if not awards:
            return {
                "risk_score": 1.0,
                "risk_factors": ["No award history"],
                "mitigation_recommendations": ["Establish track record with smaller awards"]
            }
        
        # Check for terminated awards
        terminated_count = sum(1 for award in awards if award.get("awardStatus") == "Terminated")
        if terminated_count > 0:
            termination_rate = terminated_count / len(awards)
            risk_factors.append(f"Award termination rate: {termination_rate:.1%}")
            risk_score += termination_rate * 0.5
        
        # Check for recent activity
        recent_awards = [
            award for award in awards 
            if self._is_recent_award(award, years=2)
        ]
        
        if not recent_awards:
            risk_factors.append("No recent award activity (past 2 years)")
            risk_score += 0.3
        
        # Check agency concentration
        agencies = [award.get("fundingAgency") for award in awards if award.get("fundingAgency")]
        if agencies:
            agency_counts = Counter(agencies)
            max_agency_share = max(agency_counts.values()) / len(agencies)
            if max_agency_share > 0.8:
                risk_factors.append(f"High agency concentration: {max_agency_share:.1%}")
                risk_score += 0.2
        
        # Generate mitigation recommendations
        mitigation_recommendations = []
        if "termination" in str(risk_factors).lower():
            mitigation_recommendations.append("Improve project management and delivery capabilities")
        if "recent" in str(risk_factors).lower():
            mitigation_recommendations.append("Pursue new funding opportunities to maintain active status")
        if "concentration" in str(risk_factors).lower():
            mitigation_recommendations.append("Diversify funding sources across multiple agencies")
        
        return {
            "risk_score": min(risk_score, 1.0),
            "risk_factors": risk_factors,
            "mitigation_recommendations": mitigation_recommendations
        }
    
    def _is_recent_award(self, award: Dict[str, Any], years: int = 2) -> bool:
        """Check if award is recent (within specified years)."""
        start_date_str = award.get("startDate")
        if not start_date_str:
            return False
        
        try:
            if start_date_str.endswith('Z'):
                award_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            else:
                award_date = datetime.fromisoformat(start_date_str)
            
            cutoff_date = datetime.now() - timedelta(days=years * 365)
            return award_date.replace(tzinfo=None) >= cutoff_date
        except ValueError:
            return False
