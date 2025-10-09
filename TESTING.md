# Testing Guide

## Overview

The SBIR CET Classifier uses pytest for comprehensive testing across unit, integration, and contract test suites.

**Current Status**: ✅ 23/23 tests passing

## Quick Start

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

## Test Organization

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Speed**: Fast (< 100ms per test)
- **Coverage**: Core business logic, data models, utilities
- **Count**: 13 tests

**Key test files**:
- `test_applicability.py` - ML model functionality
- `test_evidence.py` - Evidence extraction logic
- `test_summary.py` - Portfolio summary calculations
- `test_ingest.py` - Data ingestion pipeline
- `test_store.py` - Parquet data storage

### Integration Tests (`tests/integration/`)
- **Purpose**: Test component interactions and workflows
- **Speed**: Medium (100ms - 1s per test)
- **Coverage**: End-to-end workflows, CLI commands, data flows
- **Count**: 5 tests

**Key test files**:
- `test_bootstrap.py` - System initialization and data loading
- `test_award_gap_flow.py` - Award analysis workflows
- `test_summary_filters.py` - Cross-system filter consistency

### Contract Tests (`tests/contract/`)
- **Purpose**: Test API endpoint contracts and responses
- **Speed**: Fast (< 200ms per test)
- **Coverage**: FastAPI routes, request/response schemas
- **Count**: 5 tests

**Key test files**:
- `test_awards_and_cet_endpoints.py` - Award and CET API endpoints
- `test_summary_endpoint.py` - Summary API endpoint

## Running Tests

### Development Workflow

```bash
# Quick feedback loop during development
pytest tests/unit/ -v

# Full test suite before commits
pytest tests/ -v

# Check coverage
pytest tests/ --cov=src/sbir_cet_classifier --cov-report=term-missing
```

### Continuous Integration

```bash
# CI-friendly command (no verbose output)
pytest tests/ --cov=src/sbir_cet_classifier --cov-report=xml

# Performance testing
pytest tests/ --durations=10
```

### Test Markers

```bash
# Skip slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m "integration"
```

## Test Data

### Fixtures (`tests/fixtures/`)
- Sample award data for consistent testing
- Mock taxonomy data
- Test configuration files

### Test Database
Tests use in-memory pandas DataFrames and temporary files to avoid dependencies on external data.

## Coverage Requirements

- **Minimum coverage**: 85%
- **Current coverage**: ~90%
- **Excluded from coverage**: 
  - CLI entry points
  - Configuration loading
  - External API calls

## Troubleshooting

### Common Issues

**Missing CSV file errors**:
```bash
# Some integration tests require award_data.csv
# These tests are automatically skipped if file is missing
pytest tests/ -v  # Will show SKIPPED for missing data tests
```

**Slow test performance**:
```bash
# Run only fast tests during development
pytest -m "not slow" -v

# Profile slow tests
pytest --durations=10
```

**Import errors**:
```bash
# Ensure package is installed in development mode
pip install -e .[dev]
```

### Test Configuration

Configuration is managed via `pytest.ini`:
```ini
[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra"
testpaths = ["tests"]
```

## Writing New Tests

### Unit Test Example
```python
def test_classification_bands():
    """Test score-to-band classification logic."""
    assert band_for_score(75) == "High"
    assert band_for_score(50) == "Medium"
    assert band_for_score(25) == "Low"
```

### Integration Test Example
```python
def test_end_to_end_workflow():
    """Test complete award processing workflow."""
    # Setup test data
    awards_df = create_test_awards()
    
    # Process through pipeline
    service = AwardsService(awards_df, ...)
    result = service.list_awards(filters)
    
    # Verify results
    assert len(result.awards) > 0
    assert result.pagination.total_records > 0
```

### Contract Test Example
```python
def test_api_endpoint_response_schema():
    """Test API endpoint returns expected schema."""
    response = client.get("/awards?page=1")
    assert response.status_code == 200
    
    data = response.json()
    assert "awards" in data
    assert "pagination" in data
```

## Performance Testing

Monitor test performance to catch regressions:

```bash
# Time all tests
pytest --durations=0

# Profile memory usage (requires pytest-memray)
pytest --memray tests/integration/
```

## Best Practices

1. **Keep tests fast** - Unit tests should run in < 100ms
2. **Use descriptive names** - Test names should explain what is being tested
3. **Test edge cases** - Include boundary conditions and error cases
4. **Mock external dependencies** - Don't rely on external services
5. **Maintain test data** - Keep fixtures small and focused
6. **Check coverage** - Aim for >85% coverage on new code

---

For more details on the testing framework and patterns, see the individual test files in the `tests/` directory.
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
