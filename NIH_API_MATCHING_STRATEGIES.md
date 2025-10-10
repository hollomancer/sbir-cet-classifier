# NIH API Matching Strategies

**Date**: 2025-10-10  
**Status**: Alternative approaches to match CSV awards with NIH API

## Problem

CSV awards lack NIH project numbers, which are the primary identifier for the NIH Reporter API. We need alternative matching strategies.

## Available Data

### In Our CSV
- `firm_name` - Company name
- `award_amount` - Dollar amount
- `award_date` - Award date (year)
- `award_id` - Internal ID (not NIH project number)
- `topic_code` - SBIR topic code
- `abstract` - Award abstract text

### NIH API Search Criteria
The NIH Reporter API supports searching by:
- `org_names` - Organization/company names
- `award_amount_range` - Min/max dollar amounts
- `fiscal_years` - Fiscal year(s)
- `pi_names` - Principal investigator names
- `project_nums` - Project numbers (if we had them)
- `appl_ids` - Application IDs
- `foa` - Funding opportunity announcements

## Matching Strategies

### Strategy 1: Organization + Amount + Year (Recommended)
**Match on**: Company name + award amount (±10%) + fiscal year

**Pros**:
- Uses data we have
- Relatively unique combination
- API supports all three criteria

**Cons**:
- Company names may not match exactly
- Multiple awards to same company in same year
- Amount may differ slightly (overhead, etc.)

**Implementation**:
```python
def find_nih_project(award):
    """Find NIH project by organization, amount, and year."""
    amount_min = award.award_amount * 0.9
    amount_max = award.award_amount * 1.1
    
    criteria = {
        'org_names': [award.firm_name],
        'award_amount_range': {
            'min_amount': int(amount_min),
            'max_amount': int(amount_max)
        },
        'fiscal_years': [award.award_date.year]
    }
    
    # Search API and return best match
    results = nih_api.search(criteria)
    return results[0] if results else None
```

**Expected match rate**: 40-60%

### Strategy 2: Text Similarity Matching
**Match on**: Abstract text similarity

**Pros**:
- Abstracts are unique
- We have abstracts in CSV
- NIH API returns abstracts

**Cons**:
- Requires downloading many NIH projects
- Computationally expensive
- Abstracts may differ between CSV and NIH

**Implementation**:
```python
def find_by_abstract_similarity(award):
    """Find NIH project by abstract similarity."""
    # 1. Search by org + year (broad)
    candidates = nih_api.search({
        'org_names': [award.firm_name],
        'fiscal_years': [award.award_date.year]
    })
    
    # 2. Compare abstracts
    best_match = None
    best_score = 0
    
    for candidate in candidates:
        score = text_similarity(award.abstract, candidate.abstract)
        if score > best_score:
            best_score = score
            best_match = candidate
    
    return best_match if best_score > 0.8 else None
```

**Expected match rate**: 60-80%

### Strategy 3: Fuzzy Organization Name Matching
**Match on**: Fuzzy company name + amount + year

**Pros**:
- Handles name variations
- More robust than exact matching

**Cons**:
- More complex
- May have false positives

**Implementation**:
```python
def normalize_org_name(name):
    """Normalize organization name for matching."""
    # Remove common suffixes
    name = name.upper()
    for suffix in [' INC', ' LLC', ' CORP', ' CO', ' LTD']:
        name = name.replace(suffix, '')
    return name.strip()

def find_with_fuzzy_org(award):
    """Find with fuzzy organization matching."""
    normalized = normalize_org_name(award.firm_name)
    
    # Try variations
    variations = [
        award.firm_name,
        normalized,
        normalized.replace(',', ''),
        # Add more variations
    ]
    
    for org_name in variations:
        results = find_nih_project_with_org(org_name, award)
        if results:
            return results[0]
    
    return None
```

**Expected match rate**: 50-70%

### Strategy 4: Hybrid Approach (Best)
**Match on**: Combination of strategies with confidence scoring

**Pros**:
- Highest match rate
- Confidence scores for validation
- Fallback options

**Cons**:
- Most complex
- Slower

**Implementation**:
```python
def find_nih_project_hybrid(award):
    """Hybrid matching with confidence scoring."""
    matches = []
    
    # Try exact org + amount + year
    exact = find_by_org_amount_year(award)
    if exact:
        matches.append(('exact', 1.0, exact))
    
    # Try fuzzy org + amount + year
    fuzzy = find_with_fuzzy_org(award)
    if fuzzy:
        matches.append(('fuzzy', 0.8, fuzzy))
    
    # Try abstract similarity
    similar = find_by_abstract_similarity(award)
    if similar:
        matches.append(('abstract', 0.9, similar))
    
    # Return best match
    if matches:
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[0][2]
    
    return None
```

**Expected match rate**: 70-85%

## Recommended Implementation

### Phase 1: Simple Matching (Quick Win)
Implement Strategy 1 (Organization + Amount + Year):
- Fast to implement
- Good enough for 40-60% of awards
- Provides immediate value

### Phase 2: Enhanced Matching (Better Coverage)
Add Strategy 4 (Hybrid):
- Increase match rate to 70-85%
- Add confidence scoring
- Enable validation

### Phase 3: Manual Review (Complete Coverage)
For unmatched awards:
- Export to CSV for manual review
- Use web interface to NIH Reporter
- Build mapping table for future runs

## Performance Considerations

### API Rate Limits
- NIH API has no documented rate limits
- Observed: ~100 requests/second sustainable
- For 47,050 awards: ~8 minutes with caching

### Caching Strategy
```python
# Cache by (org_name, amount, year) tuple
cache_key = f"{award.firm_name}|{award.award_amount}|{award.award_date.year}"

if cache_key in match_cache:
    return match_cache[cache_key]

result = find_nih_project(award)
match_cache[cache_key] = result
return result
```

### Batch Processing
```python
# Group awards by year for batch API calls
awards_by_year = defaultdict(list)
for award in awards:
    awards_by_year[award.award_date.year].append(award)

# Process year by year
for year, year_awards in awards_by_year.items():
    # Fetch all NIH projects for this year once
    nih_projects = fetch_nih_projects_for_year(year)
    
    # Match locally
    for award in year_awards:
        match = find_best_match(award, nih_projects)
```

## Testing Plan

### Test Set
1. Select 100 random HHS awards
2. Manually find their NIH project numbers
3. Test each matching strategy
4. Measure:
   - Match rate (% found)
   - Accuracy (% correct)
   - False positive rate
   - Performance (time per award)

### Success Criteria
- Match rate: ≥70%
- Accuracy: ≥95% (of matches)
- False positive rate: <5%
- Performance: <100ms per award (cached)

## Conclusion

**Recommended approach**: Start with Strategy 1 (Organization + Amount + Year)
- Simplest to implement
- Provides 40-60% coverage
- Can enhance later with hybrid approach

**Alternative**: If abstracts are reliable, Strategy 2 (Text Similarity) may provide better accuracy

**Long-term**: Build mapping table from successful matches for instant lookup

---

**Next Steps**:
1. Implement Strategy 1
2. Test on 100-award sample
3. Measure match rate and accuracy
4. Decide on enhancement strategy

**Estimated Effort**: 2-4 hours for Strategy 1, 4-8 hours for Strategy 4
