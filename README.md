# SBIR CET Classifier

This project analyses Small Business Innovation Research (SBIR) awards and aligns them to critical and emerging technology (CET) areas. It provides tooling to ingest SBIR.gov bulk datasets, score award applicability, surface analyst workflows (summaries, drill-downs, exports), and manage manual review queues in line with the feature specification stored in `specs/001-i-want-to/`.

## Repository Layout

- `src/sbir_cet_classifier/` – Python package split into `data`, `features`, `models`, `evaluation`, `common`, `cli`, and `api` modules.
- `tests/` – Unit, integration, and contract tests mirroring the source tree.
- `specs/001-i-want-to/` – Active feature specification, plan, research, design artefacts, and tasks.
- `artifacts/`, `data/raw/`, `data/processed/` – Default locations for ingested datasets and generated model outputs.

## Getting Started

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .[dev]
   python -m spacy download en_core_web_md
   ```
2. Review the current implementation plan and task list in `specs/001-i-want-to/` before coding.
3. Use the Typer CLI (`python -m sbir_cet_classifier.cli.app`) and FastAPI router stubs as entry points while iteratively implementing the planned tasks.

## Development Workflow

The repository follows the constitution in `.specify/memory/constitution.md`. Key principles include:
- Modular Design
- Consistent Dual Interfaces: CLI and API
- Test-Driven Development
- Code Quality through Static Analysis
- Specification-Driven Development
- Performance Requirements

Refer to `specs/001-i-want-to/quickstart.md` for deeper usage notes once the feature set is implemented.
