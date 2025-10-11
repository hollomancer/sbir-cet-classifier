"""Tests for agency name normalization."""


from sbir_cet_classifier.data.agency_mapping import normalize_agency_name


class TestNormalizeAgencyName:
    """Test agency name normalization."""

    def test_exact_match(self):
        """Test exact match from mapping table."""
        assert normalize_agency_name("National Aeronautics and Space Administration") == "NASA"
        assert normalize_agency_name("Department of Defense") == "DOD"

    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        assert normalize_agency_name("NATIONAL AERONAUTICS AND SPACE ADMINISTRATION") == "NASA"
        assert normalize_agency_name("department of defense") == "DOD"

    def test_short_name_passthrough(self):
        """Test short names pass through unchanged."""
        assert normalize_agency_name("NASA") == "NASA"
        assert normalize_agency_name("DOD") == "DOD"
        assert normalize_agency_name("AF") == "AF"

    def test_unmappable_long_name(self):
        """Test unmappable long names default to UNKNOWN."""
        long_name = "Some Very Long Agency Name That Exceeds Thirty Two Characters"
        assert normalize_agency_name(long_name) == "UNKNOWN"

    def test_empty_string(self):
        """Test empty string returns UNKNOWN."""
        assert normalize_agency_name("") == "UNKNOWN"

    def test_military_branches(self):
        """Test military branch mappings."""
        assert normalize_agency_name("Air Force") == "AF"
        assert normalize_agency_name("Navy") == "NAVY"
        assert normalize_agency_name("Army") == "ARMY"
