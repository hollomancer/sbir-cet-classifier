# Project Structure

## Source Code Organization

```
src/sbir_cet_classifier/
├── api/                    # FastAPI routes and endpoints
├── cli/                    # Typer CLI commands (sub-app structure)
│   └── commands/          # Individual command modules
├── common/                # Shared schemas, config, utilities
├── data/                  # Data ingestion, storage, and processing
│   ├── enrichment/        # External API enrichment services
│   └── external/          # Third-party API integrations
├── features/              # Domain services and business logic
├── models/                # ML models and scoring algorithms
└── evaluation/            # Metrics and validation tools
```

## Key Architectural Patterns

### CLI Structure
- **Sub-app hierarchy**: `sbir <subapp> <command>` (e.g., `sbir summary show`)
- **Command modules**: Each feature area has its own command module
- **Two invocation forms**: Module form (`python -m sbir_cet_classifier.cli.app`) and installed entrypoint (`sbir`)

### Configuration Management
- **YAML externalization**: All parameters in `config/` directory
- **Validation**: Built-in config validation via `sbir config validate`
- **Hierarchical**: taxonomy.yaml, classification.yaml, enrichment.yaml

### Data Flow
- **Input**: CSV files → **Processing**: Parquet storage → **Output**: API/CLI/Export
- **Caching**: SQLite for external API responses
- **Artifacts**: JSON logs for performance telemetry

## Testing Structure

```
tests/
├── unit/                  # Fast, isolated tests
├── integration/           # Cross-component tests
├── contract/              # API contract tests
└── fixtures/              # Shared test data
```

### Testing Conventions
- Use `@pytest.mark.integration` for data-dependent tests
- Mock at import site, not definition site
- Guard against pandas NaN/scalar iteration issues

## Data Directories

```
data/
├── raw/                   # Input CSV files
├── processed/             # Parquet files (awards, assessments, taxonomy)
└── taxonomy/              # CET taxonomy reference data

artifacts/                 # Performance logs and telemetry
config/                    # YAML configuration files
```

## Import Patterns

- **Absolute imports**: Always use full module paths
- **Common utilities**: Import from `sbir_cet_classifier.common.*`
- **Python 3.9 compatibility**: Use `typing.Optional`, not `str | None`
- **DateTime**: Use `from sbir_cet_classifier.common.datetime_utils import UTC`

## File Naming Conventions

- **Snake_case**: All Python modules and packages
- **Descriptive names**: `awardee_matching.py`, `confidence_scoring.py`
- **Test prefixes**: `test_*.py` for all test files
- **Config suffixes**: `*.yaml` for configuration files