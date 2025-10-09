# Quickstart — SBIR CET Applicability Assessment

## Prerequisites
- Python 3.11+
- `pip install -e .[dev]` (after project scaffolding) to obtain pandas, scikit-learn, spacy, pydantic, typer, pytest, and tooling.
- SBIR.gov bulk data ZIP available locally or accessible via HTTPS.

## Environment Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python -m spacy download en_core_web_md  # evidence extraction model
```

## Refresh & Classification
```bash
sbir-nist refresh \
  --fiscal-year-start 2020 \
  --fiscal-year-end 2024 \
  --source-url https://www.sbir.gov/sites/default/files/sbir_awards_fy2024.zip
```
- Ingests raw ZIP into `data/raw/`.
- Materializes normalized Parquet tables in `data/processed/`.
- Trains/calibrates applicability model and emits artefacts under `artifacts/`.

## Analyst Summary View
```bash
sbir-nist summary \
  --fiscal-year-start 2023 \
  --fiscal-year-end 2024 \
  --agency AF \
  --phase II
```
- Returns CET distribution with counts, obligated dollars, and share per area.
- Flags classification coverage (auto vs. manual) and taxonomy version.

## Drill-down Awards
```bash
sbir-nist awards list --cet-area quantum_sensing --page 1 --page-size 25
sbir-nist awards show --award-id AF-2023-QS-001
```
- Lists award-level applicability scores and evidence snippets.
- Shows historical assessments for a single award, including manual overrides.

## Manual Review Queue
```bash
sbir-nist review-queue list --status pending
sbir-nist review-queue resolve --queue-id <UUID> --notes "Added missing abstract"
```
- Ensures overdue items escalate before fiscal quarter close.

## Exports
```bash
sbir-nist export create \
  --fiscal-year-start 2021 \
  --fiscal-year-end 2024 \
  --agencies AF,NASA \
  --format csv
sbir-nist export status --job-id <JOB_ID>
```
- Generates CSV/Parquet exports with methodology footnotes.
- Excludes `is_export_controlled` awards from line-level output; they remain in aggregate totals.

## Notebook Validation
- Launch `jupyter lab specs/001-i-want-to/notebooks/001-analysis.ipynb`.
- Use shared service layer to reproduce summary charts, reviewer agreement metrics, and calibration plots referenced in spec success criteria.
