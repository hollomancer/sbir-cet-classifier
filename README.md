# SBIR CET Classifier

Quick links to consolidated docs:
- CLI: docs/cli/README.md
- Configuration: docs/config/README.md
- Contributing: CONTRIBUTING.md

## Overview

Automated classification system for SBIR awards against 20 Critical and Emerging Technology areas. Features ML-based scoring, portfolio analytics, and export capabilities.

## Quick Start

### Installation

```bash
git clone <repository-url>
cd sbir-cet-classifier
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

# Download spaCy model for evidence extraction (optional)
python -m spacy download en_core_web_md
```

### Demo with Sample Data

We've already classified 997 sample awards for you:

```bash
# View summary statistics
python -c "
import pandas as pd
awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')

print(f'Awards: {len(awards):,}')
print(f'Total Funding: \${awards[\"award_amount\"].sum()/1e6:.1f}M')
print(f'\\nTop 5 CET Areas:')
print(assessments['primary_cet_id'].value_counts().head())
"
```

### CLI Usage

```bash
# View portfolio summary
python -m sbir_cet_classifier.cli.app summary --fiscal-year-start 2023 --fiscal-year-end 2025

# List awards with filters
python -m sbir_cet_classifier.cli.app awards list \
  --fiscal-year-start 2023 --fiscal-year-end 2025 \
  --cet-areas artificial_intelligence \
  --page 1

# Export filtered data
python -m sbir_cet_classifier.cli.app export \
  --fiscal-year-start 2023 --fiscal-year-end 2025 \
  --format csv \
  --output-file ai_awards.csv
```

### API Server

```bash
# Start the API server
uvicorn sbir_cet_classifier.api.router:router --reload --port 8000

# Test endpoints
curl http://localhost:8000/summary?fiscal_year_start=2023&fiscal_year_end=2025
curl http://localhost:8000/awards?fiscal_year_start=2023&fiscal_year_end=2025&page=1
```

### Processing Your Own Data

```bash
# Run the ingestion pipeline
python ingest_awards.py

# This will:
# 1. Load award_data.csv
# 2. Classify against CET taxonomy
# 3. Save results to data/processed/
```

## Architecture

### Tech Stack

- **Language**: Python 3.11+
- **CLI**: Typer with Rich output formatting
- **API**: FastAPI (internal-only, no authentication)
- **Data Processing**: pandas + pyarrow (Parquet)
- **ML**: scikit-learn (TF-IDF + logistic regression)
- **NLP**: spaCy for evidence extraction
- **Testing**: pytest with coverage tracking
- **Code Quality**: ruff for linting and formatting

### Project Structure

```
sbir-cet-classifier/
├── src/sbir_cet_classifier/          # Main package
│   ├── api/                          # FastAPI routes
│   ├── cli/                          # Typer commands
│   ├── common/                       # Schemas and config
│   ├── data/                         # Ingestion and storage
│   ├── features/                     # Domain services
│   ├── models/                       # ML scoring
│   └── evaluation/                   # Metrics and validation
├── tests/                            # Test suites
├── data/                             # Data storage
├── config/                           # Configuration files
└── ingest_awards.py                  # Ingestion script
```

## Configuration

Classification parameters are externalized to YAML files in the `config/` directory:

- **`config/taxonomy.yaml`** — CET taxonomy with 21 technology areas, definitions, and keywords
- **`config/classification.yaml`** — Model hyperparameters, stop words, classification bands
- **`config/enrichment.yaml`** — Topic domain mappings, agency focus areas, phase keywords

**Validate configuration changes:**
```bash
python -m sbir_cet_classifier.cli.app config validate
```

## CET Taxonomy

The Critical and Emerging Technology taxonomy includes 20 technology areas:

- Artificial Intelligence
- Quantum Computing & Sensing
- Hypersonics
- Advanced Materials & Thermal Protection
- Biotechnology
- Space Technology
- Autonomous Systems
- Semiconductors & Microelectronics
- Cybersecurity
- Energy Storage & Renewable Energy
- And 10 more...

## Classification System

### Applicability Scoring

Awards receive a 0-100 applicability score based on:
- **TF-IDF vectorization** of abstracts and keywords
- **Calibrated logistic regression** classifier
- **Classification bands**: High (≥70), Medium (40-69), Low (<40)

### Evidence Statements

Each classification includes ≤3 evidence statements with:
- ≤50 word excerpt from source text
- Source location (abstract, keywords, etc.)
- Rationale tag explaining CET alignment

## Common Queries & Examples

### Find High-Value Awards in Specific CET Areas

```python
import pandas as pd

awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')

# Merge data
merged = awards.merge(assessments, on='award_id')

# High-value AI awards
ai_high_value = merged[
    (merged['primary_cet_id'] == 'artificial_intelligence') &
    (merged['award_amount'] > 1000000) &
    (merged['classification'] == 'High')
]

print(f"High-value AI awards: {len(ai_high_value)}")
print(f"Total funding: ${ai_high_value['award_amount'].sum()/1e6:.1f}M")
```

### Agency Distribution Analysis

```python
import pandas as pd

awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')

merged = awards.merge(assessments, on='award_id')

# Agency breakdown by CET area
agency_cet = merged.groupby(['agency', 'primary_cet_id']).agg({
    'award_id': 'count',
    'award_amount': 'sum'
}).round(2)

print(agency_cet.head(10))
```

## Data Files

### Processed Data
- **`data/processed/awards.parquet`** — Normalized award records
- **`data/processed/assessments.parquet`** — CET classifications with scores
- **`data/processed/taxonomy.parquet`** — Taxonomy reference data

### Input Data
- **`award_data.csv`** — Raw SBIR awards dataset (excluded from git)
- **`data/taxonomy/cet_taxonomy_v1.csv`** — CET taxonomy definitions

### Artifacts
- **`artifacts/export_runs.json`** — Export performance telemetry
- **`artifacts/scoring_runs.json`** — Scoring latency metrics
- **`artifacts/refresh_runs.json`** — Ingestion execution logs

## Environment Variables

```bash
# Data paths (defaults shown)
export SBIR_RAW_DIR=data/raw
export SBIR_PROCESSED_DIR=data/processed
export SBIR_ARTIFACTS_DIR=artifacts

# Performance tuning
export SBIR_BATCH_SIZE=100
export SBIR_MAX_WORKERS=4
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/sbir_cet_classifier --cov-report=html

# Run specific test suites
pytest tests/unit/ -v              # Unit tests
pytest tests/integration/ -v       # Integration tests
pytest tests/contract/ -v          # API contract tests

# Run fast tests only (skip slow integration tests)
pytest -m "not slow" -v
```

## Contributing

This is a personal research project. For collaboration:

1. Review the development guide for detailed setup instructions
2. Check task documentation for implementation status
3. Run tests before submitting changes: `pytest tests/ -v`
4. Maintain ≥85% code coverage
5. Follow ruff formatting: `ruff format src/ tests/`

## License

MIT License - see [LICENSE](LICENSE) file for details.

This project uses public SBIR.gov data under research terms.

## Acknowledgments

- **SBIR.gov** for public access to award data
- **NSTC** for Critical and Emerging Technology taxonomy framework
- **scikit-learn** and **spaCy** for ML/NLP capabilities

---

**Status**: ✅ Production-ready | **Last Updated**: 2025-10-10 | **Version**: 1.1.0 (Phase O Optimizations)

For detailed documentation see:
- **DEVELOPMENT.md** - Development setup, testing, and contribution guidelines
- **STATUS.md** - Project status, task completion, and release readiness
- **config/README.md** - Configuration file documentation
- **docs/CONFIG.md** - Editing classification.yaml safely and validation steps
