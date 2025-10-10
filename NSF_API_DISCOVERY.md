# NSF API Discovery Summary

**Date**: 2025-10-10  
**Status**: ✅ **NSF Award API works without authentication**

## Key Finding

The NSF Award API at `https://www.research.gov/awardapi-service/v1/awards.json` **does NOT require authentication**, contrary to previous documentation in this repository.

## Previous vs. Current Status

### Previous Documentation (Incorrect)
- **Status**: ❌ Requires authentication
- **Endpoint**: `https://api.research.gov/awardapi-service/v1/awards.json` (wrong domain)
- **Error**: 403 Forbidden
- **Source**: `PUBLIC_API_SURVEY.md`

### Actual Status (Verified)
- **Status**: ✅ Works without authentication
- **Endpoint**: `https://www.research.gov/awardapi-service/v1/awards.json` (correct domain)
- **Response**: JSON with award data
- **Test Results**: See `test_nsf_api.py`

## API Capabilities

### Available Data Fields
- `title` - Award title
- `fundsObligatedAmt` - Award amount
- `date` - Award date
- `startDate` - Project start date
- `awardeeName` - Institution name
- `awardeeCity` - Institution city
- `awardeeStateCode` - Institution state
- `agency` - Always "NSF"
- `id` - Unique award identifier
- `publicAccessMandate` - Public access flag

### Search Parameters
- `keyword` - Search in titles and abstracts
- `agency` - Filter by agency (always NSF for this API)
- `rpp` - Results per page (default: 25, max: 2000)
- `offset` - Pagination offset
- `id` - Get specific award by ID

### SBIR Coverage
- Successfully returns NSF SBIR Phase I and Phase II awards
- Example query: `?keyword=SBIR&rpp=10`
- Estimated coverage: ~10-15% of total SBIR awards (NSF portion)

## Integration Opportunity

### Current SBIR CET Classifier Coverage
- NIH RePORTER: ~15% of awards (excellent quality)
- Fallback enrichment: 85% of awards (synthetic data)

### With NSF Integration
- NIH RePORTER: ~15% of awards
- **NSF Award API: ~10-15% of awards** (newly available)
- Fallback enrichment: ~70-75% of awards
- **Total real data coverage: ~25-30%** (up from 15%)

## Implementation Plan

1. **Create NSF enrichment module** similar to existing NIH integration
2. **Add NSF API client** in `src/sbir_cet_classifier/data/enrichment/`
3. **Update ingestion pipeline** to try NSF API after NIH
4. **Add NSF-specific field mapping** for award data normalization
5. **Update tests** to include NSF API integration tests

## Files Updated

- ✅ `PUBLIC_API_SURVEY.md` - Corrected NSF API status
- ✅ `test_nsf_api.py` - Created verification script
- ✅ `NSF_API_DISCOVERY.md` - This summary document

## Next Steps

1. **Implement NSF integration** - High priority, immediate value
2. **Test with production data** - Verify coverage estimates
3. **Update documentation** - Reflect new capabilities
4. **Consider other APIs** - Re-evaluate other "blocked" APIs for similar issues

## Verification Commands

```bash
# Test basic functionality
curl "https://www.research.gov/awardapi-service/v1/awards.json?keyword=SBIR&rpp=2"

# Run comprehensive test
python test_nsf_api.py
```

---

**Impact**: This discovery increases real award data coverage by ~10-15 percentage points without requiring any API keys or authentication setup.
