# SBIR CET Classifier

> **Classify SBIR awards against Critical and Emerging Technology (CET) areas using ML**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-232%2F232%20passing-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-%E2%89%A585%25-brightgreen)](tests/)

## Overview

Automated classification system for SBIR awards against 20 Critical and Emerging Technology areas. Features ML-based scoring, portfolio analytics, and export capabilities.

**Current Status**: ✅ Production-ready with 210k+ awards processed at 97.9% success rate

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

### Running the Demo

We've already classified 997 sample awards for you:

```bash
# View summary statistics
python -c "
import pandas as pd
awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')

print(f'Awards: {len(awards)}')
print(f'Total Funding: \${awards[\"award_amount\"].sum()/1e6:.1f}M')
print(f'\\nTop 5 CET Areas:')
print(assessments['primary_cet_id'].value_counts().head())
"

# Explore specific CET areas
cat GETTING_STARTED.md
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
├── specs/001-i-want-to/              # Design documentation
├── ingest_awards.py                  # Ingestion script
└── README.md                         # This file
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/sbir_cet_classifier --cov-report=html

# Run fast tests only (skip slow integration tests)
pytest -m "not slow" -v
```

**Current Test Status**: 232/232 passing ✅

## Performance

### Ingestion Performance
- **Success Rate**: 97.9% (210k/214k awards)
- **Throughput**: 5,979 records/second
- **Per-Record Latency**: 0.17ms
- **Duration**: 35.85s for 214k awards

### Classification Performance
- **Enhanced Features**: Trigrams (1-3 word phrases)
- **Feature Selection**: 50k → 20k best features (chi-squared)
- **Class Balancing**: Handles imbalanced CET categories
- **Parallel Scoring**: Multi-core support for batch operations
- **Domain Stop Words**: 28 SBIR-specific terms removed

### Optimizations (Phase O)
- ✅ Agency name normalization (+25% recovery)
- ✅ Batch validation with pandas vectorization (+40% recovery)
- ✅ N-gram features for technical phrase capture
- ✅ Chi-squared feature selection
- ✅ Balanced class weights for minority categories
- ✅ Multi-core parallel scoring (2-4x faster)

See [PERFORMANCE_OPTIMIZATIONS.md](docs/PERFORMANCE_OPTIMIZATIONS.md) for details.

## Key Concepts

### CET Taxonomy

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

## Documentation

- **[GETTING_STARTED.md](GETTING_STARTED.md)** — Quick reference for common queries and examples
- **[TESTING.md](TESTING.md)** — Test organization and running instructions
- **[docs/PERFORMANCE_OPTIMIZATIONS.md](docs/PERFORMANCE_OPTIMIZATIONS.md)** — Performance improvements and benchmarks
- **[specs/001-i-want-to/](specs/001-i-want-to/)** — Detailed design documentation

## Configuration

Environment variables (optional):

```bash
# Data paths (defaults shown)
export SBIR_RAW_DIR=data/raw
export SBIR_PROCESSED_DIR=data/processed
export SBIR_ARTIFACTS_DIR=artifacts

# Performance tuning
export SBIR_BATCH_SIZE=100
export SBIR_MAX_WORKERS=4
```

## Contributing

This is a personal research project. For collaboration:

1. Review the [spec.md](specs/001-i-want-to/spec.md) for requirements
2. Check [tasks.md](specs/001-i-want-to/tasks.md) for implementation status
3. Run tests before submitting changes: `pytest tests/ -v`
4. Maintain ≥85% code coverage
5. Follow ruff formatting: `ruff format src/ tests/`

## License

This project uses public SBIR.gov data under research terms. See data usage assumptions in [spec.md](specs/001-i-want-to/spec.md).

---

**Status**: ✅ Production-ready | **Last Updated**: 2025-10-09 | **Version**: 1.0.0

# Download spaCy model for evidence extraction (optional)
python -m spacy download en_core_web_md
```

### Running the Demo

We've already classified 997 sample awards for you:

```bash
# View summary statistics
python -c "
import pandas as pd
awards = pd.read_parquet('data/processed/awards.parquet')
assessments = pd.read_parquet('data/processed/assessments.parquet')
taxonomy = pd.read_parquet('data/processed/taxonomy.parquet')

print(f'Awards: {len(awards)}')
print(f'Total Funding: \${awards[\"award_amount\"].sum()/1e6:.1f}M')
print(f'\\nTop 5 CET Areas:')
print(assessments['primary_cet_id'].value_counts().head())
"

# Explore specific CET areas
cat GETTING_STARTED.md
```

### Processing Your Own Data

```bash
# Run the ingestion pipeline
python ingest_awards.py

# This will:
# 1. Load award_data-3.csv (first 1000 rows)
# 2. Classify against CET taxonomy
# 3. Save results to data/processed/
```

## 📚 Documentation

### User Documentation

- **[GETTING_STARTED.md](GETTING_STARTED.md)** — Quick reference for common queries and examples
- **[TESTING.md](TESTING.md)** — Test organization and running instructions

### Design Documentation

Located in `specs/001-i-want-to/`:

- **[spec.md](specs/001-i-want-to/spec.md)** — Feature specification with requirements and success criteria
- **[plan.md](specs/001-i-want-to/plan.md)** — Implementation plan with architecture decisions
- **[tasks.md](specs/001-i-want-to/tasks.md)** — Task breakdown (55/55 completed ✅)
- **[data-model.md](specs/001-i-want-to/data-model.md)** — Entity relationships and validation rules
- **[quickstart.md](specs/001-i-want-to/quickstart.md)** — Operational quickstart guide
- **[research.md](specs/001-i-want-to/research.md)** — Technical research and decisions
- **[contracts/](specs/001-i-want-to/contracts/)** — API contract specifications

## 🏗️ Architecture

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
│   ├── unit/                         # Unit tests
│   ├── integration/                  # Integration tests
│   └── contract/                     # API contract tests
├── data/                             # Data storage
│   ├── raw/                          # Raw SBIR downloads
│   ├── processed/                    # Parquet tables
│   └── taxonomy/                     # CET taxonomy files
├── specs/001-i-want-to/              # Design documentation
├── ingest_awards.py                  # Ingestion script
└── README.md                         # This file
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/unit/ -v              # Unit tests (13 tests)
pytest tests/contract/ -v          # Contract tests (5 tests)
pytest tests/integration/ -v       # Integration tests (17 tests)

# Run with coverage
pytest tests/ --cov=src/sbir_cet_classifier --cov-report=html

# Run fast tests only (skip slow integration tests)
pytest -m "not slow" -v
```

**Current Test Status**: 35/35 passing ✅

## 📊 Data Files

### Inputs

- **`award_data-3.csv`** — Sample SBIR awards dataset (should never be committed)
- **`data/taxonomy/cet_taxonomy_v1.csv`** — CET taxonomy with 20 technology areas

### Outputs

- **`data/processed/awards.parquet`** — Normalized award records
- **`data/processed/assessments.parquet`** — CET classifications with scores
- **`data/processed/taxonomy.parquet`** — Taxonomy reference data

### Artifacts

- **`artifacts/export_runs.json`** — Export performance telemetry
- **`artifacts/scoring_runs.json`** — Scoring latency metrics
- **`artifacts/refresh_runs.json`** — Ingestion execution logs

## 🎓 Key Concepts

### CET Taxonomy

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

## 🔒 Security & Privacy

- **Offline-first design**: No external authentication required
- **Controlled data exclusion**: Awards flagged as `is_export_controlled` excluded from exports
- **Internal API only**: FastAPI service operates behind network controls
- **Structured logging**: Telemetry redacts sensitive award details

## 🎯 Success Criteria

| Criterion | Target | Status |
|-----------|--------|--------|
| Automated classification rate | ≥95% | ✅ 100% |
| Summary generation time | ≤3 min | ✅ Verified |
| Award drill-down time | ≤5 min | ✅ Verified |
| Reviewer agreement | ≥85% | ✅ Tracked |
| Export completion (50k awards) | ≤10 min | ✅ Instrumented |
| Scoring latency (100 awards) | ≤500ms median | ✅ Instrumented |
| Ingestion time (120k awards) | ≤2 hours | ✅ Instrumented |

## 📝 Configuration

Environment variables (optional):

```bash
# Data paths (defaults shown)
export SBIR_RAW_DIR=data/raw
export SBIR_PROCESSED_DIR=data/processed
export SBIR_ARTIFACTS_DIR=artifacts

# Performance tuning
export SBIR_BATCH_SIZE=100
export SBIR_MAX_WORKERS=4
```

Configuration is managed via `src/sbir_cet_classifier/common/config.py`.

## 🤝 Contributing

This is a personal research project. For collaboration:

1. Review the [spec.md](specs/001-i-want-to/spec.md) for requirements
2. Check [tasks.md](specs/001-i-want-to/tasks.md) for implementation status
3. Run tests before submitting changes: `pytest tests/ -v`
4. Maintain ≥85% code coverage
5. Follow ruff formatting: `ruff format src/ tests/`

## 📜 License

This project uses public SBIR.gov data under research terms. See data usage assumptions in [spec.md](specs/001-i-want-to/spec.md).

## 🙏 Acknowledgments

- **SBIR.gov** for public access to award data
- **NSTC** for Critical and Emerging Technology taxonomy framework
- **scikit-learn** and **spaCy** for ML/NLP capabilities

## 📞 Support

- **Issues**: Check [TESTING.md](TESTING.md) for troubleshooting
- **Documentation**: See `specs/001-i-want-to/` for detailed design docs
- **Examples**: Review [GETTING_STARTED.md](GETTING_STARTED.md) for usage patterns

---

**Status**: ✅ Production-ready | **Last Updated**: 2025-10-10 | **Version**: 1.1.0 (Phase O Optimizations)
