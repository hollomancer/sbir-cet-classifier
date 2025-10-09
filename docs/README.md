# Documentation

## Core Documentation

- **[../README.md](../README.md)** - Project overview and quick start
- **[../GETTING_STARTED.md](../GETTING_STARTED.md)** - Usage examples and common queries  
- **[../TESTING.md](../TESTING.md)** - Testing guide and best practices

## Technical Documentation

- **[PERFORMANCE_OPTIMIZATIONS.md](PERFORMANCE_OPTIMIZATIONS.md)** - Performance improvements and benchmarks
- **[../specs/001-i-want-to/](../specs/001-i-want-to/)** - Detailed design specifications

## Archive

- **[archive/](archive/)** - Historical documentation and reports
  - **[archive/cleanup-reports/](archive/cleanup-reports/)** - Security cleanup and refactoring reports
  - **[archive/README.md](archive/README.md)** - Archive index and descriptions

## Quick Reference

### Getting Started
```bash
# Install and run demo
pip install -e .[dev]
python -c "import pandas as pd; print(pd.read_parquet('data/processed/awards.parquet').info())"
```

### Running Tests
```bash
pytest tests/ -v
```

### API Server
```bash
uvicorn sbir_cet_classifier.api.router:router --reload
```

### CLI Commands
```bash
python -m sbir_cet_classifier.cli.app summary --fiscal-year-start 2023
python -m sbir_cet_classifier.cli.app awards list --page 1
```
