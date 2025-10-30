# Technology Stack

## Core Technologies

- **Python 3.11+**: Primary language (supports 3.9+ for compatibility)
- **pandas + pyarrow**: Data processing with Parquet storage format
- **scikit-learn**: ML pipeline (TF-IDF vectorization, logistic regression, calibration)
- **spaCy**: NLP for evidence extraction (requires `en_core_web_md` model)
- **Pydantic v2**: Data validation and serialization
- **PyYAML**: Configuration management

## Framework Stack

- **CLI**: Typer with Rich formatting for terminal output
- **API**: FastAPI with uvicorn (internal-only, no authentication)
- **Testing**: pytest with coverage tracking
- **Code Quality**: ruff for linting and formatting

## Build System

Uses modern Python packaging with `pyproject.toml`:

```bash
# Development setup
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

# Install spaCy model (optional, for evidence extraction)
python -m spacy download en_core_web_md
```

## Common Commands

```bash
# Testing
pytest tests/ -v                    # All tests
pytest tests/unit/ -v               # Unit tests only
pytest tests/integration/ -v        # Integration tests
pytest --cov=src/sbir_cet_classifier --cov-report=html  # With coverage

# Code quality
ruff format src/ tests/             # Format code
ruff check src/ tests/              # Lint code
pre-commit run -a                   # Run all hooks

# CLI usage (two equivalent forms)
python -m sbir_cet_classifier.cli.app <command>  # Module form
sbir <command>                      # Installed entrypoint

# API server
uvicorn sbir_cet_classifier.api.router:router --reload --port 8000
```

## Configuration

- **YAML-based**: All configuration externalized to `config/` directory
- **Validation**: Built-in config validation via CLI
- **Environment Variables**: Optional overrides for data paths and performance tuning

## Data Storage

- **Parquet format**: Primary storage for processed data
- **SQLite**: Caching layer for external API data
- **CSV**: Input format for raw award data