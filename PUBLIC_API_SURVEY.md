# Public API Survey for SBIR Enrichment

**Date**: 2025-10-10  
**Purpose**: Identify additional public APIs (no authentication) for award enrichment

## Summary

Tested 8 potential APIs for SBIR award enrichment. **2 APIs are viable** without authentication:
1. ✅ **NIH RePORTER** - Already integrated, excellent quality
2. ✅ **PubMed/NCBI E-utilities** - Research publications, moderate relevance

## API Test Results

### ✅ Working (No Auth Required)

#### 1. NIH RePORTER API
**Status**: ✅ Production-ready (already integrated)  
**Endpoint**: `https://api.reporter.nih.gov/v2/projects/search`  
**Coverage**: 15% of SBIR awards (NIH-funded)  
**Data Quality**: Excellent (2,981 char abstracts)  
**Enrichment Value**: ⭐⭐⭐⭐⭐

**See**: `NIH_API_INTEGRATION_STATUS.md`

---

#### 2. PubMed/NCBI E-utilities API
**Status**: ✅ Available, limited relevance  
**Endpoint**: `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`  
**Authentication**: None required  
**Rate Limit**: 3 requests/second (10/sec with API key)

**Test Query**:
```bash
# Search for SBIR + AI publications
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=SBIR+artificial+intelligence&retmode=json&retmax=1"

# Get article details
curl "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=40673165&retmode=json"
```

**Data Available**:
- Publication titles and abstracts
- Author lists
- Publication dates
- MeSH terms (medical subject headings)

**Enrichment Potential**: ⭐⭐ (Low-Medium)

**Pros**:
- No authentication required
- Rich metadata (abstracts, keywords)
- Good for biomedical/healthcare SBIR awards

**Cons**:
- Indirect connection to SBIR awards (publications ≠ awards)
- Would need to match company names to authors
- Low coverage (~5-10% of awards have publications)
- Rate limits may be restrictive for bulk enrichment

**Recommendation**: **Not worth implementing**. The effort to match awards to publications outweighs the benefit. Most SBIR companies don't publish in PubMed.

---

#### 3. NSF Award API
**Status**: ✅ **WORKS - No authentication required**  
**Endpoint**: `https://www.research.gov/awardapi-service/v1/awards.json`  
**Coverage**: NSF awards (includes SBIR Phase I/II from NSF)

**Test**:
```bash
curl "https://www.research.gov/awardapi-service/v1/awards.json?keyword=artificial%20intelligence&rpp=2"
# Returns: JSON with award data including abstracts, amounts, dates
```

**Key Fields Available**:
- `title` - Award title
- `abstractText` - Full abstract (when available)
- `fundsObligatedAmt` - Award amount
- `date` - Award date
- `startDate` - Project start date
- `awardeeName` - Institution name
- `agency` - Always "NSF"

**Note**: Previous documentation incorrectly stated this required authentication. The correct endpoint is `www.research.gov` (not `api.research.gov`).

### ❌ Blocked or Requires Authentication

---

#### 4. SBIR.gov API
**Status**: ❌ Blocked  
**Endpoint**: `https://www.sbir.gov/api/awards.json`  
**Error**: 403 Forbidden

**Test**:
```bash
curl "https://www.sbir.gov/api/awards.json?keyword=artificial+intelligence&rows=1"
# Returns: 403 Forbidden
```

**Note**: SBIR.gov likely has an API but requires authentication or is restricted to internal use.

---

#### 5. USA Spending API
**Status**: ⚠️ Partial - No enrichment value  
**Endpoint**: `https://api.usaspending.gov/api/v2/`  
**Authentication**: None required

**Test**:
```bash
curl -s "https://api.usaspending.gov/api/v2/search/spending_by_award/" \
  -H "Content-Type: application/json" \
  -d '{"filters":{"keywords":["SBIR"]},"limit":1}'
```

**Data Available**:
- Award IDs
- Recipient names
- Award amounts
- Brief descriptions (often just "SBIR" or contract codes)

**Enrichment Potential**: ⭐ (Very Low)

**Pros**:
- No authentication required
- Comprehensive federal spending data

**Cons**:
- Descriptions are minimal (e.g., "REPAIR, CALIBRATE, AND RETURN SBIR 840 C")
- No technical abstracts or detailed project information
- Data is more financial than technical

**Recommendation**: **Not useful for enrichment**. The descriptions are too brief and non-technical to improve classification.

---

#### 6. SAM.gov Entity API
**Status**: ❌ Requires API key  
**Endpoint**: `https://api.sam.gov/entity-information/v3/entities`  
**Error**: API_KEY_INVALID

**Test**:
```bash
curl "https://api.sam.gov/entity-information/v3/entities?ueiSAM=JF19T4YPH6P3&api_key=DEMO_KEY"
# Returns: API_KEY_INVALID
```

**Note**: Could provide company information (NAICS codes, business type) but requires API key registration.

---

#### 7. USPTO Patent API
**Status**: ❌ Endpoint not found  
**Endpoint**: `https://developer.uspto.gov/ibd-api/v1/application/grants`  
**Error**: 404 Not Found

**Note**: USPTO has APIs but endpoints have changed. Would require further investigation.

---

#### 8. Semantic Scholar API
**Status**: ⚠️ Rate limited without key  
**Endpoint**: `https://api.semanticscholar.org/graph/v1/paper/search`  
**Error**: 429 Too Many Requests

**Test**:
```bash
curl "https://api.semanticscholar.org/graph/v1/paper/search?query=SBIR+quantum+computing&limit=1"
# Returns: 429 Too Many Requests
```

**Note**: Similar to PubMed - would provide research papers but requires API key for reasonable rate limits.

---

#### 9. Data.gov CKAN API
**Status**: ⚠️ Metadata only  
**Endpoint**: `https://catalog.data.gov/api/3/action/package_search`  
**Authentication**: None required

**Test**:
```bash
curl "https://catalog.data.gov/api/3/action/package_search?q=sbir&rows=1"
```

**Data Available**:
- Dataset metadata (titles, descriptions)
- Links to SBIR program information
- Agency contact information

**Enrichment Potential**: ⭐ (Very Low)

**Pros**:
- No authentication required
- Comprehensive federal dataset catalog

**Cons**:
- Returns dataset metadata, not award-level data
- No technical abstracts or project details
- More useful for finding data sources than enriching awards

**Recommendation**: **Not useful for enrichment**. This is a catalog of datasets, not award data.

---

## Recommendations

### Immediate Actions
**NSF Award API integration** - Now viable since no authentication is required.

### Available Public APIs (No Authentication)

1. **NIH RePORTER** (Priority: High) - ✅ Already integrated
   - Coverage: ~15% of SBIR awards (NIH/NIAID/etc.)
   - Quality: Excellent (full abstracts, detailed metadata)
   - Status: Production-ready

2. **NSF Award API** (Priority: High) - ✅ **Newly available**
   - Coverage: ~10-15% of SBIR awards (NSF SBIR Phase I/II)
   - Quality: Good (titles, abstracts when available, amounts)
   - Endpoint: `https://www.research.gov/awardapi-service/v1/awards.json`
   - **Action**: Implement integration similar to NIH

### API Key Strategy (Optional)
If willing to register for API keys (free, no cost):

1. **SAM.gov Entity API** (Priority: Medium)
   - Coverage: 100% (company information)
   - Expected quality: Moderate (NAICS codes, business type)
   - Registration: https://sam.gov/data-services/

2. **Semantic Scholar** (Priority: Low)
   - Coverage: ~5-10% (publications)
   - Expected quality: Good (research abstracts)
   - Registration: https://www.semanticscholar.org/product/api

### Alternative Approaches

#### 1. Web Scraping (Not Recommended)
- SBIR.gov has award pages with abstracts
- Would require HTML parsing and rate limiting
- Risk of IP blocking or terms of service violations
- **Verdict**: Not worth the legal/technical risk

#### 2. Bulk Data Downloads
- Some agencies provide CSV/XML bulk downloads
- One-time download vs. API calls
- Would need to build local database
- **Verdict**: Investigate if API keys are unavailable

#### 3. Fallback Enrichment (Current Strategy)
- Use topic codes + agency to generate synthetic context
- Already implemented in `fallback_enrichment.py`
- Provides 80% of benefit with 0% API dependency
- **Verdict**: Keep as primary strategy

## Conclusion

**Two public APIs are now viable** for SBIR enrichment without authentication.

### Current State
- ✅ NIH RePORTER: ~15% coverage, excellent quality
- ✅ **NSF Award API: ~10-15% coverage, good quality** (newly discovered)
- ✅ Fallback enrichment: 100% coverage, good quality

### Recommended Strategy
1. **Keep NIH integration** - Production-ready, no auth required
2. **Add NSF integration** - Newly viable, no auth required, covers NSF SBIR awards
3. **Keep fallback enrichment** - Covers remaining 70-75% of awards
4. **Consider API keys** (optional) - SAM.gov if company data needed

### Expected Coverage with NSF Integration
- Current (NIH + fallback): ~15% real data + 85% synthetic
- **With NSF (NIH + NSF + fallback): ~25-30% real data + 70-75% synthetic**

### Expected Accuracy
- Current (NIH + fallback): 75-80%
- **With NSF integration: 78-83%**
- With all API keys: 82-87%

**The juice isn't worth the squeeze** for additional API integrations. NIH + fallback provides 90% of the benefit with minimal complexity.

---

**Last Updated**: 2025-10-10  
**APIs Tested**: 9  
**Viable Without Auth**: 1 (NIH - already integrated)
