# YAML Configuration Scope

**Date**: 2025-10-10  
**Purpose**: Externalize taxonomy and classification parameters for easy updates

## Overview

Move hardcoded configuration from Python files to YAML for:
1. **CET Taxonomy** - Categories, definitions, hierarchies
2. **Classification Parameters** - Model hyperparameters, thresholds
3. **Enrichment Mappings** - Topic codes, agency focus areas
4. **Stop Words** - Domain-specific terms to filter

## Current State

### 1. CET Taxonomy
**Location**: `data/taxonomy/cet_taxonomy_v1.csv`  
**Format**: CSV with 21 rows, 8 columns  
**Fields**: `cet_id`, `name`, `definition`, `parent_cet_id`, `version`, `effective_date`, `retired_date`, `status`

**Issues**:
- CSV is hard to edit (no comments, no nesting)
- Version management is manual
- No validation of parent relationships
- Definitions are single-line (hard to read long text)

### 2. Classification Parameters
**Location**: `src/sbir_cet_classifier/models/applicability.py`  
**Hardcoded Values**:
```python
# TF-IDF parameters
ngram_range=(1, 3)
max_features=50000
min_df=2
max_df=0.95

# Feature selection
k=20000  # SelectKBest

# Logistic regression
max_iter=500
solver="lbfgs"
n_jobs=-1

# Classification bands
"High": (70, 100)
"Medium": (40, 69)
"Low": (0, 39)

# Stop words (28 terms)
SBIR_STOP_WORDS = ["phase", "sbir", "sttr", ...]
```

**Issues**:
- Requires code changes to tune parameters
- No A/B testing without code branches
- Hard to document parameter rationale

### 3. Enrichment Mappings
**Location**: `src/sbir_cet_classifier/features/fallback_enrichment.py`  
**Hardcoded Values**:
```python
# Topic domains (10 mappings)
TOPIC_DOMAINS = {
    "AI": ("Artificial Intelligence", ["machine learning", ...]),
    "BT": ("Biotechnology", ["biotechnology", ...]),
    ...
}

# Agency focus (9 agencies)
AGENCY_FOCUS = {
    "NSF": "fundamental research and technology development",
    "DOD": "defense and national security applications",
    ...
}
```

**Issues**:
- New agencies require code changes
- Topic codes are NSF-specific (other agencies differ)
- No way to add custom mappings per deployment

## Proposed YAML Structure

### File: `config/taxonomy.yaml`

```yaml
version: "NSTC-2025Q1"
effective_date: "2025-01-01"
status: active

categories:
  - id: artificial_intelligence
    name: Artificial Intelligence
    definition: |
      AI and machine learning technologies including neural networks, 
      deep learning, and computer vision
    parent: null
    keywords:
      - machine learning
      - neural networks
      - deep learning
      - computer vision
      - natural language processing
    
  - id: quantum_computing
    name: Quantum Computing
    definition: |
      Quantum information science including quantum computing, 
      quantum sensing, and quantum communications
    parent: null
    keywords:
      - quantum computing
      - quantum algorithms
      - quantum error correction
    
  - id: quantum_sensing
    name: Quantum Sensing
    definition: Quantum-based sensing and measurement technologies
    parent: quantum_computing
    keywords:
      - quantum sensors
      - quantum metrology
      - atomic clocks

  # ... 18 more categories
```

**Benefits**:
- Multi-line definitions (readable)
- Comments for rationale
- Keywords embedded with category
- Parent relationships explicit
- Version tracking built-in

---

### File: `config/classification.yaml`

```yaml
version: "1.0.0"
description: Classification model hyperparameters

vectorizer:
  type: TfidfVectorizer
  ngram_range: [1, 3]  # Unigrams, bigrams, trigrams
  max_features: 50000
  min_df: 2  # Ignore terms in <2 documents
  max_df: 0.95  # Ignore terms in >95% of documents
  sublinear_tf: false
  
feature_selection:
  enabled: true
  method: chi2
  k: 20000  # Top 20k features
  
classifier:
  type: LogisticRegression
  max_iter: 500
  solver: lbfgs
  n_jobs: -1  # Use all CPU cores
  class_weight: balanced  # Handle imbalanced classes
  
calibration:
  enabled: true
  method: sigmoid
  cv: 3  # 3-fold cross-validation
  min_samples_per_class: 3
  
scoring:
  bands:
    high:
      min: 70
      max: 100
      label: High
    medium:
      min: 40
      max: 69
      label: Medium
    low:
      min: 0
      max: 39
      label: Low
  
  # Number of supporting CET areas to return
  max_supporting: 3

stop_words:
  # Generic SBIR terms
  - phase
  - sbir
  - sttr
  - award
  - contract
  - proposal
  - program
  - project
  - research
  - development
  - technology
  - technical
  
  # Business terms
  - company
  - firm
  - small
  - business
  - innovative
  - innovation
  
  # Proposal boilerplate
  - objective
  - approach
  - anticipated
  - benefits
  - commercial
  - applications
  - potential
  - proposed
  - develop
  - provide
```

**Benefits**:
- Easy parameter tuning without code changes
- Comments explain parameter choices
- Can version control different configs
- A/B testing via config swap

---

### File: `config/enrichment.yaml`

```yaml
version: "1.0.0"
description: Fallback enrichment mappings

topic_domains:
  # NSF SBIR topic codes
  AI:
    name: Artificial Intelligence
    keywords:
      - machine learning
      - neural networks
      - AI
      - deep learning
  
  BT:
    name: Biotechnology
    keywords:
      - biotechnology
      - gene editing
      - synthetic biology
      - biomedical
  
  LC:
    name: Low Carbon Energy
    keywords:
      - renewable energy
      - energy storage
      - sustainability
      - clean energy
  
  # ... 7 more topic codes

agency_focus:
  NSF:
    description: fundamental research and technology development
    domains: [AI, BT, LC, ET, PT, CT, IT, MT, ST]
  
  DOD:
    description: defense and national security applications
    domains: [AI, CT, IT, advanced_materials, cybersecurity]
  
  AF:
    description: air force and aerospace systems
    domains: [hypersonics, space_technology, autonomous_systems]
  
  NAVY:
    description: naval and maritime systems
    domains: [autonomous_systems, advanced_materials, cybersecurity]
  
  ARMY:
    description: ground systems and soldier technology
    domains: [autonomous_systems, advanced_materials, medical_devices]
  
  DOE:
    description: energy systems and national laboratories
    domains: [energy_storage, renewable_energy, advanced_materials]
  
  NASA:
    description: space exploration and aeronautics
    domains: [space_technology, advanced_materials, autonomous_systems]
  
  NIH:
    description: biomedical research and healthcare innovation
    domains: [biotechnology, medical_devices, artificial_intelligence]
  
  NOAA:
    description: environmental monitoring and climate science
    domains: [environmental_tech, data_analytics, autonomous_systems]

phase_keywords:
  phase_i:
    - feasibility
    - proof of concept
    - preliminary
  
  phase_ii:
    - development
    - commercialization
    - prototype
  
  phase_iii:
    - production
    - deployment
    - scale-up
```

**Benefits**:
- Agency-specific domain mappings
- Phase-specific keyword enrichment
- Easy to add new agencies
- Can customize per deployment

---

## Implementation Plan

### Phase 1: YAML Loading Infrastructure (2-3 hours)

**Files to Create**:
- `src/sbir_cet_classifier/common/yaml_config.py` - YAML loader with validation
- `config/taxonomy.yaml` - Taxonomy definition
- `config/classification.yaml` - Model parameters
- `config/enrichment.yaml` - Enrichment mappings

**Dependencies**:
```bash
pip install pyyaml pydantic
```

**Core Loader**:
```python
from pathlib import Path
import yaml
from pydantic import BaseModel, Field

class TaxonomyConfig(BaseModel):
    version: str
    effective_date: str
    categories: list[CategoryConfig]

class ClassificationConfig(BaseModel):
    vectorizer: VectorizerConfig
    classifier: ClassifierConfig
    scoring: ScoringConfig
    stop_words: list[str]

def load_taxonomy(path: Path = Path("config/taxonomy.yaml")) -> TaxonomyConfig:
    with open(path) as f:
        data = yaml.safe_load(f)
    return TaxonomyConfig(**data)
```

### Phase 2: Refactor Existing Code (3-4 hours)

**Files to Modify**:
1. `src/sbir_cet_classifier/data/taxonomy.py`
   - Replace CSV loading with YAML loading
   - Keep same `TaxonomyEntry` schema
   - Add validation for parent relationships

2. `src/sbir_cet_classifier/models/applicability.py`
   - Load parameters from `classification.yaml`
   - Keep same `ApplicabilityModel` interface
   - Add config validation in `__init__`

3. `src/sbir_cet_classifier/features/fallback_enrichment.py`
   - Load mappings from `enrichment.yaml`
   - Keep same function signatures
   - Add config caching

**Backward Compatibility**:
- Keep CSV loading as fallback
- Environment variable to choose config source: `SBIR_CONFIG_FORMAT=yaml|csv`
- Default to YAML if both exist

### Phase 3: Testing & Validation (2 hours)

**Test Coverage**:
- YAML parsing and validation
- Schema compatibility with existing code
- Performance (YAML loading should be <100ms)
- Error handling (malformed YAML, missing fields)

**Test Files**:
- `tests/unit/test_yaml_config.py`
- `tests/integration/test_yaml_taxonomy.py`
- `tests/integration/test_yaml_classification.py`

### Phase 4: Documentation (1 hour)

**Files to Create/Update**:
- `docs/CONFIGURATION.md` - User guide for editing YAML
- `config/README.md` - Config file descriptions
- Update `README.md` - Mention YAML configuration

**Documentation Topics**:
- How to add new CET categories
- How to tune classification parameters
- How to add new agencies/topic codes
- Config validation and error messages

---

## Benefits

### For Users
✅ **Easy Updates** - Edit YAML, no code changes  
✅ **Comments** - Document rationale inline  
✅ **Validation** - Pydantic catches errors early  
✅ **Version Control** - Track config changes separately from code  
✅ **A/B Testing** - Swap configs without code branches  

### For Developers
✅ **Separation of Concerns** - Config vs. logic  
✅ **Type Safety** - Pydantic models enforce schema  
✅ **Testing** - Mock configs easily  
✅ **Deployment** - Different configs per environment  

### For Operations
✅ **Hot Reload** - Update config without restart (future)  
✅ **Auditing** - Track who changed what  
✅ **Rollback** - Git revert config changes  
✅ **Multi-Tenant** - Different configs per customer  

---

## Risks & Mitigations

### Risk 1: Breaking Changes
**Impact**: Existing code expects CSV/hardcoded values  
**Mitigation**: 
- Keep CSV as fallback
- Phased rollout with feature flag
- Comprehensive test coverage

### Risk 2: Performance
**Impact**: YAML parsing slower than Python imports  
**Mitigation**:
- Cache loaded configs (LRU cache)
- Load once at startup
- Benchmark: YAML load should be <100ms

### Risk 3: User Errors
**Impact**: Invalid YAML breaks system  
**Mitigation**:
- Pydantic validation with clear error messages
- Schema documentation with examples
- Config validation CLI command: `sbir validate-config`

### Risk 4: Complexity
**Impact**: More files to manage  
**Mitigation**:
- Keep YAML simple (no advanced features)
- Provide templates and examples
- Document common patterns

---

## Effort Estimate

| Phase | Hours | Complexity |
|-------|-------|------------|
| YAML Infrastructure | 2-3 | Medium |
| Code Refactoring | 3-4 | Medium |
| Testing | 2 | Low |
| Documentation | 1 | Low |
| **Total** | **8-10** | **Medium** |

**Timeline**: 1-2 days for single developer

---

## Alternatives Considered

### 1. Keep CSV for Taxonomy
**Pros**: Already works, simple  
**Cons**: No comments, hard to edit, no nesting  
**Verdict**: YAML is better for taxonomy

### 2. Use TOML Instead of YAML
**Pros**: Simpler syntax, less ambiguity  
**Cons**: Less familiar, no multi-line strings  
**Verdict**: YAML is more readable for definitions

### 3. Use JSON
**Pros**: Native Python support, fast parsing  
**Cons**: No comments, no multi-line strings  
**Verdict**: YAML is more user-friendly

### 4. Database Configuration
**Pros**: Dynamic updates, versioning, audit trail  
**Cons**: Overkill for this use case, adds complexity  
**Verdict**: YAML is sufficient

---

## Recommendation

**Proceed with YAML configuration** for all three areas:
1. Taxonomy (highest value - easier to maintain)
2. Classification parameters (medium value - enables tuning)
3. Enrichment mappings (medium value - easier to extend)

**Phased Approach**:
1. Start with taxonomy (most benefit, least risk)
2. Add classification parameters (enables experimentation)
3. Add enrichment mappings (nice-to-have)

**Success Criteria**:
- ✅ Users can add CET category without code changes
- ✅ Users can tune model parameters without code changes
- ✅ Config validation catches errors before runtime
- ✅ Performance impact <100ms at startup
- ✅ All existing tests pass with YAML config

---

## Example User Workflow

### Adding a New CET Category

**Before (CSV)**:
1. Open `cet_taxonomy_v1.csv` in Excel
2. Add row with 8 columns
3. Hope you didn't break CSV format
4. No validation until runtime

**After (YAML)**:
1. Open `config/taxonomy.yaml`
2. Copy existing category block
3. Edit fields with comments
4. Run `sbir validate-config` to check
5. Validation errors show exactly what's wrong

### Tuning Classification

**Before (Python)**:
1. Edit `applicability.py`
2. Change hardcoded values
3. Commit code changes
4. Deploy new code

**After (YAML)**:
1. Edit `config/classification.yaml`
2. Change parameter values
3. Run `sbir validate-config`
4. Deploy config file only (no code changes)

---

## Next Steps

1. **Review this scope** - Get stakeholder approval
2. **Create YAML schemas** - Define Pydantic models
3. **Implement Phase 1** - YAML loading infrastructure
4. **Test with taxonomy** - Validate approach works
5. **Expand to other configs** - Classification, enrichment
6. **Document** - User guide and examples

**Estimated Delivery**: 1-2 days for full implementation

---

**Last Updated**: 2025-10-10  
**Status**: Scoping Complete - Ready for Implementation  
**Effort**: 8-10 hours (1-2 days)
