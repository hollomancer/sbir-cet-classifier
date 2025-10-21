# Quickstart: SAM.gov API Enrichment

**Feature**: SAM.gov API Data Enrichment  
**Phase**: 1 - Design & Contracts  
**Date**: 2025-10-10

## Prerequisites

- Python 3.11+ environment with existing SBIR CET Classifier
- SAM.gov API key (obtain from [SAM.gov API documentation](https://open.gsa.gov/api/sam-api/))
- Existing award data in `data/processed/awards.parquet`
- At least 2GB available storage for enriched data

## Quick Setup

### 1. Environment Configuration

```bash
# Set SAM.gov API credentials
export SAM_API_KEY="your-api-key-here"
export SAM_API_BASE_URL="https://api.sam.gov/prod/federalregistry/v2"

# Optional: Configure rate limiting
export SAM_API_RATE_LIMIT=100  # requests per minute
export SAM_API_TIMEOUT=30      # seconds
```

### 2. Install Dependencies

```bash
# Install additional dependencies for SAM.gov integration
pip install requests>=2.31.0 tenacity>=8.2.0 pydantic>=2.0.0

# Verify existing dependencies
pip install -e .[dev]  # Existing project dependencies
```

### 3. Basic Enrichment

```bash
# Enrich a single award (test)
python -m sbir_cet_classifier.cli enrich-award --award-id "AWARD_123" --types awardee

# Enrich sample dataset (997 awards)
python -m sbir_cet_classifier.cli enrich-batch --input data/processed/awards.parquet --types all

# Check enrichment status
python -m sbir_cet_classifier.cli enrichment-status --award-id "AWARD_123"
```

## Core Usage Patterns

### Single Award Enrichment

```python
from sbir_cet_classifier.data.enrichment import EnrichmentService

# Initialize service
enricher = EnrichmentService(api_key=os.getenv("SAM_API_KEY"))

# Enrich specific award
result = enricher.enrich_award(
    award_id="AWARD_123",
    enrichment_types=["awardee", "program_office", "solicitation"],
    confidence_threshold=0.7
)

print(f"Enrichment confidence: {result.overall_confidence}")
print(f"Processing time: {result.processing_time}ms")
```

### Batch Processing

```python
from sbir_cet_classifier.data.enrichment import BatchEnricher
import pandas as pd

# Load existing awards
awards_df = pd.read_parquet("data/processed/awards.parquet")

# Configure batch enrichment
batch_enricher = BatchEnricher(
    api_key=os.getenv("SAM_API_KEY"),
    batch_size=10,
    max_workers=4
)

# Process awards
job_id = batch_enricher.enrich_awards(
    award_ids=awards_df["award_id"].tolist(),
    enrichment_types=["all"]
)

# Monitor progress
status = batch_enricher.get_status(job_id)
print(f"Progress: {status.overall_progress:.1%}")
```

### Data Validation

```python
from sbir_cet_classifier.data.enrichment import EnrichmentValidator

validator = EnrichmentValidator()

# Validate enriched award
validation_result = validator.validate_award("AWARD_123")

if validation_result.is_valid:
    print(f"Data quality score: {validation_result.confidence_score}")
else:
    print("Validation issues:")
    for check in validation_result.validation_checks:
        if not check.passed:
            print(f"  - {check.check_name}: {check.message}")
```

## Data Access Patterns

### Reading Enriched Data

```python
import pandas as pd

# Load enriched awards
enriched_awards = pd.read_parquet("data/processed/enriched_awards.parquet")

# Load awardee profiles
awardee_profiles = pd.read_parquet("data/processed/awardee_profiles.parquet")

# Join awards with awardee data
awards_with_profiles = enriched_awards.merge(
    awardee_profiles, 
    on="awardee_profile_id", 
    how="left"
)

# Filter high-confidence enrichments
high_confidence = enriched_awards[
    enriched_awards["enrichment_confidence"] >= 0.8
]
```

### Querying Program Offices

```python
# Load program office data
program_offices = pd.read_parquet("data/processed/program_offices.parquet")

# Find offices by strategic focus
ai_offices = program_offices[
    program_offices["strategic_focus_areas"].str.contains("Artificial Intelligence")
]

# Get awards by program office
office_awards = enriched_awards[
    enriched_awards["program_office_id"].isin(ai_offices["office_id"])
]
```

### Analyzing Solicitation Data

```python
# Load solicitation data
solicitations = pd.read_parquet("data/processed/solicitations.parquet")

# Find solicitations with high CET relevance
high_cet_solicitations = solicitations[
    solicitations["cet_relevance_scores"].apply(
        lambda scores: max(scores.values()) > 0.8
    )
]

# Enhanced CET classification using solicitation text
from sbir_cet_classifier.models.scoring import EnhancedCETClassifier

classifier = EnhancedCETClassifier(use_solicitation_text=True)
enhanced_scores = classifier.score_awards(awards_with_solicitations)
```

## Performance Monitoring

### Enrichment Metrics

```python
# Check enrichment coverage
enrichment_status = pd.read_parquet("data/processed/enrichment_status.parquet")

# Calculate success rates by enrichment type
success_rates = enrichment_status.groupby("enrichment_type")["status"].apply(
    lambda x: (x == "completed").mean()
)

print("Enrichment Success Rates:")
for enrichment_type, rate in success_rates.items():
    print(f"  {enrichment_type}: {rate:.1%}")
```

### API Usage Tracking

```python
from sbir_cet_classifier.data.enrichment import APIUsageTracker

tracker = APIUsageTracker()

# Get usage statistics
usage_stats = tracker.get_daily_usage()
print(f"API calls today: {usage_stats.total_calls}")
print(f"Rate limit utilization: {usage_stats.rate_limit_utilization:.1%}")
print(f"Average response time: {usage_stats.avg_response_time}ms")
```

## Troubleshooting

### Common Issues

**API Rate Limiting**:
```bash
# Check current rate limit status
python -m sbir_cet_classifier.cli api-status

# Adjust rate limiting
export SAM_API_RATE_LIMIT=50  # Reduce to 50 requests/minute
```

**Low Confidence Matches**:
```python
# Review low-confidence enrichments
low_confidence = enrichment_status[
    (enrichment_status["confidence_score"] < 0.7) & 
    (enrichment_status["status"] == "completed")
]

# Manual review interface
from sbir_cet_classifier.data.enrichment import ManualReviewInterface
reviewer = ManualReviewInterface()
reviewer.review_low_confidence_matches(low_confidence["award_id"].tolist())
```

**Data Inconsistencies**:
```python
# Run data consistency checks
from sbir_cet_classifier.data.enrichment import ConsistencyChecker

checker = ConsistencyChecker()
inconsistencies = checker.find_inconsistencies()

for issue in inconsistencies:
    print(f"Award {issue.award_id}: {issue.description}")
    print(f"  Suggested fix: {issue.suggested_fix}")
```

### Performance Optimization

**Parallel Processing**:
```python
# Increase concurrency for batch processing
batch_enricher = BatchEnricher(
    api_key=os.getenv("SAM_API_KEY"),
    batch_size=20,      # Increase batch size
    max_workers=8,      # Increase worker threads
    rate_limit=150      # Increase rate limit if API allows
)
```

**Selective Enrichment**:
```python
# Only enrich awards missing specific data
awards_needing_awardee_data = awards_df[
    awards_df["awardee_profile_id"].isna()
]

# Enrich only specific types
enricher.enrich_awards(
    award_ids=awards_needing_awardee_data["award_id"].tolist(),
    enrichment_types=["awardee"]  # Only awardee data
)
```

## Integration with Existing Pipeline

### Enhanced CET Classification

```python
# Update existing classification to use enriched data
from sbir_cet_classifier.models.scoring import CETClassifier

# Load classifier with solicitation enhancement
classifier = CETClassifier(
    use_solicitation_text=True,
    solicitation_weight=0.3  # 30% weight to solicitation text
)

# Re-score awards with enriched data
enhanced_assessments = classifier.score_awards(enriched_awards)

# Compare accuracy improvement
original_accuracy = calculate_accuracy(original_assessments)
enhanced_accuracy = calculate_accuracy(enhanced_assessments)
improvement = enhanced_accuracy - original_accuracy

print(f"Classification accuracy improvement: {improvement:.1%}")
```

### Export Integration

```python
# Include enriched data in exports
from sbir_cet_classifier.features.export import EnhancedExporter

exporter = EnhancedExporter(include_enrichment=True)

# Export with awardee profiles and program context
export_data = exporter.export_awards(
    award_ids=selected_awards,
    include_fields=[
        "awardee_profile", 
        "program_office", 
        "solicitation_summary"
    ]
)
```

## Next Steps

1. **Run initial enrichment** on sample dataset (997 awards)
2. **Validate data quality** and adjust confidence thresholds
3. **Measure classification improvement** with enriched solicitation text
4. **Scale to full dataset** (200k+ awards) with optimized batch processing
5. **Integrate with existing workflows** and export capabilities

For detailed implementation guidance, see:
- [data-model.md](data-model.md) - Data schemas and relationships
- [contracts/](contracts/) - API specifications and contracts
- [research.md](research.md) - Technical decisions and alternatives
