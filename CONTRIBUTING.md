# Contributing to SBIR CET Classifier

Thanks for your interest in improving this project! This guide covers developer setup, how to run tests, coding conventions, and where to find the relevant documentation.

If anything here is unclear or missing, open an issue or a PR to improve it.


## Quick start (development setup)

Requirements:
- Python 3.9–3.11 (project and CI support 3.9; please validate changes against it)
- macOS/Linux/WSL recommended

Create and activate a virtual environment:

```bash
# clone the repo
git clone https://github.com/<org>/sbir-cet-classifier.git
cd sbir-cet-classifier

# create a virtualenv (example with venv)
python3 -m venv .venv
source .venv/bin/activate

# install in editable mode with dev extras
pip install -U pip
pip install -e ".[dev]"

# install pre-commit hooks (recommended)
pre-commit install
```

Tips:
- If you use pyenv, set the local version to match CI.
- Keep dependencies minimal; prefer changes in extras or dev extras.


## Running the CLI locally

This project uses a Typer-based CLI with a sub-app hierarchy.

Two equivalent ways to invoke:
- Installed entrypoint (preferred for everyday usage):
  ```bash
  sbir <subapp> <command> [options]
  ```
- Python module (works everywhere, including dev checkouts):
  ```bash
  python -m sbir_cet_classifier.cli.app <subapp> <command> [options]
  ```

Common examples:
```bash
# Validate configuration YAMLs
python -m sbir_cet_classifier.cli.app config validate

# Bootstrap from a local CSV (if you have award_data.csv)
sbir ingest bootstrap --csv-path ./award_data.csv --year 2024

# Summaries
sbir summary show --fiscal-year-start 2023 --fiscal-year-end 2024
```

See the CLI guide:
- docs/cli/README.md


## Running tests

Run all tests:
```bash
pytest tests/ -q
```

Run unit-only tests:
```bash
pytest tests/unit -q
```

Run a single test module or test:
```bash
pytest tests/unit/enrichment/test_confidence_scoring.py::TestConfidenceScorer::test_uei_only_match_score -q
```

Integration tests and data:
- Some integration tests expect a large optional CSV at the repo root named `award_data.csv`.
- If the file is absent, those tests will be skipped automatically.
- We use a pytest mark `@pytest.mark.integration` for longer-running or data-dependent tests.

Pytest marks and CI guidance:
- docs/ci/troubleshooting.md


## Linting, formatting, and hooks

We use standard Python tooling (configured via pre-commit):
- Black (formatting)
- Ruff/Isort (linting/imports)
- Optional: type checking if enabled in the toolchain

Run all hooks manually:
```bash
pre-commit run -a
```

Please keep PRs formatted and lint-clean to reduce review friction.


## Coding & compatibility notes

Python compatibility:
- CI includes Python 3.9. Avoid 3.10+/3.11-only syntax in Pydantic models (e.g., `str | None`, `list[str]`).
- In models, use `typing.Optional`, `typing.List`, `typing.Dict`, etc.
- Do not import `datetime.UTC` directly (3.11+ only). Use the shared alias:
  - `from sbir_cet_classifier.common.datetime_utils import UTC`

Pydantic v2+ forward-compat:
- Prefer `model.model_dump()` over `model.dict()`

CLI structure:
- The CLI is organized as `sbir <subapp> <command>`. Tests and scripts should use this sub-app structure.
- When mocking in tests, patch symbols at the import site used by the CLI command module, not the definition site.

Pandas/DataFrame patterns:
- Avoid `DataFrame.get(...)`; that’s a dict method. Check column presence first.
- Use `.fillna(False)` before boolean indexing.
- Guard list-like iteration (coerce `NaN`/scalars to `[]` before iterating).


## Documentation

This repository includes consolidated docs. Start here:

- CLI: docs/cli/README.md
- CI troubleshooting: docs/ci/troubleshooting.md
- Configuration: docs/config/README.md
- Config & imports migration: docs/migrations/config-yaml-migration.md
- Engineering performance: docs/engineering/performance.md
- Refactoring guide: docs/engineering/refactoring/guide.md
- README (project overview): README.md

If you add a new feature or change behavior:
- Update or add documentation in the relevant doc, and link it from README.md where appropriate.


## Commit style and pull requests

Commit messages:
- Use clear, descriptive messages.
- Conventional Commits are encouraged:
  - `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`

Pull requests:
- Keep PRs small and focused (ideally < ~400 LOC net diff).
- Include tests for new behavior or bug fixes.
- Update docs for any CLI, configuration, or behavior changes.
- Add context in the PR description:
  - What changed?
  - Why? (problem being solved)
  - How was it validated? (tests, before/after measurements)

Definition of done:
- Tests pass locally and in CI.
- Lints/formatters clean (pre-commit).
- Docs updated (if relevant).
- No brittle expectations in tests (especially around timing/threshold boundaries).


## Troubleshooting

Common CI failures and how to fix them quickly:
- docs/ci/troubleshooting.md

Typical culprits:
- Tests not using sub-app CLI structure.
- Mocks applied at definition site (instead of import site).
- Pandas `.get()` misuse; NaN in boolean masks; list-like NaN iteration.
- Pydantic typing on Python 3.9 (avoid `str | None`, use `Optional[str]`).
- Confidence scoring tests not aligned with ScoreWeights/thresholds.


## Questions and help

- Open a GitHub issue if something is unclear or broken.
- Start a discussion for design changes that affect multiple components (CLI, config, schemas).
- PRs welcome for docs improvements and clarifications.

Thanks for contributing!