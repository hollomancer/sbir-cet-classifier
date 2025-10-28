# SBIR CET Classifier CLI

This is your consolidated guide to the command‑line interface (CLI) for the SBIR CET Classifier. It explains the sub‑app structure, common commands, and migration notes from the previous (flat) CLI.

Audience: Developers and power users
Goal: Enable consistent, predictable CLI usage across local development, CI, and scripted automation.


## Overview

The CLI is organized as a hierarchy of sub‑apps and commands (Typer style):

- Invocation with installed entrypoint (preferred):
  - sbir <subapp> <command> [options]
- Invocation via Python module (works anywhere):
  - python -m sbir_cet_classifier.cli.app <subapp> <command> [options]

Key characteristics:
- Sub‑app first, then command: sbir summary show …, sbir ingest bootstrap …
- All commands support --help for usage and options.
- Commands are designed to be composable in pipelines.


## Command tree (high level)

Depending on your installation, some commands may be hidden behind feature flags or configuration. The most commonly used sub‑apps are:

- summary
  - show: show a summary snapshot for CET areas and/or filters
  - list: list awards with optional filters (e.g., year range, agencies)
  - cet: show CET‑specific details (e.g., representative awards, shares)

- ingest
  - bootstrap: ingest award data from a CSV (e.g., award_data.csv)
  - refresh: fetch or rebuild local awards dataset (source may vary by config)

- enrich
  - run: run the end‑to‑end enrichment workflow (awards → assessments)
  - awardees: run awardee enrichment (historical data, profiles) when configured

- export
  - parquet: export current dataset(s) to parquet
  - csv: export subsets to CSV (e.g., awards, assessments, taxonomy views)

- config
  - validate: validate classification/config YAML schemas
  - show: print resolved configuration for inspection


Tip: Use sbir <subapp> --help to discover available commands and options, and sbir --help to view the full CLI layout.


## Common examples

- Validate classification configuration:
  - python -m sbir_cet_classifier.cli.app config validate

- Bootstrap from a local awards CSV (e.g., award_data.csv):
  - sbir ingest bootstrap --csv-path ./award_data.csv --year 2023

- Refresh local storage (source depends on your config):
  - sbir ingest refresh --force

- Run enrichment (where configured in your environment):
  - sbir enrich run --limit 500

- Summaries and drill‑downs:
  - sbir summary list --fiscal-year-start 2020 --fiscal-year-end 2024 --agencies NSF DOD
  - sbir summary show --cet-areas hypersonics quantum_computing
  - sbir summary cet --cet-id hypersonics

- Export datasets:
  - sbir export parquet --out ./data/exports/awards.parquet
  - sbir export csv --table assessments --out ./data/exports/assessments.csv


## Global patterns and options

While exact options vary by command, many follow common patterns:
- Year filters: --fiscal-year-start, --fiscal-year-end
- Agency/phase filters: --agencies, --phases
- I/O paths: --out, --storage-dir
- Execution controls: --limit, --dry-run, --force, --verbose

Configuration is typically resolved from project defaults and config files. See docs/config/README.md for details and environment‑specific overrides.


## Migration notes (flat → sub‑app CLI)

Previously, commands were invoked as a flat namespace. After CLI reorganization, they follow a sub‑app + command structure. Update usages accordingly:

- Old: sbir summary_show --cet hypersonics
- New: sbir summary show --cet-id hypersonics

- Old: sbir ingest_refresh --year 2023
- New: sbir ingest refresh --year 2023

- Old: sbir config_validate
- New: sbir config validate

Testing and mocks:
- If you patch or mock dependencies in tests, patch at the import site used by the sub‑app module (e.g., sbir_cet_classifier.cli.commands.ingest.<symbol>) rather than the original definition module. This ensures your mocks take effect when the CLI module imports the symbol.


## Local development and testing

Run commands locally with either sbir … or python -m …:
- sbir summary list --help
- python -m sbir_cet_classifier.cli.app summary list --help

Recommended testing approach:
- Unit tests: Call Typer commands with a CliRunner (Typer/Click pattern).
- Integration tests: Use subprocess or module invocation to verify end‑to‑end behavior and exit codes.
- CI: Prefer deterministic flags like --limit and --dry-run, and gate tests that depend on large datasets or external APIs.

Exit codes:
- 0 on success; non‑zero on error. Many commands log structured messages indicating the failing stage.


## Shell completion (optional)

You can enable tab completion if your shell supports it (Typer/Click feature). The exact environment variable names depend on the CLI entrypoint. A common pattern is:

- Bash:
  - eval "$(_SBIR_COMPLETE=bash_source sbir)"
- Zsh:
  - eval "$(_SBIR_COMPLETE=zsh_source sbir)"

Add to your shell profile (e.g., ~/.bashrc or ~/.zshrc) for persistence. If the above doesn’t work, consult Typer’s completion docs or your environment’s packaging/entrypoint name.


## Pipelines and scripting

Many workflows chain commands. Examples:
- Ingest → Enrich → Export:
  - sbir ingest refresh --force
  - sbir enrich run --limit 2000
  - sbir export parquet --out ./data/exports/awards.parquet

- CSV bootstrap → Validate → Summary:
  - sbir ingest bootstrap --csv-path ./award_data.csv --year 2024
  - sbir config validate
  - sbir summary show --fiscal-year-start 2023 --fiscal-year-end 2024


## Troubleshooting

- “No such command”:
  - Ensure you included the sub‑app: sbir <subapp> <command> …
  - Check sbir --help and sbir <subapp> --help.

- “Validation failed” (config):
  - Run python -m sbir_cet_classifier.cli.app config validate and fix indicated lines. See docs/config/README.md.

- External API errors:
  - Ensure credentials or environment variables are set (if your config requires them).
  - Prefer running with --limit during development to isolate issues quickly.

- Dataset‑dependent tests:
  - Some integration tests skip if large CSVs are not present. Provide the file (e.g., award_data.csv) or accept the skip in CI. See test logs for the expected path.


## Backwards compatibility checklist

- Replace flat commands with sub‑app style (one token).
- Update scripts and CI jobs to include the sub‑app token.
- Adjust mocks to patch the symbol in the CLI command module where it’s imported.
- Re‑align test expectations if command outputs or logging changed slightly due to reorganization.


## Related documentation

- Configuration: docs/config/README.md
- CI troubleshooting: docs/ci/troubleshooting.md
- Performance considerations: docs/engineering/performance.md
- Refactoring guidelines: docs/engineering/refactoring/guide.md


## FAQ

- Q: Do I have to install the package to use the CLI?
  - A: No. You can always use python -m sbir_cet_classifier.cli.app … during development. For users, an installed sbir entrypoint is more convenient.

- Q: Where do commands read/write data?
  - A: Paths are controlled by configuration and flags (e.g., --storage-dir, --out). See docs/config/README.md.

- Q: How do I see the full CLI structure?
  - A: sbir --help and sbir <subapp> --help.

- Q: Is there a dry‑run?
  - A: Many commands support --dry-run or no‑op modes. Check command‑specific help.


---

Last updated: Consolidated CLI guide (sub‑app hierarchy, examples, migration notes)