#!/usr/bin/env python
"""Validate YAML configuration files."""

from pathlib import Path

from sbir_cet_classifier.common.yaml_config import (
    load_classification_config,
    load_enrichment_config,
)


def main():
    """Validate all configuration files."""
    print("Validating YAML configuration files...\n")
    
    # Validate classification config
    try:
        clf_config = load_classification_config()
        print("✅ classification.yaml")
        print(f"   Version: {clf_config.version}")
        print(f"   Vectorizer: {clf_config.vectorizer.ngram_range} n-grams")
        print(f"   Stop words: {len(clf_config.stop_words)} terms")
        print(f"   Bands: {', '.join(clf_config.scoring.bands.keys())}")
    except Exception as e:
        print(f"❌ classification.yaml: {e}")
        return 1
    
    # Validate enrichment config
    try:
        enr_config = load_enrichment_config()
        print("\n✅ enrichment.yaml")
        print(f"   Version: {enr_config.version}")
        print(f"   Topic domains: {len(enr_config.topic_domains)}")
        print(f"   Agencies: {len(enr_config.agency_focus)}")
        print(f"   Sample topics: {', '.join(list(enr_config.topic_domains.keys())[:5])}")
    except Exception as e:
        print(f"❌ enrichment.yaml: {e}")
        return 1
    
    print("\n✅ All configuration files are valid!")
    return 0


if __name__ == "__main__":
    exit(main())
