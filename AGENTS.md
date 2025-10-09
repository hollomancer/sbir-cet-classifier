# Repository Guidelines

Use this guide as the checklist for onboarding agents and keeping the repository healthy between spec cycles.

## Project Structure & Module Organization
- `src/sbir_cet_classifier/` contains the Python package, split into `data/`, `features/`, `models/`, and `evaluation/` modules so training, feature engineering, and assessment stay isolated.
- Specs live under `specs/NNN-short-slug/` with `spec.md`, `plan.md`, `tasks.md`, and any `contracts/` kept in lockstep; update templates in `.specify/templates/` before re-running the scaffolding scripts.
- Tests mirror the package layout in `tests/unit/` and `tests/integration/`, while shared fixtures sit in `tests/fixtures/`.
- Park raw corpora and large checkpoints in `data/raw/` or `artifacts/`; commit only metadata or lightweight exemplars and lean on git-lfs when necessary.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` builds a disposable Python 3.11+ environment.
- `pip install -e .[dev]` installs the package with linting, testing, and notebook extras.
- `pytest -m "not slow"` covers the fast suites; append `-m slow` when validating retraining or long-running experiments.
- `bash .specify/scripts/bash/create-new-feature.sh "model calibration"` followed by `bash .specify/scripts/bash/setup-plan.sh specs/00x-model-calibration` spins up the next spec workspace.

## Coding Style & Naming Conventions
- Use 4-space indentation, annotate all public functions, and prefer `dataclass` or `pydantic` models for structured payloads.
- Run `ruff format` then `ruff check --select ALL --ignore N999`; adjust ignores in `pyproject.toml`, not inline.
- Modules and files use `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE`, and notebooks follow their spec ID (e.g., `000-baseline.ipynb`).

## Testing Guidelines
- Write fixtures for synthetic datasets, store gold labels in `tests/fixtures/`, and mirror package names in test modules.
- Hold statement coverage at ≥85%; document new behaviours in the spec’s “Independent Test” section and reference them in test docstrings.

## Commit & Pull Request Guidelines
- Use imperative, ≤50-character subjects like `Add tfidf vectorizer pipeline`, with bullet bodies to explain schema or notebook shifts.
- Reference the active spec folder in every PR, summarise data sources touched, enumerate generated artefacts, and attach metrics or screenshots when visual confirmation matters.
- Request review only after `ruff`, `pytest`, and `check-prerequisites.sh --require-tasks --include-tasks` all pass locally.

## Security & Configuration Tips
- Keep credentials and large private datasets out of the repo; prefer environment variables and `.env.example` patterns.
- Restrict experiments with external data to worktrees acknowledged in the relevant spec, and record any new sources in the spec’s data hygiene notes.
