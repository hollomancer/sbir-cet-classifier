# Configuration Files

This directory contains YAML configuration files for the SBIR CET Classifier.

## Files

### classification.yaml

Classification model hyperparameters and settings:

- **Vectorizer**: TF-IDF configuration (n-grams, feature limits, stop words)
- **Feature Selection**: Chi-squared feature selection settings
- **Classifier**: Logistic regression parameters
- **Calibration**: Probability calibration settings
- **Scoring**: Classification bands (High/Medium/Low) and thresholds
- **Stop Words**: Domain-specific terms to filter from text

**Example: Changing classification bands**
```yaml
scoring:
  bands:
    high:
      min: 80  # Changed from 70
      max: 100
      label: High
```

### enrichment.yaml

Fallback enrichment mappings for awards without API data:

- **Topic Domains**: NSF SBIR topic codes mapped to domain names and keywords
- **Agency Focus**: Agency-specific research focus descriptions
- **Phase Keywords**: Phase I/II specific terminology

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
    load_classification_config,
    load_enrichment_config
)

# Load configs
clf_config = load_classification_config()
enr_config = load_enrichment_config()

# Access settings
ngram_range = clf_config.vectorizer.ngram_range
stop_words = clf_config.stop_words
topic_domains = enr_config.topic_domains
```

## Validation

Configuration files are validated using Pydantic models. Invalid configurations will raise validation errors at load time with clear error messages.

To test your configuration changes:

```bash
python -c "
from sbir_cet_classifier.common.yaml_config import load_classification_config, load_enrichment_config
print('Classification config:', load_classification_config().version)
print('Enrichment config:', load_enrichment_config().version)
print('✅ All configs valid')
"
```

## Version Control

- Configuration files are versioned independently from code
- Version field in each YAML file tracks configuration schema version
- Changes to configuration should be documented in commit messages

## Best Practices

1. **Test changes**: Run validation script after editing
2. **Document rationale**: Add comments explaining parameter choices
3. **Incremental changes**: Change one parameter at a time
4. **Backup**: Keep previous versions for rollback
5. **Performance**: Monitor classification metrics after config changes
