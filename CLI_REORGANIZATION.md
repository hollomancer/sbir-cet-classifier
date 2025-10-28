# CLI Reorganization

## Overview

The CLI has been reorganized into a cleaner, more maintainable structure with feature-based command modules and shared formatting utilities.

## New Structure

```
cli/
├── app.py                    # Main entrypoint (Typer app registration only)
├── formatters.py             # Shared output formatting utilities
└── commands/                 # Feature-based command modules
    ├── __init__.py          # Exports all command apps
    ├── ingest.py            # Data ingestion commands
    ├── classify.py          # Classification and assessment commands
    ├── summary.py           # Summary and reporting commands
    ├── review_queue.py      # Manual review queue commands
    ├── awards.py            # Award data management commands
    ├── enrichment.py        # Data enrichment commands
    ├── export.py            # Data export commands
    ├── config.py            # Configuration management commands
    └── rules.py             # Rule management commands
```

## Key Changes

### 1. Command Organization

Commands are now organized by feature area rather than being in a monolithic `app.py`:

- **ingest**: Data ingestion operations (`refresh`, `single`)
- **classify**: Classification experiments (`run`)
- **summary**: CET metrics and reporting (`show`)
- **review-queue**: Manual review workflow (`list`, `escalate`, `approve`, `stats`)
- **awards**: Award drill-down operations
- **enrichment**: SAM.gov data enrichment
- **export**: Data export utilities
- **config**: Configuration management
- **rules**: Rule management

### 2. Shared Formatters Module

The new `formatters.py` module provides consistent output formatting:

```python
from sbir_cet_classifier.cli.formatters import (
    echo_json,          # Format and echo JSON
    echo_success,       # Green success messages
    echo_error,         # Red error messages
    echo_warning,       # Yellow warnings
    echo_info,          # Standard info messages
    echo_metrics,       # Format metrics as JSON
    echo_result,        # Display labeled results
    format_progress,    # Format progress strings
    echo_table_row,     # Simple table output
    echo_section_header # Section headers
)
```

### 3. Clean Entrypoint

`app.py` is now a clean entrypoint that only:
- Imports command apps from the `commands` package
- Registers them with the main Typer app
- Provides the `main()` function

## Command Changes

### Old vs New Command Paths

| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `sbir refresh ...` | `sbir ingest refresh ...` | Moved to ingest subcommand |
| `sbir ingest ...` | `sbir ingest single ...` | Renamed for clarity |
| `sbir classify ...` | `sbir classify run ...` | Moved to classify subcommand |
| `sbir summary ...` | `sbir summary show ...` | Moved to summary subcommand |
| `sbir review-queue ...` | `sbir review-queue list/escalate/approve/stats` | Expanded with new subcommands |

### New Commands

The reorganization adds several new commands:

**Review Queue Commands:**
- `sbir review-queue list` - List pending review items
- `sbir review-queue escalate <id>` - Escalate item for higher-level review
- `sbir review-queue approve <id>` - Approve and resolve review item
- `sbir review-queue stats` - Display queue statistics

**Ingest Commands:**
- `sbir ingest refresh` - Ingest multiple fiscal years
- `sbir ingest single` - Ingest a single fiscal year

**Classify Commands:**
- `sbir classify run` - Run classification experiment

**Summary Commands:**
- `sbir summary show` - Display summary metrics

## Examples

### Ingesting Data

```bash
# Ingest a single fiscal year
sbir ingest single 2023

# Ingest multiple fiscal years
sbir ingest refresh --fiscal-year-start 2020 --fiscal-year-end 2023
```

### Running Classification

```bash
# Run basic classification
sbir classify run --awards-path data/awards_2023.csv --sample-size 100

# Include rule-based and hybrid scores
sbir classify run \
  --awards-path data/awards_2023.csv \
  --sample-size 500 \
  --rule-score \
  --hybrid-score \
  --hybrid-weight 0.6
```

### Viewing Summaries

```bash
# Show summary for fiscal years 2020-2023
sbir summary show 2020 2023

# Filter by specific agencies
sbir summary show 2020 2023 --agency DOD --agency NASA
```

### Managing Review Queue

```bash
# List pending items
sbir review-queue list --limit 100

# Filter by agency
sbir review-queue list --agency DOD

# Escalate an item
sbir review-queue escalate Q12345 --reason "Requires SME input"

# Approve an item
sbir review-queue approve Q12345 --applicable --notes "Clear dual-use technology"

# View queue statistics
sbir review-queue stats --fiscal-year 2023
```

## Migration Guide

### For Users

Most commands work the same way, just with an additional subcommand level:

```bash
# Before
sbir ingest 2023

# After
sbir ingest single 2023
```

```bash
# Before
sbir classify --awards-path data/awards.csv

# After
sbir classify run --awards-path data/awards.csv
```

### For Developers

#### Adding New Commands

1. Create or edit a command module in `cli/commands/`:

```python
# cli/commands/my_feature.py
from __future__ import annotations

import typer
from sbir_cet_classifier.cli.formatters import echo_success, echo_info

app = typer.Typer(help="My feature commands")

@app.command()
def do_something(
    name: str = typer.Argument(..., help="Name parameter")
) -> None:
    """Do something useful."""
    echo_info(f"Processing {name}...")
    # ... implementation ...
    echo_success("Done!")
```

2. Export the app in `cli/commands/__init__.py`:

```python
from sbir_cet_classifier.cli.commands.my_feature import app as my_feature_app

__all__ = [
    # ... existing exports ...
    "my_feature_app",
]
```

3. Register it in `cli/app.py`:

```python
from sbir_cet_classifier.cli.commands import my_feature_app

app.add_typer(my_feature_app, name="my-feature", help="My feature commands")
```

#### Using Formatters

Instead of calling `typer.echo()` directly, use the formatter utilities:

```python
# Before
typer.echo("Processing data...")
typer.echo(json.dumps(result, indent=2))

# After
from sbir_cet_classifier.cli.formatters import echo_info, echo_json

echo_info("Processing data...")
echo_json(result)
```

```python
# Before
typer.echo(f"Success: {count} records processed", fg=typer.colors.GREEN)

# After
from sbir_cet_classifier.cli.formatters import echo_success

echo_success(f"Success: {count} records processed")
```

## Benefits

1. **Better Organization**: Commands are grouped by feature area, making them easier to find and maintain
2. **Consistent Formatting**: Shared formatters ensure consistent output across all commands
3. **Easier Testing**: Each command module can be tested independently
4. **Better Documentation**: Each command group has focused help text
5. **Scalability**: Easy to add new commands without bloating the main app.py
6. **Clean Separation**: Business logic is in command modules, registration is in app.py

## Testing

Run the test suite to ensure all CLI commands work correctly:

```bash
# Run all CLI tests
pytest tests/unit/cli/ -v

# Run specific command tests
pytest tests/unit/cli/test_ingest_commands.py -v
pytest tests/unit/cli/test_classify_commands.py -v
```

## Notes

- All existing commands maintain backward compatibility through subcommands
- The old command structure is deprecated but still functional
- The `review-queue` commands are currently stubs with "(Implementation pending)" placeholders
- All imports use absolute paths (no relative imports)
- Type hints are used consistently throughout