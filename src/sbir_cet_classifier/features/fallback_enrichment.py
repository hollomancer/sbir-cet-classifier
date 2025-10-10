"""Fallback enrichment when external APIs are unavailable.

Uses award metadata (topic codes, agency, program) to generate
synthetic solicitation context for classification.
"""

from sbir_cet_classifier.common.schemas import Award


# Topic code to domain mapping (NSF and other agency SBIR topics)
TOPIC_DOMAINS = {
    # NSF SBIR Topic Codes (most common)
    "AI": ("Artificial Intelligence", ["machine learning", "neural networks", "AI", "deep learning", "computer vision"]),
    "BC": ("Biological and Chemical Technologies", ["biotechnology", "chemistry", "biochemistry", "molecular biology", "drug discovery"]),
    "BM": ("Biomedical Technologies", ["medical devices", "diagnostics", "therapeutics", "healthcare", "clinical"]),
    "BT": ("Biotechnology", ["biotechnology", "gene editing", "synthetic biology", "biomedical", "genomics"]),
    "CT": ("Communications Technology", ["telecommunications", "wireless", "networking", "5G", "signal processing"]),
    "EA": ("Environmental and Agricultural Technologies", ["environmental monitoring", "agriculture", "sustainability", "climate", "water"]),
    "EI": ("Energy and Industrial Technologies", ["energy systems", "industrial automation", "manufacturing", "process control"]),
    "EL": ("Electronics and Photonics", ["electronics", "photonics", "optics", "sensors", "imaging"]),
    "IT": ("Information Technology", ["software", "cybersecurity", "data analytics", "cloud computing", "databases"]),
    "LC": ("Low Carbon Energy", ["renewable energy", "energy storage", "sustainability", "clean energy", "solar"]),
    "MI": ("Materials and Instrumentation", ["advanced materials", "instrumentation", "measurement", "testing", "characterization"]),
    "NM": ("Nanotechnology and Advanced Materials", ["nanotechnology", "nanomaterials", "advanced materials", "composites", "coatings"]),
    "SE": ("Semiconductors and Electronics", ["semiconductors", "microelectronics", "integrated circuits", "chip design", "VLSI"]),
    
    # Generic/Legacy Topic Codes
    "ET": ("Emerging Technologies", ["quantum computing", "quantum sensing", "advanced technology", "emerging tech"]),
    "MD": ("Medical Devices", ["medical devices", "diagnostics", "healthcare technology", "clinical", "therapeutic"]),
    "PT": ("Physical Technologies", ["advanced materials", "nanotechnology", "manufacturing", "materials science"]),
    "MT": ("Manufacturing Technology", ["advanced manufacturing", "automation", "robotics", "3D printing", "additive"]),
    "ST": ("Space Technology", ["aerospace", "satellite", "space systems", "propulsion", "orbital"]),
}

# Agency-specific focus areas
AGENCY_FOCUS = {
    "NSF": "fundamental research and technology development",
    "DOD": "defense and national security applications",
    "AF": "air force and aerospace systems",
    "NAVY": "naval and maritime systems",
    "ARMY": "ground systems and soldier technology",
    "DOE": "energy systems and national laboratories",
    "NASA": "space exploration and aeronautics",
    "NIH": "biomedical research and healthcare innovation",
    "NOAA": "environmental monitoring and climate science",
}


def generate_fallback_solicitation(award: Award) -> tuple[str, list[str]]:
    """Generate synthetic solicitation context from award metadata.
    
    Args:
        award: Award to generate context for
        
    Returns:
        Tuple of (description, keywords)
    """
    # Extract topic domain
    topic_prefix = award.topic_code[:2].upper() if len(award.topic_code) >= 2 else ""
    domain_name, keywords = TOPIC_DOMAINS.get(topic_prefix, ("Technology Development", ["innovation", "research"]))
    
    # Get agency focus
    agency_focus = AGENCY_FOCUS.get(award.agency, "research and development")
    
    # Generate description
    description = f"{domain_name} research for {agency_focus}"
    
    # Add program-specific keywords if available
    if award.program:
        program_lower = award.program.lower()
        if "phase i" in program_lower:
            keywords = keywords + ["feasibility", "proof of concept"]
        elif "phase ii" in program_lower:
            keywords = keywords + ["development", "commercialization"]
    
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
