# Full Dataset Classification Analysis

**Date**: 2025-10-08
**Dataset**: award_data-3.csv (complete file)
**Classifier**: TF-IDF-based keyword matching

---

## Executive Summary

Successfully classified **151,773 unique SBIR awards** totaling **$64.5 billion** in funding across **20 Critical and Emerging Technology (CET) areas** using the current TF-IDF keyword-based classifier.

### Key Findings

✅ **100% automation rate** - All awards automatically classified
⚠️ **Binary score distribution** - Only 2 scores (50 and 100) produced
💡 **AI dominates** - 67.8% of awards classified as Artificial Intelligence
🎯 **DoD leads funding** - 50.8% of awards from Department of Defense

---

## Dataset Overview

| Metric | Value |
|--------|-------|
| **Total Awards Classified** | 151,773 |
| **Original CSV Rows** | 214,381 |
| **Duplicates Removed** | 62,608 (29.2%) |
| **Total Funding** | $64.50B |
| **Average Award** | $425.0K |
| **Median Award** | $150.0K |
| **Date Range** | FY 1983 - FY 2025 |
| **Agencies Covered** | 10+ federal agencies |

---

## Classification Results

### Automation Performance

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| **Automation Rate** | ≥95% | 100.0% | ✅ EXCEEDED |
| **Awards Classified** | - | 151,773 | ✅ COMPLETE |
| **Manual Review Needed** | - | 0 | ✅ NONE |

### Score Distribution ⚠️ KEY FINDING

The current keyword-based classifier produces **only 2 distinct scores**:

| Score | Classification | Count | Percentage |
|-------|----------------|-------|------------|
| **50** | Medium (40-69) | 113,023 | 74.5% |
| **100** | High (≥70) | 38,750 | 25.5% |

**Statistical Summary:**
- Min Score: 50.0
- Max Score: 100.0
- Mean Score: 62.8
- Median Score: 50.0
- Std Deviation: 21.8

**Why This Matters:**
- Current scoring logic: `normalized_score = min(100, keyword_count * 10 * 5)`
- Produces discrete values based on keyword matches
- **No awards scored in 0-40 range** (all match at least one keyword)
- **No nuanced 40-100 scoring** (binary high/low only)
- Deep learning models would produce continuous 0-100 scores with better discrimination

---

## Top 10 CET Areas by Award Count

| Rank | CET Area | Awards | % | Funding |
|------|----------|--------|---|---------|
| 1 | **Artificial Intelligence** | 102,870 | 67.8% | $45.0B |
| 2 | Advanced Manufacturing | 19,937 | 13.1% | $7.3B |
| 3 | Space Technology | 7,706 | 5.1% | $3.2B |
| 4 | Medical Devices | 3,413 | 2.2% | $1.9B |
| 5 | Semiconductors and Microelectronics | 3,012 | 2.0% | $1.2B |
| 6 | Autonomous Systems | 2,841 | 1.9% | $1.3B |
| 7 | Quantum Computing | 2,437 | 1.6% | $931M |
| 8 | Advanced Materials | 2,232 | 1.5% | $702M |
| 9 | Renewable Energy | 1,791 | 1.2% | $646M |
| 10 | Biotechnology | 1,749 | 1.2% | $804M |

### Key Observations

⚠️ **AI Over-Classification**: 67.8% of all awards classified as AI suggests keyword overlap:
- Many technical fields use "machine learning", "neural network", "ai" in descriptions
- Keyword matching captures these broadly without contextual understanding
- Deep learning models could better distinguish:
  - Core AI research vs. AI-enabled applications
  - Primary focus vs. secondary methodology

💡 **Long Tail Distribution**: Top 2 CET areas account for 80.9% of awards
- Remaining 18 CET areas share only 19.1%
- May indicate keyword bias rather than true distribution

---

## Top 10 Agencies by Award Count

| Rank | Agency | Awards | % | Funding |
|------|--------|--------|---|---------|
| 1 | **Department of Defense** | 77,062 | 50.8% | $33.1B |
| 2 | Department of Health and Human Services | 33,670 | 22.2% | $19.3B |
| 3 | NASA | 13,060 | 8.6% | $3.6B |
| 4 | National Science Foundation | 11,409 | 7.5% | $3.2B |
| 5 | Department of Energy | 9,135 | 6.0% | $3.7B |
| 6 | Department of Agriculture | 2,599 | 1.7% | $493M |
| 7 | Environmental Protection Agency | 1,270 | 0.8% | $157M |
| 8 | Department of Homeland Security | 1,186 | 0.8% | $377M |
| 9 | Department of Commerce | 1,151 | 0.8% | $223M |
| 10 | Department of Transportation | 671 | 0.4% | $191M |

**Insights:**
- DoD dominates both count (50.8%) and funding ($33.1B)
- HHS second largest despite lower average award size
- Top 5 agencies account for 95.1% of all awards

---

## Fiscal Year Distribution (Last 15 Years)

| Fiscal Year | Awards | Funding |
|-------------|--------|---------|
| FY 2025 | 286 | $172M |
| FY 2024 | 6,359 | $4,290M |
| FY 2023 | 6,139 | $4,429M |
| FY 2022 | 6,439 | $4,353M |
| FY 2021 | 6,627 | $3,698M |
| FY 2020 | 7,120 | $3,851M |
| FY 2019 | 6,795 | $3,699M |
| FY 2018 | 5,428 | $2,749M |
| FY 2017 | 5,796 | $3,106M |
| FY 2016 | 5,116 | $2,539M |
| FY 2015 | 4,981 | $2,427M |
| FY 2014 | 5,026 | $2,220M |
| FY 2013 | 5,035 | $2,072M |
| FY 2012 | 5,486 | $2,230M |
| FY 2011 | 5,947 | $2,285M |

**Trends:**
- Steady ~6,000 awards per year (2020-2024)
- FY 2025 incomplete (only 286 awards as of data extract)
- Funding per award increasing over time

---

## Phase Distribution

| Phase | Awards | % | Funding | Avg Award |
|-------|--------|---|---------|-----------|
| **Phase I** | 103,921 | 68.5% | $15.0B | $145K |
| **Phase II** | 47,852 | 31.5% | $49.5B | $1,034K |

**Insights:**
- Phase I outnumbers Phase II 2.2:1 (expected funnel)
- Phase II awards 7x larger on average ($1.03M vs $145K)
- Phase II represents 76.7% of total funding despite 31.5% of awards

---

## Top 10 States by Award Count

| Rank | State | Awards | % | Funding |
|------|-------|--------|---|---------|
| 1 | **California** | 30,179 | 19.9% | $13.1B |
| 2 | Massachusetts | 17,601 | 11.6% | $7.6B |
| 3 | Virginia | 9,258 | 6.1% | $3.9B |
| 4 | Colorado | 7,222 | 4.8% | $2.9B |
| 5 | Texas | 7,095 | 4.7% | $2.8B |
| 6 | Maryland | 6,961 | 4.6% | $2.9B |
| 7 | New York | 6,600 | 4.3% | $2.9B |
| 8 | Ohio | 6,137 | 4.0% | $2.5B |
| 9 | Pennsylvania | 5,668 | 3.7% | $2.6B |
| 10 | Florida | 4,436 | 2.9% | $1.9B |

**Geographic Insights:**
- California dominates (19.9% of awards, $13.1B)
- Top 10 states account for 67.5% of all awards
- Strong correlation with tech hubs and defense contractors

---

## Comparison: Sample vs. Full Dataset

| Metric | Sample (1,000 rows) | Full Dataset (151,773) | Change |
|--------|---------------------|------------------------|--------|
| **Awards Classified** | 997 | 151,773 | 152x |
| **Total Funding** | $742M | $64,500M | 87x |
| **AI Classification %** | 78.3% | 67.8% | -10.5% |
| **Medium Classification %** | 71.4% | 74.5% | +3.1% |
| **High Classification %** | 28.6% | 25.5% | -3.1% |

**Why Differences?**
- Sample had selection bias toward recent awards (more AI keywords)
- Full dataset includes historical awards (1983-2025) with different terminology
- Score distribution remarkably stable (74.5% vs 71.4% Medium)

---

## Limitations of Current TF-IDF Approach

### 1. Binary Scoring (Critical Issue)
❌ **Only 2 scores produced**: 50 and 100
- No granularity for prioritization
- Cannot distinguish "somewhat applicable" from "highly applicable"
- Makes portfolio analysis less actionable

### 2. Keyword Over-Matching
❌ **67.8% classified as AI**: Likely over-inclusive
- Terms like "machine learning", "neural network" appear in many contexts
- Awards using AI as a tool (not focus) get AI classification
- Cross-disciplinary work mislabeled

### 3. Lack of Context Understanding
❌ **Keyword presence ≠ semantic meaning**
- "Bank" in financial vs. river context
- "Quantum" in quantum computing vs. quantum chemistry
- Abstract mentions don't imply primary focus

### 4. Historical Terminology Gaps
❌ **Older awards use different language**
- Pre-2010 awards may not use "AI" terminology
- Concepts described differently over time
- Misses semantic equivalents ("pattern recognition" vs "machine learning")

### 5. No Confidence Scores
❌ **All classifications appear equally confident**
- Cannot identify borderline cases for manual review
- No ranking within classification bands
- Manual review queue stays empty (0 items)

---

## Deep Learning Would Improve:

### 1. Continuous Scoring ✅
- True 0-100 scale with nuanced differentiation
- Better portfolio prioritization
- Confidence intervals for each classification

### 2. Semantic Understanding ✅
- Context-aware classification
- Distinguishes primary focus from methodology
- Handles synonyms and evolving terminology

### 3. Multi-label Classification ✅
- Awards can span multiple CET areas naturally
- Weighted contributions rather than forced primary selection
- Better represents interdisciplinary research

### 4. Confidence Estimation ✅
- Identifies low-confidence cases for manual review
- Enables active learning (human feedback loop)
- Populates review queue intelligently

### 5. Historical Adaptation ✅
- Transfer learning handles terminology evolution
- Pre-trained on scientific literature
- Generalizes beyond keyword matching

---

## Recommendations

### Immediate Actions

1. **Evaluate Current System**
   - Create 200-award validation set with expert labels
   - Measure precision/recall per CET area
   - Quantify over-classification rate (especially AI)

2. **Score Distribution Analysis**
   - Investigate why 74.5% scored exactly 50
   - Examine awards with score 100 - truly high applicability?
   - Consider recalibrating keyword weights

### Short-term Improvements (Without Deep Learning)

1. **Enhanced Keyword Matching**
   - Add negative keywords (exclude false positives)
   - Weight keywords by importance (core vs. peripheral terms)
   - Implement hierarchical matching (must match N of M core terms)

2. **Scoring Refinement**
   - Use continuous scoring: `score = (keyword_matches / max_possible) * 100`
   - Add context bonus (title match > abstract match)
   - Implement decay for multiple weak matches vs. single strong match

3. **Multi-label Support**
   - Allow top 3 CET classifications with weights
   - Report CET distribution rather than forced primary
   - Better represents interdisciplinary awards

### Long-term (Deep Learning Evaluation)

1. **Baseline Validation** (Week 1)
   - Create expert-labeled validation set (200 awards)
   - Measure current TF-IDF performance
   - Document error patterns

2. **Prototype Evaluation** (Week 2)
   - Test Sentence Transformers (zero-shot)
   - Compare accuracy vs. TF-IDF on validation set
   - Measure inference latency

3. **Go/No-Go Decision** (Week 3)
   - If accuracy gain <5%: Stick with improved TF-IDF
   - If accuracy gain 5-10%: Consider hybrid approach
   - If accuracy gain >10%: Invest in SciBERT training

---

## Success Criteria Met

| Criterion | Target | Actual | Status |
|-----------|--------|--------|--------|
| SC-001: Automated classification | ≥95% | 100% | ✅ EXCEEDED |
| SC-002: Summary generation | ≤3 min | < 1 min | ✅ EXCEEDED |
| SC-003: Award drill-down | ≤5 min | < 1 min | ✅ EXCEEDED |
| SC-004: Reviewer agreement | ≥85% | Not measured | ⚠️ PENDING |
| SC-005: Export completion | ≤10 min | Untested | ⚠️ PENDING |
| SC-006: Scoring latency | ≤500ms/100 | < 200ms | ✅ EXCEEDED |
| SC-007: Ingestion time | ≤2 hours | ~3 min | ✅ EXCEEDED |

---

## Next Steps

### Priority 1: Validate Classification Quality
```bash
# Create validation dataset
python -m sbir_cet_classifier.evaluation.create_validation_sample --size 200

# Get expert labels (manual review)
# ...

# Measure agreement
python -m sbir_cet_classifier.evaluation.reviewer_agreement \
    --validation-file artifacts/validation_sample.csv
```

### Priority 2: Run Tests on Full Dataset
```bash
# Verify tests still pass with large dataset
pytest tests/integration/ -v --tb=short

# Generate performance metrics
python -m sbir_cet_classifier.evaluation.benchmark \
    --awards 151773 --output artifacts/benchmark_full.json
```

### Priority 3: Export Validation
```bash
# Test export with full dataset
python -m sbir_cet_classifier.cli.app export create \
    --fiscal-year-start 1983 --fiscal-year-end 2025 \
    --format csv --output exports/full_dataset.csv

# Verify SC-005 (≤10 min for 50k awards)
```

---

## Conclusion

The SBIR CET Classifier successfully processed **151,773 awards** with **100% automation**, but reveals important limitations:

✅ **Strengths:**
- Fast (3 minutes for full dataset)
- 100% automation rate
- No infrastructure requirements
- Reproducible and interpretable

⚠️ **Weaknesses:**
- Binary scoring (only 50 or 100) lacks nuance
- 67.8% classified as AI suggests over-matching
- No confidence scores for manual review prioritization
- Keyword approach misses semantic context

**Verdict:** Current system meets automation targets but **validation with expert labels is critical** before production use. Deep learning evaluation recommended only if validation reveals <85% agreement rate.

---

**Report Generated**: 2025-10-08
**Dataset**: 151,773 awards, $64.5B, FY 1983-2025
**Classifier**: TF-IDF keyword matching (version 1.0)
