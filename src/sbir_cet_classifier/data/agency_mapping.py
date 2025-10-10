"""Agency name to code mapping for ingestion."""

AGENCY_NAME_TO_CODE = {
    # Federal agencies with long names
    "National Oceanic and Atmospheric Administration": "NOAA",
    "National Aeronautics and Space Administration": "NASA",
    "Department of Homeland Security": "DHS",
    "Department of Health and Human Services": "HHS",
    "National Institutes of Health": "NIH",
    "National Science Foundation": "NSF",
    "Department of Defense": "DOD",
    "Department of Energy": "DOE",
    "Department of Agriculture": "USDA",
    "Department of Transportation": "DOT",
    "Department of Commerce": "DOC",
    "Environmental Protection Agency": "EPA",
    "Small Business Administration": "SBA",
    # Military branches
    "Air Force": "AF",
    "Army": "ARMY",
    "Navy": "NAVY",
    "Marine Corps": "USMC",
    "Space Force": "USSF",
    # Common variations
    "Dept of Defense": "DOD",
    "Dept of Energy": "DOE",
    "Dept of Agriculture": "USDA",
    "Dept of Transportation": "DOT",
    "Dept of Commerce": "DOC",
    "Dept of Homeland Security": "DHS",
    "Dept of Health and Human Services": "HHS",
}


def normalize_agency_name(name: str) -> str:
    """Normalize agency name to standard code."""
    if not name:
        return "UNKNOWN"
    
    # Try exact match first
    if name in AGENCY_NAME_TO_CODE:
        return AGENCY_NAME_TO_CODE[name]
    
    # Try case-insensitive match
    name_upper = name.upper()
    for full_name, code in AGENCY_NAME_TO_CODE.items():
        if full_name.upper() == name_upper:
            return code
    
    # If already short, return as-is (up to 32 chars)
    if len(name) <= 32:
        return name
    
    # Default to UNKNOWN for unmappable long names
    return "UNKNOWN"
