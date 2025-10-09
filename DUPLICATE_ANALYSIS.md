# Duplicate Analysis: Why 62,608 Awards Were Dropped

**Investigation Date**: 2025-10-08
**Issue**: 29.2% of CSV rows (62,608 out of 214,381) were dropped as duplicates

---

## Root Cause: Aggressive Deduplication Logic

The ingestion script used this logic:
```python
df = df.drop_duplicates(subset=["award_id"], keep="first")
```

This treated **all rows with NULL `award_id` as duplicates of each other**, which is incorrect.

---

## Breakdown of the 62,608 "Duplicates"

### 1. NULL Contract IDs: 52,115 rows (83% of duplicates)

**The Problem:**
- 52,115 rows (24.3% of CSV) have NULL/missing Contract numbers
- `drop_duplicates()` treated all NULLs as identical values
- Only the **first NULL row was kept**, all others dropped
- These are **legitimate unique awards** with missing metadata

**Distribution by Agency:**
| Agency | NULL Contracts | % of NULLs |
|--------|----------------|------------|
| Department of Defense | 23,590 | 45.3% |
| HHS | 12,897 | 24.7% |
| NASA | 4,861 | 9.3% |
| NSF | 3,401 | 6.5% |
| DOE | 3,141 | 6.0% |

**Time Period:**
- Concentrated in 1990s-early 2000s (FY 1999-2002 peak)
- Likely data quality issues in older SBIR.gov records
- Contract tracking improved over time

**Example Dropped Award:**
```
Company: Samraksh Company, The
Title: Customizing Security for Diverse IoT Endpoints
Agency: Department of Defense
Year: 2016
Amount: $149,988
Contract: NULL ❌ (Dropped as duplicate!)
```

### 2. Legitimate Duplicate Contract IDs: 10,494 rows (17% of duplicates)

**The Problem:**
- Some contract numbers genuinely appear multiple times
- These may be legitimate duplicates OR data quality issues

**Top Example: "NAS 96-1"**
- Appears **348 times** in the CSV
- Each occurrence has:
  - Different company name
  - Different award title
  - Different amount
  - Different tracking number
- **Conclusion**: Data entry error or placeholder value

**Other Examples:**
- "PHS2001-2": 145 occurrences
- "DE-FG02-08ER86334": 26 occurrences
- Various DoD contracts: 10 occurrences each

**Legitimate Cases:**
Some awards may have amendments, modifications, or multi-year phases that generate multiple CSV rows with the same contract number but different:
- Award dates
- Award amounts (incremental funding)
- Phase designations

---

## Impact Analysis

### Awards Lost

| Category | Rows in CSV | After Deduplication | Lost |
|----------|-------------|---------------------|------|
| **NULL Contracts** | 52,115 | 1 | 52,114 (99.998%) |
| **Valid Duplicates** | 162,266 | 151,772 | 10,494 (6.5%) |
| **Total** | 214,381 | 151,773 | 62,608 (29.2%) |

### Funding Lost

Estimated **$15-25 billion** in awards excluded from analysis:
- 52,114 awards with NULL contracts
- Average award ~$425K
- Total: ~$22B (rough estimate)

### Agency Impact

Agencies most affected by NULL contract drops:
1. **DoD**: Lost 23,590 awards
2. **HHS**: Lost 12,897 awards
3. **NASA**: Lost 4,861 awards

---

## Why This Happened

### 1. Pandas `drop_duplicates()` Behavior

```python
import pandas as pd
df = pd.DataFrame({'id': [None, None, 'A', 'A'], 'value': [1, 2, 3, 4]})
df.drop_duplicates(subset=['id'], keep='first')
```

Result:
```
   id  value
0  NaN     1   ← First NULL kept
2   A      3   ← First 'A' kept
```

**Both NULL rows are treated as duplicates!** This is standard pandas behavior but wrong for our use case.

### 2. Missing Composite Key

The script should have used a **composite key** for deduplication:
- Company + Award Title + Award Date + Amount
- OR: Generate synthetic ID for NULL contracts

---

## Recommended Fixes

### Option 1: Generate Synthetic IDs for NULLs (Recommended)

```python
import hashlib

def generate_award_id(row):
    """Generate unique ID from award attributes if contract is missing."""
    if pd.notna(row['award_id']) and row['award_id'] != '':
        return row['award_id']

    # Create composite key from available fields
    composite = f"{row['firm_name']}|{row['title']}|{row['award_date']}|{row['award_amount']}|{row['agency']}"
    return f"SYNTH-{hashlib.md5(composite.encode()).hexdigest()[:12]}"

df['award_id'] = df.apply(generate_award_id, axis=1)
df = df.drop_duplicates(subset=['award_id'], keep='first')
```

**Advantages:**
- Preserves all 52,114 awards with NULL contracts
- Each unique award gets unique ID
- Still removes true duplicates

### Option 2: Multi-Column Deduplication

```python
# Use multiple columns to identify duplicates
df = df.drop_duplicates(
    subset=['firm_name', 'title', 'award_date', 'award_amount', 'agency'],
    keep='first'
)
```

**Advantages:**
- No synthetic IDs needed
- Identifies true duplicates even without contract number

**Disadvantages:**
- Slight variations in company name would create duplicates
- Awards with identical amounts on same day might be falsely merged

### Option 3: Conditional Deduplication

```python
# Only deduplicate rows with valid contract IDs
df_with_contract = df[df['award_id'].notna()]
df_without_contract = df[df['award_id'].isna()]

df_with_contract_dedup = df_with_contract.drop_duplicates(subset=['award_id'], keep='first')
# Don't deduplicate NULL contracts - keep all

df = pd.concat([df_with_contract_dedup, df_without_contract])
```

**Advantages:**
- Preserves all NULL contract awards
- Only deduplicates where we have reliable key

**Disadvantages:**
- May retain some true duplicates among NULL contracts

---

## Investigation of "NAS 96-1" (348 occurrences)

This contract number appears 348 times with completely different awards. Examples:

| Company | Award Title | Amount | Agency Tracking |
|---------|-------------|--------|-----------------|
| Astral Technology Unlimited | Thin Film Coating To Protect FEP Teflon... | $70,000 | 39858 |
| EPITAXIAL LABORATORY INC | New Materials For High Performance Sensors... | $69,846 | 39934 |
| FERMIONICS CORP | Optoelectronic Microwave Oscillator | $69,499 | 39941 |

**Conclusion:** "NAS 96-1" is clearly a **placeholder or data entry error**, not a real contract number. These should NOT be deduplicated.

**Recommendation:** Flag suspicious contract patterns:
- Contract IDs appearing >100 times
- Generic patterns like "NAS 96-1", "PHS2001-2"
- Mark these for synthetic ID generation

---

## Comparison: With vs. Without Aggressive Deduplication

| Metric | Current (Aggressive) | Should Be (Fixed) | Difference |
|--------|----------------------|-------------------|------------|
| **Awards Analyzed** | 151,773 | ~203,000 | +51,227 |
| **Total Funding** | $64.5B | ~$85B | +$20.5B |
| **NULL Contract Awards** | 1 | 52,115 | +52,114 |
| **Data Completeness** | 70.8% | 94.7% | +23.9% |

---

## Action Items

### Immediate (Priority 1)

1. **Fix deduplication logic** in `ingest_awards.py`:
   - Implement Option 1 (synthetic IDs) or Option 3 (conditional dedup)
   - Test on sample data first

2. **Re-run ingestion** with fixed logic:
   ```bash
   python ingest_awards.py
   ```

3. **Validate results**:
   - Should have ~203,000 awards (not 151,773)
   - Check that NULL contract awards are preserved
   - Verify no true duplicates remain

### Short-term (Priority 2)

4. **Flag suspicious contracts**:
   - Identify contract IDs appearing >50 times
   - Manual review or automated pattern detection
   - Document known placeholders

5. **Update documentation**:
   - Add data quality notes to README
   - Document deduplication strategy
   - Explain synthetic ID generation

### Long-term (Priority 3)

6. **Data quality analysis**:
   - Investigate why so many NULL contracts (especially pre-2005)
   - Contact SBIR.gov data team if possible
   - Consider backfilling missing contracts from agency sources

7. **Multi-award tracking**:
   - Identify legitimate multi-row awards (amendments, phases)
   - Link related awards (Phase I → Phase II)
   - Track total funding across award lifecycle

---

## Conclusion

**The 62,608 "duplicates" are NOT all duplicates:**

✅ **52,114 awards** (83%) have NULL contracts and should be KEPT
❌ **10,494 awards** (17%) have legitimate duplicate contracts and need investigation

**Root cause:** `drop_duplicates()` treating all NULL values as identical.

**Fix:** Generate synthetic IDs for NULL contracts OR use multi-column deduplication.

**Impact of fix:** Increase dataset from 151,773 → ~203,000 awards (+33.8%)

---

**Investigation by**: Claude Code
**Date**: 2025-10-08
**Status**: ⚠️ Fix Required Before Production Use
