# Development Guide

This guide provides comprehensive information for developers working on the SBIR CET Classifier project.

## Development Setup

### Prerequisites

- Python 3.11+ (matches existing project)
- Git for version control
- Virtual environment support

### Installation

```bash
# Clone repository
git clone <repository-url>
cd sbir-cet-classifier

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Unix/MacOS
# .venv\Scripts\activate    # Windows

# Install dependencies with development tools
pip install -e .[dev]

# Download spaCy model (optional)
python -m spacy download en_core_web_md

# Install pre-commit hooks (recommended)
pre-commit install
```

### Project Structure

```
src/                              # Source code
├── sbir_cet_classifier/         # Main package
│   ├── api/                     # FastAPI routes
│   ├── cli/                     # Typer commands
│   ├── common/                  # Schemas and config
│   ├── data/                    # Ingestion and storage
│   ├── features/                # Domain services
│   ├── models/                  # ML scoring
│   └── evaluation/              # Metrics and validation
tests/                           # Test suites
├── unit/                        # Unit tests
├── integration/                 # Integration tests
└── contract/                    # API contract tests
```

## Active Technologies

- **Python 3.11+** (matches existing project)
- **requests/httpx** for API calls
- **pandas** for data processing
- **scikit-learn** pipeline for ML
- **FastAPI** for internal API
- **Typer** for CLI interface
- **pytest** for testing
- **ruff** for code quality

## Code Style & Standards

### Python Conventions
- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Maximum line length: 88 characters (ruff default)
- Use descriptive variable and function names

### Code Quality Tools

```bash
# Format code
ruff format src/ tests/

# Check code quality
ruff check .

# Run all quality checks
pre-commit run --all-files
```

### Import Organization
- Standard library imports first
- Third-party imports second
- Local/project imports last
- Use absolute imports for clarity

## Testing

### Overview

The project uses pytest for comprehensive testing with 100% pass rate (232/232 tests).

### Test Organization

#### Unit Tests (`tests/unit/`) - 130 tests
- **Purpose**: Test individual components in isolation
- **Speed**: Fast (< 100ms per test)
- **Coverage**: Core business logic, data models, utilities

**Key test files**:
- `test_applicability.py` - ML model functionality
- `test_evidence.py` - Evidence extraction logic
- `test_summary.py` - Portfolio summary calculations
- `test_ingest.py` - Data ingestion pipeline
- `test_store.py` - Parquet data storage

#### Integration Tests (`tests/integration/`) - 27 tests  
- **Purpose**: Test component interactions and workflows
- **Speed**: Medium (100ms - 1s per test)
- **Coverage**: End-to-end workflows, CLI commands, data flows

**Key test files**:
- `test_bootstrap.py` - System initialization and data loading
- `test_award_gap_flow.py` - Award analysis workflows
- `test_summary_filters.py` - Cross-system filter consistency

#### Contract Tests (`tests/contract/`) - 5 tests
- **Purpose**: Test API endpoint contracts and responses
- **Speed**: Fast (< 200ms per test)
- **Coverage**: FastAPI routes, request/response schemas

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/unit/ -v              # Unit tests only
pytest tests/integration/ -v       # Integration tests only
pytest tests/contract/ -v          # Contract tests only

# Run with coverage
pytest tests/ --cov=src/sbir_cet_classifier --cov-report=html

# Run fast tests only (development)
pytest -m "not slow" -v

# Check specific areas
pytest tests/unit/sbir_cet_classifier/data/ -v           # Data layer
pytest tests/unit/sbir_cet_classifier/features/ -v      # Feature services
pytest tests/unit/sbir_cet_classifier/models/ -v        # ML models
```

### Coverage Requirements

- **Minimum coverage**: 85%
- **Current coverage**: ~90%
- **Target**: Maintain >85% on new code

**Generate coverage reports**:
```bash
pytest --cov=src/sbir_cet_classifier --cov-report=html
open htmlcov/index.html  # View report
```

### Test Configuration

Configuration managed via `pytest.ini`:
```ini
[tool.pytest.ini_options]
minversion = "8.0"
addopts = "-ra"
testpaths = ["tests"]
```

### Writing New Tests

#### Unit Test Example
```python
def test_classification_bands():
    """Test score-to-band classification logic."""
    assert band_for_score(75) == "High"
    assert band_for_score(50) == "Medium"
    assert band_for_score(25) == "Low"
```

#### Integration Test Example
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

#### Contract Test Example
```python
def test_api_endpoint_response_schema():
    """Test API endpoint returns expected schema."""
    response = client.get("/awards?page=1")
    assert response.status_code == 200
    
    data = response.json()
    assert "awards" in data
    assert "pagination" in data
```

### Test Data & Fixtures

- **Test Datasets**: Located in `tests/fixtures/`
- **Mock Data**: In-memory pandas DataFrames and temporary files
- **Sample Data**: `award_data-3.csv` (100 realistic SBIR awards)

### Troubleshooting Tests

**Missing CSV file errors**:
```bash
# Some integration tests require award_data.csv
# These tests are automatically skipped if file is missing
pytest tests/ -v  # Will show SKIPPED for missing data tests
```

**Slow test performance**:
```bash
# Profile slow tests
pytest --durations=10

# Run only fast tests during development
pytest -m "not slow" -v
```

**Import errors**:
```bash
# Ensure package is installed in development mode
pip install -e .[dev]
```

## API Development

### Starting the Development Server

```bash
# Start FastAPI server with auto-reload
uvicorn sbir_cet_classifier.api.router:router --reload --port 8000
```

### API Testing

```bash
# Health check
curl http://localhost:8000/health

# Get summary
curl "http://localhost:8000/summary?fiscal_year_start=2023&fiscal_year_end=2024"

# List awards
curl "http://localhost:8000/awards?fiscal_year_start=2023&fiscal_year_end=2024&page=1"

# Get award detail
curl http://localhost:8000/awards/AWARD-ID

# Create export
curl -X POST http://localhost:8000/exports \
  -H "Content-Type: application/json" \
  -d '{"fiscal_year_start": 2023, "fiscal_year_end": 2024, "format": "csv"}'
```

## CLI Development

### Testing CLI Commands

```bash
# Install the CLI
pip install -e .

# Test summary command
python -m sbir_cet_classifier.cli.app summary 2023 2024 --agency AF

# Test awards commands
python -m sbir_cet_classifier.cli.app awards list \
  --fiscal-year-start 2023 \
  --fiscal-year-end 2024 \
  --page 1

# Test export commands
python -m sbir_cet_classifier.cli.app export create \
  --fiscal-year-start 2023 \
  --fiscal-year-end 2024 \
  --format csv
```

## Performance Testing

### Benchmarking

```bash
# Test SLA requirements
time python -m sbir_cet_classifier.cli.app summary 2020 2024  # Target: ≤3 min

# Load testing with locust
pip install locust
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

### Performance Monitoring

```bash
# Time all tests
pytest --durations=0

# Profile memory usage (requires pytest-memray)
pytest --memray tests/integration/

# Monitor specific functions
python -c "import cProfile; cProfile.run('your_function()')"
```

## Data Pipeline Development

### Data Processing

```bash
# Run ingestion pipeline
python ingest_awards.py

# Test with sample data
python -c "
import pandas as pd
awards = pd.read_parquet('data/processed/awards.parquet')
print(f'Loaded {len(awards)} awards')
"
```

### Configuration Management

Configuration files in `config/`:
- `taxonomy.yaml` - CET taxonomy definitions
- `classification.yaml` - Model parameters
- `enrichment.yaml` - API mappings

```bash
# Validate configuration changes
python validate_config.py
```

## Debugging

### Development Environment

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
pytest -vv --tb=long

# Run specific test with debugging
pytest tests/unit/test_example.py::test_specific -vv -s

# Enable logging in tests
pytest --log-cli-level=DEBUG
```

### Common Issues

**ImportError: cannot import name 'UTC'**
- Solution: Use `timezone.utc` instead of `UTC` for Python 3.9

**FileNotFoundError: No taxonomy versions available**
- Solution: Create taxonomy file in `data/taxonomy/`

**Service unavailable (503)**
- Solution: Configure services before using API

## Continuous Integration

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### CI Pipeline Commands

```bash
# Full CI workflow
pytest --cov --cov-report=xml
ruff check .
ruff format --check .
```

### GitHub Actions Example

```yaml
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

## Contribution Guidelines

### Development Workflow

1. **Fork/Branch**: Create feature branch from main
2. **Develop**: Implement changes with tests
3. **Test**: Ensure all tests pass locally
4. **Quality**: Run ruff formatting and checks
5. **Documentation**: Update relevant documentation
6. **Submit**: Create pull request with description

### Pull Request Requirements

- [ ] All tests pass (232/232)
- [ ] Code coverage ≥85%
- [ ] Ruff formatting applied
- [ ] Type hints added for new functions
- [ ] Documentation updated
- [ ] Performance impact considered

### Code Review Process

1. Automated checks must pass
2. Manual review by maintainer
3. Address feedback and re-test
4. Merge after approval

## Best Practices

### Code Organization

1. **Keep functions small** - Single responsibility principle
2. **Use type hints** - Improve code clarity and IDE support
3. **Document complex logic** - Add docstrings for non-obvious code
4. **Handle errors gracefully** - Provide meaningful error messages
5. **Avoid deep nesting** - Use early returns and guard clauses

### Testing Best Practices

1. **Test behavior, not implementation** - Focus on what, not how
2. **Use descriptive test names** - Test name should explain the scenario
3. **Keep tests independent** - Tests should not depend on each other
4. **Mock external dependencies** - Don't rely on external services
5. **Test edge cases** - Include boundary conditions and error scenarios

### Performance Guidelines

1. **Profile before optimizing** - Measure actual bottlenecks
2. **Use appropriate data structures** - Choose efficient collections
3. **Batch operations** - Process data in chunks when possible
4. **Cache expensive computations** - Store results of slow operations
5. **Monitor memory usage** - Be aware of data size in processing

## Resources

- [Python Style Guide (PEP 8)](https://peps.python.org/pep-0008/)
- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Typer Documentation](https://typer.tiangolo.com/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

---

**Development Status**: Active | **Test Coverage**: >85% | **Code Quality**: Ruff compliant