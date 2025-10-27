# Configuration Files

This directory contains YAML configuration files for the SBIR CET Classifier.

## Files

### taxonomy.yaml

CET (Critical and Emerging Technology) taxonomy definition:

- **Version**: NSTC taxonomy version (e.g., NSTC-2025Q1)
- **Categories**: 21 technology areas with definitions, keywords, and parent relationships
- **Keywords**: Domain-specific terms for each CET category

**Example: Adding a new CET category**
```yaml
categories:
  - id: new_technology
    name: New Technology Area
    definition: Description of the technology area
    parent: parent_category_id  # Optional
    keywords:
      - keyword1
      - keyword2
```

### classification.yaml

Classification model parameters and rule-based scoring data. This file is designed so non-developers can make safe edits. Use two spaces for indentation and keep keys exactly as shown.

Structure:

- version: Schema version string (e.g., "1.0.0")
- vectorizer: TF-IDF settings
  - ngram_range: [min, max] n-gram sizes
  - max_features: integer feature cap
  - min_df: ignore terms appearing in fewer than N documents
  - max_df: ignore terms appearing in more than X% of documents (0-1)
- feature_selection: chi2 settings
  - enabled: true/false
  - method: chi2
  - k: number of top features to keep
- classifier: logistic regression settings
  - max_iter, solver, n_jobs, class_weight
- calibration: probability calibration
  - enabled, method, cv, min_samples_per_class
- scoring: band thresholds and options
  - bands: high/medium/low each with min, max, label (0-100)
  - max_supporting: number of secondary CETs to return
- stop_words: list of generic terms to ignore
- agency_priors: per-agency score boosts by CET id
- branch_priors: per-branch (sub-agency) score boosts by CET id
- cet_keywords: for each CET id, lists of core, related, negative phrases
- context_rules: CET-specific keyword combinations that add a boost

Safe editing guidelines:

- Do not rename top-level keys.
- CET ids are lowercase with underscores (e.g., artificial_intelligence).
- Keep numbers as integers; typical boost range is 0-25.
- Put multi-word phrases in quotes: "quantum computing".
- Use dashes for lists; align with two-space indentation.
- Prefer small, incremental changes; validate after each change.

Common edits and examples:

1) Change classification bands
```yaml
scoring:
  bands:
    high:
      min: 80
      max: 100
      label: High
    medium:
      min: 50
      max: 79
      label: Medium
    low:
      min: 0
      max: 49
      label: Low
```

2) Add or adjust agency priors (boosts applied when an award is from that agency)
```yaml
agency_priors:
  National Institutes of Health:
    medical_devices: 25
    biotechnology: 20
  National Science Foundation:
    _all_cets: 5   # Small global boost across all CETs
```

3) Edit CET keywords (core = strongest signals; negative = exclude contexts)
```yaml
cet_keywords:
  quantum_computing:
    core:
      - "quantum computing"
      - "quantum algorithm"
    related:
      - "qubit"
    negative:
      - "quantum chemistry"
```

4) Add a context rule (adds points when all required keywords occur together)
```yaml
context_rules:
  medical_devices:
    - [["ai", "diagnostic"], 20]
```

After any change, run the validation command shown below to ensure the file is still valid.

### enrichment.yaml

Fallback enrichment mappings and NIH matcher configuration:

- **NIH Matcher**: Hybrid matching strategy parameters
  - `amount_tolerance_min/max`: Award amount matching tolerance (default: ±10%)
  - `similarity_threshold`: Abstract text similarity threshold (default: 0.5 = 50%)
  - `org_suffixes`: Organization name suffixes to remove for fuzzy matching
  - `exact_match_limit`, `fuzzy_match_limit`, `similarity_match_limit`: API search limits
- **Topic Domains**: NSF SBIR topic codes mapped to domain names and keywords
- **Agency Focus**: Agency-specific research focus descriptions
- **Phase Keywords**: Phase I/II specific terminology

**Example: Adjusting NIH matcher sensitivity**
```yaml
nih_matcher:
  amount_tolerance_min: 0.85  # Stricter: ±15% instead of ±10%
  amount_tolerance_max: 1.15
  similarity_threshold: 0.6   # Require 60% similarity instead of 50%
```

**Example: Adding a new topic code**
```yaml
topic_domains:
  XY:
    name: Example Technology
    keywords:
      - example
      - technology
      - innovation
```

## Usage

Configuration files are automatically loaded at module import time and cached for performance.

```python
from sbir_cet_classifier.common.yaml_config import (
    load_taxonomy_config,
    load_classification_config,
    load_enrichment_config
)

# Load configs
tax_config = load_taxonomy_config()
clf_config = load_classification_config()
enr_config = load_enrichment_config()

# Access settings
categories = tax_config.categories
ngram_range = clf_config.vectorizer.ngram_range
stop_words = clf_config.stop_words
topic_domains = enr_config.topic_domains
```

## Validation

Configuration files are validated using Pydantic models. Invalid configurations will raise validation errors at load time with clear error messages.

To test your configuration changes:

```bash
python -m sbir_cet_classifier.cli.app config validate
```

Expected output:
```
✅ taxonomy.yaml
   Version: NSTC-2025Q1
   Categories: 21

✅ classification.yaml
   Version: 1.0.0
   Vectorizer: (1, 3) n-grams

✅ enrichment.yaml
   Version: 1.0.0
   Topic domains: 18

✅ All configuration files are valid!
```

## Version Control

- Configuration files are versioned independently from code
- Version field in each YAML file tracks configuration schema version
- Changes to configuration should be documented in commit messages

## Best Practices

1. **Test changes**: Run validation command after editing (`python -m sbir_cet_classifier.cli.app config validate`)
2. **Document rationale**: Add comments explaining parameter choices
3. **Incremental changes**: Change one parameter at a time
4. **Backup**: Keep previous versions for rollback
5. **Performance**: Monitor classification metrics after config changes
