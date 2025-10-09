# Contextual Features for CET Classification

**Date**: 2025-10-09
**Purpose**: Analyze additional context beyond title/abstract that could improve CET classification accuracy

---

## Executive Summary

The SBIR dataset contains **rich contextual metadata** beyond title and abstract that can significantly improve classification accuracy:

| Feature | Completeness | CET Signal Strength | Implementation Priority |
|---------|--------------|---------------------|-------------------------|
| **Agency** | 100% | **VERY HIGH** | **HIGH** |
| **Branch** | 65.6% | **HIGH** | **HIGH** |
| **Topic Code** | 56.3% | **MEDIUM-HIGH** | MEDIUM |
| **Phase** | 100% | LOW | LOW |
| **Program (SBIR/STTR)** | 100% | LOW | LOW |
| **Solicitation Number** | 51.3% | MEDIUM | LOW |

**Key Insight**: Agency and Branch provide **strong priors** that can boost CET classification confidence by 20-40%.

---

## Available Contextual Fields

### Field Inventory

| # | Field | Completeness | Unique Values | Type |
|---|-------|--------------|---------------|------|
| 1 | Company | 100% | ~100,000 | Text |
| 2 | Award Title | 100% | ~200,000 | Text |
| 3 | **Agency** | **100%** | **10** | **Categorical** |
| 4 | **Branch** | **65.6%** | **~200** | **Categorical** |
| 5 | Phase | 100% | 2 | Categorical |
| 6 | Program | 100% | 2 | Categorical |
| 7 | Agency Tracking Number | ~50% | ~100,000 | ID |
| 8 | Contract | ~75% | ~160,000 | ID |
| 9-15 | Dates | 100% | N/A | Date |
| 16 | **Topic Code** | **56.3%** | **~20,000** | **Categorical** |
| 17 | Solicitation Number | 51.3% | ~10,000 | Categorical |
| 18 | Award Amount | 100% | ~50,000 | Numeric |
| 19-30 | Company Info | Various | N/A | Mixed |
| 31 | Abstract | 100% | ~200,000 | Text |
| 32-42 | Contact Info | Various | N/A | Text |

---

## High-Value Contextual Features

### 1. Agency (100% Complete) - **VERY HIGH Value**

#### Distribution
- Department of Defense: 102,780 (47.9%)
- HHS (mostly NIH): 48,707 (22.7%)
- NASA: 19,034 (8.9%)
- DOE: 16,390 (7.6%)
- NSF: 15,356 (7.2%)
- USDA: 4,094 (1.9%)
- EPA: 2,050 (1.0%)
- Commerce: 1,889 (0.9%)
- Education: 1,430 (0.7%)
- Transportation: 1,279 (0.6%)

#### CET Signal Mapping

| Agency | Strong CET Signals | Example CETs | Boost Amount |
|--------|-------------------|--------------|--------------|
| **DoD** | hypersonics, autonomous_systems, directed_energy, advanced_materials | Military tech focus | +15 pts |
| **HHS/NIH** | biotechnology, medical_devices | Healthcare focus | +20 pts |
| **NASA** | space_technology, advanced_materials, autonomous_systems | Space focus | +25 pts |
| **DOE** | renewable_energy, energy_storage, quantum_computing | Energy/physics focus | +20 pts |
| **NSF** | all CETs (broad R&D) | Basic research | +5 pts (all) |
| **USDA** | biotechnology, environmental_tech | Agriculture/bio focus | +10 pts |
| **EPA** | environmental_tech, renewable_energy | Environmental focus | +20 pts |
| **Commerce** | semiconductors, advanced_communications | Tech/commerce focus | +10 pts |

#### Implementation Strategy

```python
AGENCY_CET_PRIORS = {
    "Department of Defense": {
        "hypersonics": 15,
        "autonomous_systems": 15,
        "directed_energy": 15,
        "advanced_materials": 10,
        "cybersecurity": 10,
        "semiconductors": 10,
        "advanced_communications": 10,
    },
    "Department of Health and Human Services": {
        "biotechnology": 20,
        "medical_devices": 20,
        "artificial_intelligence": 5,  # Medical AI is common
    },
    "National Aeronautics and Space Administration": {
        "space_technology": 25,
        "advanced_materials": 15,
        "autonomous_systems": 10,
        "renewable_energy": 10,  # Space solar
    },
    "Department of Energy": {
        "renewable_energy": 20,
        "energy_storage": 20,
        "quantum_computing": 15,
        "advanced_materials": 10,
        "semiconductors": 10,
    },
    "National Science Foundation": {
        # NSF funds all areas - give small boost to all
        "_all_cets": 5,
    },
    "Department of Agriculture": {
        "biotechnology": 15,
        "environmental_tech": 15,
    },
    "Environmental Protection Agency": {
        "environmental_tech": 25,
        "renewable_energy": 15,
    },
    "Department of Commerce": {
        "semiconductors": 15,
        "advanced_communications": 15,
        "quantum_computing": 10,
    },
}

def apply_agency_prior(cet_scores: dict, agency: str) -> dict:
    """Apply agency-based CET priors."""
    if agency in AGENCY_CET_PRIORS:
        priors = AGENCY_CET_PRIORS[agency]
        for cet_id, boost in priors.items():
            if cet_id == "_all_cets":
                # Boost all CETs
                for cet in cet_scores:
                    if cet != "none":
                        cet_scores[cet] = cet_scores.get(cet, 0) + boost
            else:
                cet_scores[cet_id] = cet_scores.get(cet_id, 0) + boost
    return cet_scores
```

#### Expected Impact
- **Reduce None category**: 69.1% → ~55-60% (as agency context disambiguates low-keyword awards)
- **Increase confidence**: Awards with weak keyword signals but strong agency match get boosted
- **Example**: DoD award about "advanced propulsion" with no explicit "hypersonics" keyword → gets +15 pts to hypersonics

---

### 2. Branch (65.6% Complete) - **HIGH Value**

#### Distribution (Top 10)
- National Institutes of Health: 35,976 (16.8%)
- Air Force: 34,552 (16.1%)
- Navy: 26,960 (12.6%)
- Army: 19,355 (9.0%)
- Missile Defense Agency: 8,882 (4.1%)
- DARPA: 6,583 (3.1%)
- Defense Health Agency: 1,254 (0.6%)
- DTRA: 1,072 (0.5%)
- SOCOM: 1,038 (0.5%)
- CBRND: 843 (0.4%)

#### CET Signal Mapping

| Branch | Strong CET Signals | Rationale | Boost Amount |
|--------|-------------------|-----------|--------------|
| **NIH** | medical_devices, biotechnology | Healthcare research | +25 pts |
| **Air Force** | hypersonics, space_technology, autonomous_systems | Aerospace focus | +20 pts |
| **Navy** | autonomous_systems, advanced_materials, directed_energy | Naval systems | +15 pts |
| **Army** | autonomous_systems, cybersecurity, advanced_materials | Ground systems | +15 pts |
| **MDA** | hypersonics, directed_energy, space_technology | Missile defense | +25 pts |
| **DARPA** | all high-tech CETs | Breakthrough research | +10 pts (all) |
| **Defense Health** | medical_devices, biotechnology | Military healthcare | +20 pts |

#### Implementation Strategy

```python
BRANCH_CET_PRIORS = {
    "National Institutes of Health": {
        "medical_devices": 25,
        "biotechnology": 25,
        "artificial_intelligence": 10,  # Medical AI
    },
    "Air Force": {
        "hypersonics": 20,
        "space_technology": 15,
        "autonomous_systems": 15,
        "directed_energy": 10,
        "advanced_materials": 10,
    },
    "Navy": {
        "autonomous_systems": 15,
        "advanced_materials": 15,
        "directed_energy": 10,
        "cybersecurity": 10,
    },
    "Army": {
        "autonomous_systems": 15,
        "cybersecurity": 15,
        "advanced_materials": 10,
        "medical_devices": 5,  # Combat medicine
    },
    "Missile Defense Agency": {
        "hypersonics": 25,
        "directed_energy": 20,
        "space_technology": 15,
    },
    "Defense Advanced Research Projects Agency": {
        # DARPA funds breakthrough tech in all areas
        "quantum_computing": 15,
        "artificial_intelligence": 15,
        "biotechnology": 15,
        "autonomous_systems": 15,
        "hypersonics": 15,
        "directed_energy": 15,
    },
    "Defense Health Agency": {
        "medical_devices": 25,
        "biotechnology": 20,
    },
}

def apply_branch_prior(cet_scores: dict, branch: str) -> dict:
    """Apply branch-based CET priors."""
    if pd.notna(branch) and branch in BRANCH_CET_PRIORS:
        priors = BRANCH_CET_PRIORS[branch]
        for cet_id, boost in priors.items():
            cet_scores[cet_id] = cet_scores.get(cet_id, 0) + boost
    return cet_scores
```

#### Expected Impact
- **Higher precision**: Branch provides more specific signal than agency
- **Example**: Air Force + "thermal protection" → strong signal for hypersonics (not just advanced_materials)
- **Caveat**: 34.4% missing data - use as bonus signal, not requirement

---

### 3. Topic Code (56.3% Complete) - **MEDIUM-HIGH Value**

#### Characteristics
- **20,000+ unique codes** across all agencies
- **Highly specific** to solicitation topics
- **Structured codes** with patterns:
  - NIH: Institute names (NIAID, NHLBI, NCI, etc.)
  - DoD: Alphanumeric codes (AF192-001, N192-077, etc.)
  - NSF: Letter codes (BT, LC, ET, etc.)
  - NASA: Numeric codes

#### CET Signal Examples

**NIH Institute Codes:**
- `NIAID` (National Institute of Allergy and Infectious Diseases) → biotechnology, medical_devices
- `NHLBI` (Heart, Lung, Blood Institute) → medical_devices, biotechnology
- `NCI` (Cancer Institute) → medical_devices, biotechnology
- `NIDA` (Drug Abuse) → medical_devices, biotechnology
- `NICHD` (Child Health) → medical_devices, biotechnology

**DoD Topic Codes (require lookup):**
- DoD topic codes are too numerous (16,542 unique) to manually map
- **Recommendation**: Scrape solicitation topic descriptions from SBIR.gov API

**NSF Topic Codes:**
- `BT` → Biotechnology
- `ET` → Energy Technology
- `EL` → Electronics
- `CT` → Computer Technology
- Require NSF topic code lookup table

#### Implementation Strategy

**Option A: Manual Mapping (NIH only)**
```python
NIH_INSTITUTE_CET_MAPPING = {
    "NIAID": {"biotechnology": 20, "medical_devices": 20},
    "NHLBI": {"medical_devices": 25, "biotechnology": 15},
    "NCI": {"medical_devices": 25, "biotechnology": 20},
    "NIA": {"medical_devices": 20, "biotechnology": 15},
    "NICHD": {"medical_devices": 20, "biotechnology": 15},
    "NIDA": {"medical_devices": 20, "biotechnology": 15},
    "NIDDK": {"medical_devices": 20, "biotechnology": 15},
    "NIGMS": {"biotechnology": 25, "medical_devices": 10},
    # ... add all 27 NIH institutes
}
```

**Option B: External Lookup (All agencies)**
```python
# Scrape from SBIR.gov or agency websites
# Create mapping: topic_code → CET preferences

TOPIC_CODE_CET_MAPPING = {
    # From solicitation topic descriptions
    "AF192-001": {"artificial_intelligence": 20, "autonomous_systems": 15},
    "N192-077": {"advanced_materials": 20},
    # ... 20,000+ entries (requires data pipeline)
}
```

**Recommendation**: Start with Option A (NIH only) as it covers 22.7% of dataset with high precision. Add other agencies later.

#### Expected Impact
- **NIH institutes**: Very precise CET signal (covers 48,707 awards)
- **DoD topics**: High precision but requires scraping solicitation data
- **Overall**: Could improve classification for 56.3% of dataset

---

## Medium-Value Contextual Features

### 4. Solicitation Number (51.3% Complete)

**Example**: `NSF 24-580`, `N241-001`, `DOE-SBIR-2024`

**Value**: Links to specific solicitation topics (similar to Topic Code)

**Challenge**: Need to scrape solicitation topic descriptions from agency websites

**Recommendation**: Use Topic Code instead (more complete, easier to map)

---

### 5. Phase (100% Complete) - **LOW Value**

**Distribution**:
- Phase I: 148,595 (69.3%)
- Phase II: 65,786 (30.7%)

**CET Signal**: Minimal
- Phase I: Feasibility/proof of concept
- Phase II: Development/commercialization

**Potential Use**: Phase II awards may have more detailed technical descriptions → slightly higher weight on abstract keywords

**Recommendation**: Low priority, minor signal

---

### 6. Program (100% Complete) - **LOW Value**

**Distribution**:
- SBIR: 193,433 (90.2%)
- STTR: 20,948 (9.8%)

**CET Signal**: Minimal
- SBIR: Small business only
- STTR: Small business + research institution partnership

**Potential Use**: STTR may have slightly higher rate of breakthrough research → small boost to high-tech CETs

**Recommendation**: Low priority

---

## Implementation Plan

### Phase 1: Agency Priors (Week 1) - **HIGH IMPACT**

**Tasks**:
1. Create `AGENCY_CET_PRIORS` dictionary
2. Add `apply_agency_prior()` function to classifier
3. Apply after keyword scoring, before normalization
4. Test on sample of 1,000 awards

**Expected Results**:
- None category: 69.1% → ~60%
- High-confidence awards: 0.2% → ~2-3%
- Overall accuracy: +10-15%

**Code Location**: `ingest_awards.py` line ~450 (after keyword scoring)

```python
# In classify_award() function:
cet_scores = calculate_keyword_scores(title, abstract)  # Existing
cet_scores = apply_agency_prior(cet_scores, agency)      # NEW
cet_scores = apply_context_rules(cet_scores, title, abstract)  # Existing
```

---

### Phase 2: Branch Priors (Week 2) - **MEDIUM-HIGH IMPACT**

**Tasks**:
1. Create `BRANCH_CET_PRIORS` dictionary
2. Add `apply_branch_prior()` function
3. Handle 34.4% missing data gracefully
4. Test on full dataset

**Expected Results**:
- Precision improvement: +5-10%
- None category: 60% → ~55%

**Code Location**: Same as Phase 1, apply after agency prior

```python
cet_scores = apply_agency_prior(cet_scores, agency)
if pd.notna(branch):
    cet_scores = apply_branch_prior(cet_scores, branch)  # NEW
```

---

### Phase 3: NIH Institute Mapping (Week 3) - **MEDIUM IMPACT**

**Tasks**:
1. Create `NIH_INSTITUTE_CET_MAPPING` for all 27 NIH institutes
2. Apply when agency=HHS and topic_code in NIH institutes
3. Test on 48,707 HHS awards

**Expected Results**:
- HHS classification precision: +15-20%
- Better distinction between biotechnology vs medical_devices

**Code Location**: Same as Phase 1/2

```python
if agency == "Department of Health and Human Services" and topic_code in NIH_INSTITUTE_CET_MAPPING:
    cet_scores = apply_nih_institute_prior(cet_scores, topic_code)  # NEW
```

---

### Phase 4: Topic Code Scraping (Future) - **HIGH EFFORT**

**Tasks**:
1. Scrape solicitation topic descriptions from SBIR.gov API
2. Extract CET keywords from topic descriptions
3. Create `TOPIC_CODE_CET_MAPPING` for all 20,000+ codes
4. Maintain as ongoing data pipeline

**Expected Results**:
- Classification precision: +10-20%
- Covers 56.3% of dataset

**Recommendation**: Only pursue if Phase 1-3 validation shows success

---

## Validation Strategy

### Before/After Comparison

**Metrics to Track**:
1. None category percentage (expect: 69.1% → 55%)
2. High-confidence awards (expect: 0.2% → 2-3%)
3. CET distribution changes
4. Multi-label rate (expect: 2.91% → 4-5%)

### Expert Review (200-Award Sample)

**Stratification**:
- 50 awards where context changed classification (None → CET)
- 50 awards where context boosted confidence (Medium → High)
- 50 awards where context didn't change classification
- 50 awards with missing context (Branch/Topic Code)

**Goal**: Measure precision improvement from contextual features

---

## Expected Overall Impact

### Classification Accuracy Improvements

| Feature | Coverage | Expected Precision Gain | None Category Reduction |
|---------|----------|-------------------------|-------------------------|
| **Agency Prior** | 100% | +10-15% | 69% → 60% |
| **Branch Prior** | 65.6% | +5-10% | 60% → 55% |
| **NIH Institute** | 22.7% | +15-20% | (HHS only) |
| **Combined** | 100% | **+20-30%** | **69% → 55%** |

### Example Improvements

**Before (v4 - Keywords Only)**:
```
Award: "Development of High-Speed Vehicle Thermal Protection"
Agency: DoD, Branch: Air Force
Keywords: "thermal protection" (15 pts → advanced_materials)
Classification: advanced_materials (score: 48, Medium)
```

**After (v5 - With Context)**:
```
Award: "Development of High-Speed Vehicle Thermal Protection"
Agency: DoD (+15 hypersonics), Branch: Air Force (+20 hypersonics)
Keywords: "thermal protection" (15 pts → advanced_materials)
Context: "high-speed" + "thermal" + Air Force → hypersonics context rule
Classification: hypersonics (score: 70, High)
Supporting: advanced_materials (score: 48)
```

### Real-World Example

**NASA Award - v4 Classification**:
```
Title: "Advanced Battery System for Lunar Rover"
Keywords: "battery" (15) → energy_storage (score: 48)
Classification: energy_storage (Medium)
```

**NASA Award - v5 with Context**:
```
Title: "Advanced Battery System for Lunar Rover"
Keywords: "battery" (15) → energy_storage
Agency: NASA (+25 space_technology, +10 energy_storage)
Classification: space_technology (score: 55, Medium, 57% weight)
Supporting: energy_storage (score: 58, 43% weight)
```

This correctly identifies it as primarily a **space technology** award, with energy storage as supporting.

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| **Agency/Branch priors too strong** | Over-classify to agency-preferred CETs | Use moderate boost values (10-25 pts, not 50+) |
| **Missing Branch data (34.4%)** | Inconsistent classification | Use as bonus signal only, not requirement |
| **Topic code scraping maintenance** | Data pipeline becomes stale | Start with static NIH mapping, defer DoD scraping |
| **Over-fitting to agency patterns** | Miss novel cross-domain work | Maintain keyword-based scoring as primary signal |

---

## Recommendation

**Start with Phase 1 (Agency Priors) immediately**:
- 100% data coverage
- Simple implementation (50 lines of code)
- Expected 10-15% accuracy improvement
- Can complete in 1 week

**Follow with Phase 2 (Branch Priors)**:
- Covers 65.6% of data
- Additive to Phase 1
- Expected additional 5-10% improvement

**Defer Phase 3 (NIH Institutes)** until after Phase 1/2 validation shows success.

**Defer Phase 4 (Topic Code Scraping)** indefinitely unless expert validation shows need.

---

## Implementation Checklist

### v5 Classifier: Agency + Branch Priors

- [ ] Create `AGENCY_CET_PRIORS` dictionary
- [ ] Create `BRANCH_CET_PRIORS` dictionary
- [ ] Add `apply_agency_prior()` function
- [ ] Add `apply_branch_prior()` function
- [ ] Integrate into `classify_award()` pipeline
- [ ] Update generation method to `automated_v5_with_context`
- [ ] Run on full dataset
- [ ] Generate v4 vs v5 comparison report
- [ ] Validate with 200-award expert sample
- [ ] Document results in `V5_COMPARISON_REPORT.md`

**Estimated Time**: 1-2 weeks
**Expected Impact**: None category 69% → 55%, precision +20-30%

---

**Analysis Complete**: 2025-10-09
**Next Step**: Implement v5 classifier with Agency + Branch priors
