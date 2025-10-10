"""Fallback enrichment when external APIs are unavailable.

Uses award metadata (topic codes, agency, program) to generate
synthetic solicitation context for classification.
"""

from sbir_cet_classifier.common.schemas import Award
from sbir_cet_classifier.common.yaml_config import load_enrichment_config

# Load configuration from YAML
_config = load_enrichment_config()


def generate_fallback_solicitation(award: Award) -> tuple[str, list[str]]:
    """Generate synthetic solicitation context from award metadata.
    
    Args:
        award: Award to generate context for
        
    Returns:
        Tuple of (description, keywords)
    """
    # Extract topic domain
    topic_prefix = award.topic_code[:2].upper() if len(award.topic_code) >= 2 else ""
    topic_domain = _config.topic_domains.get(topic_prefix)
    
    if topic_domain:
        domain_name = topic_domain.name
        keywords = list(topic_domain.keywords)
    else:
        domain_name = "Technology Development"
        keywords = ["innovation", "research"]
    
    # Get agency focus
    agency_focus = _config.agency_focus.get(award.agency, "research and development")
    
    # Generate description
    description = f"{domain_name} research for {agency_focus}"
    
    # Add program-specific keywords if available
    if award.program:
        program_lower = award.program.lower()
        if "phase i" in program_lower:
            keywords = keywords + _config.phase_keywords.phase_i
        elif "phase ii" in program_lower:
            keywords = keywords + _config.phase_keywords.phase_ii
    
    return description, keywords


def enrich_with_fallback(award: Award, award_text: str) -> str:
    """Enrich award text with fallback solicitation context.
    
    Args:
        award: Award to enrich
        award_text: Original award text (abstract + keywords)
        
    Returns:
        Enriched text with synthetic solicitation context
    """
    description, keywords = generate_fallback_solicitation(award)
    
    # Combine texts
    enriched = award_text
    if description:
        enriched = f"{enriched} {description}"
    if keywords:
        enriched = f"{enriched} {' '.join(keywords)}"
    
    return enriched
