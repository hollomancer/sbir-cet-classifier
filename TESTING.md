# Testing Guide: SBIR CET Classifier

## Quick Start

```bash
# 1. Install dependencies
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .[dev]

# 2. Run all tests
pytest

# 3. Run tests with coverage
pytest --cov=src/sbir_cet_classifier --cov-report=html

# 4. Run specific test suites
pytest tests/unit/           # Unit tests only
pytest tests/contract/       # Contract tests only
pytest tests/integration/    # Integration tests only
```

## Test Structure

```
tests/
├── unit/                    # Fast, isolated tests for individual modules
│   ├── data/               # Data ingestion, taxonomy, storage
│   ├── features/           # Summary, awards, evidence, review queue
│   └── models/             # Applicability scoring, metrics
├── contract/               # API contract validation
│   ├── test_summary_endpoint.py
│   └── test_awards_and_cet_endpoints.py
└── integration/            # End-to-end workflow tests
    └── sbir_cet_classifier/
        ├── summary/
        └── awards/
```

## Test Categories

### 1. Unit Tests (Fast, ~3s)

Test individual modules in isolation:

```bash
# Run all unit tests
pytest tests/unit/ -v

# Test specific modules
pytest tests/unit/sbir_cet_classifier/data/ -v           # Data layer
pytest tests/unit/sbir_cet_classifier/features/ -v      # Feature services
pytest tests/unit/sbir_cet_classifier/models/ -v        # ML models
```

**What's tested:**
- Data ingestion and normalization
- Taxonomy loading and versioning
- Applicability scoring logic
- Evidence extraction
- Summary aggregation
- Review queue state management

### 2. Contract Tests (API Validation)

Validate API endpoints match OpenAPI spec:

```bash
pytest tests/contract/ -v
```

**What's tested:**
- Request/response schemas
- HTTP status codes
- Pagination structures
- Error handling
- Filter parameter parsing

### 3. Integration Tests (Full Workflows)

Test complete user journeys:

```bash
pytest tests/integration/ -v
```

**What's tested:**
- CLI and API parity (same filters, same results)
- Multi-agency comparisons
- Award drill-down workflows
- Export generation
- Manual review queue integration

## CLI Testing

### Test Summary Command

```bash
# Install the CLI
pip install -e .

# Test summary (uses fixture data)
sbir-nist summary 2023 2024 --agency AF

# Expected output: JSON with CET distribution, counts, and obligated dollars
```

### Test Awards Commands

```bash
# List awards
sbir-nist awards list \
  --fiscal-year-start 2023 \
  --fiscal-year-end 2024 \
  --agency AF \
  --page 1 \
  --page-size 10

# Show award detail
sbir-nist awards show --award-id AF-2023-001

# CET area detail with gap analytics
sbir-nist awards cet-detail \
  --cet-id hypersonics \
  --fiscal-year-start 2023 \
  --fiscal-year-end 2024
```

### Test Export Commands

```bash
# Create export
sbir-nist export create \
  --fiscal-year-start 2023 \
  --fiscal-year-end 2024 \
  --agency AF \
  --format csv

# Check export status
sbir-nist export status --job-id <JOB_ID>
```

## API Testing

### Start the API Server

```bash
# Start FastAPI server
uvicorn sbir_cet_classifier.api.router:router --reload --port 8000
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Get summary
curl "http://localhost:8000/applicability/summary?fiscal_year_start=2023&fiscal_year_end=2024&agency=AF"

# List awards
curl "http://localhost:8000/applicability/awards?fiscal_year_start=2023&fiscal_year_end=2024&page=1&pageSize=25"

# Get award detail
curl http://localhost:8000/applicability/awards/AF-2023-001

# Get CET detail
curl "http://localhost:8000/applicability/cet/hypersonics?fiscal_year_start=2023&fiscal_year_end=2024"

# Create export
curl -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -d '{
    "fiscal_year_start": 2023,
    "fiscal_year_end": 2024,
    "agencies": ["AF"],
    "format": "csv"
  }'

# Check export status
curl "http://localhost:8000/exports?jobId=<JOB_ID>"
```

## Test with Real Data

### 1. Set Up Test Data

```bash
# Create test taxonomy
mkdir -p data/taxonomy
cat > data/taxonomy/NSTC-2025Q1.json << 'EOF'
{
  "version": "NSTC-2025Q1",
  "effective_date": "2025-01-01",
  "entries": [
    {
      "cet_id": "hypersonics",
      "name": "Hypersonics",
      "definition": "High-speed flight technologies",
      "parent_cet_id": null,
      "version": "NSTC-2025Q1",
      "effective_date": "2025-01-01",
      "retired_date": null,
      "status": "active"
    }
  ]
}
EOF
```

### 2. Run Ingestion (Stub Mode)

```bash
# Ingest test fiscal year
sbir-nist refresh \
  --fiscal-year-start 2023 \
  --fiscal-year-end 2023 \
  --source-url https://example.com/test_data.zip
```

### 3. Generate Summary

```bash
sbir-nist summary 2023 2023
```

## Performance Testing

### Test SLA Requirements

```bash
# Test summary generation (target: ≤3 minutes)
time sbir-nist summary 2020 2024 --agency AF

# Test export generation (target: ≤10 minutes for 50k awards)
time sbir-nist export create \
  --fiscal-year-start 2020 \
  --fiscal-year-end 2024 \
  --format csv
```

### Load Testing

```bash
# Install load testing tool
pip install locust

# Run load tests against API
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

## Continuous Integration

### Pre-commit Checks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### CI Pipeline

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e .[dev]
      - run: pytest --cov --cov-report=xml
      - run: ruff check .
```

## Troubleshooting

### Common Issues

**ImportError: cannot import name 'UTC'**
- Solution: Using Python 3.9, use `timezone.utc` instead of `UTC`

**FileNotFoundError: No taxonomy versions available**
- Solution: Create taxonomy file in `data/taxonomy/`

**Service unavailable (503)**
- Solution: Configure services before using API (see `configure_summary_service()`)

### Debug Mode

```bash
# Run tests with verbose output
pytest -vv --tb=long

# Run specific test with debugging
pytest tests/unit/sbir_cet_classifier/features/test_summary.py::test_summarize_filters_and_aggregates -vv -s

# Enable logging
pytest --log-cli-level=DEBUG
```

## Coverage Goals

- **Unit tests**: ≥85% statement coverage
- **Contract tests**: 100% of API endpoints
- **Integration tests**: All user stories covered

### Check Coverage

```bash
# Generate coverage report
pytest --cov=src/sbir_cet_classifier --cov-report=html

# Open report
open htmlcov/index.html  # macOS
# or
xdg-open htmlcov/index.html  # Linux
```

## Next Steps

1. **Add fixture data**: Create representative test datasets
2. **Mock external services**: Use `responses` library for SBIR.gov API
3. **Property-based testing**: Use `hypothesis` for edge case generation
4. **Performance benchmarks**: Add `pytest-benchmark` for regression tracking
5. **Contract validation**: Use `schemathesis` for OpenAPI fuzzing

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
- OpenAPI spec: `specs/001-i-want-to/contracts/openapi.yaml`
