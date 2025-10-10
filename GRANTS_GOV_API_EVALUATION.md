# Grants.gov API Evaluation

**Date**: 2025-10-10  
**Decision**: ❌ **NOT VALUABLE - REMOVED FROM CODEBASE**

## Summary

The Grants.gov API is **not applicable** to our SBIR enrichment use case and has been removed from the codebase.

## API Purpose vs. Our Need

| Aspect | Grants.gov API | Our Requirement |
|--------|----------------|-----------------|
| **Data Type** | Open/active grant opportunities | Historical SBIR award solicitation metadata |
| **Use Case** | Applicants searching for opportunities to apply to | Enriching past awards with solicitation details |
| **Lookup Method** | Search by keywords, agency, category | Lookup by SBIR topic code (e.g., "N242-074") |
| **Authentication** | Requires API key | Prefer public/no-auth APIs |

## API Endpoints

The Grants.gov API provides two main endpoints:

1. **search2** - Returns list of open Opportunity Packages matching filter criteria
2. **fetchOpportunity** - Returns details of a specific open opportunity

**Problem**: These endpoints return **active solicitations** for applicants to apply to, not historical solicitation metadata for past awards.

## Evaluation Results

- **Match Rate**: 0% (API returned HTTP 302 redirects for all topic code lookups)
- **Data Relevance**: Not applicable - wrong data type
- **Authentication**: Requires API key (not publicly accessible)
- **CSV Data**: Award CSV already contains complete award-level data including abstracts

## Comparison to Other APIs

| API | Status | Reason |
|-----|--------|--------|
| **NIH RePORTER** | ✅ Kept | 99% match rate, +24% text, +160% keywords |
| **NSF API** | ❌ Removed | CSV data superior (16x more content) |
| **Grants.gov API** | ❌ Removed | Wrong data type (open opportunities, not historical awards) |

## Files Removed

- `src/sbir_cet_classifier/data/external/grants_gov.py` - API client (stub implementation)
- `tests/unit/sbir_cet_classifier/data/external/test_grants_gov.py` - Unit tests
- `test_grants_gov_api.py` - Evaluation script
- All references from enrichment pipeline, cache, and metrics

## Recommendation

**No action needed**. The Grants.gov API serves a different purpose (helping applicants find opportunities) and cannot enrich historical SBIR awards. Our CSV data already contains all necessary award-level information.

## Related Documentation

- NSF API removal: `NSF_API_DISCOVERY.md` (removed - CSV data superior)
- NIH API integration: `NIH_API_INTEGRATION_STATUS.md` (kept - valuable enrichment)
- Public API survey: `PUBLIC_API_SURVEY.md`
