# CI Troubleshooting Guide

This document consolidates the most frequent CI issues in this repo and how to fix them quickly. It prioritizes root-cause explanations and durable fixes.

Audience: contributors and maintainers
Scope: unit/integration test failures, Python compatibility, CLI/test structure, data/model pitfalls


## Quick checklist (when CI turns red)

1) Read the first failure in pytest’s output. Fix the first red, re-run.
2) Reproduce locally:
   - Pin Python to CI’s version.
   - Run: `pytest tests/ -q -k <failing-test-name>`
3) If it’s a CLI or mock issue, check:
   - Typer sub-app invocation (sbir <subapp> <command>)
   - Patch targets at import-site, not definition-site
4) If it’s pandas or exporter code:
   - Check `.get()` misuse on DataFrames
   - Handle NaN booleans with `.fillna(False)`
   - Guard list-like fields before iteration
5) If it’s model/training:
   - Ensure enough docs for TF-IDF + feature selection
6) If it’s a naming/fuzzy match test:
   - Account for normalization → exact matches
7) If it’s confidence-score expectations:
   - Align expected scores with implemented weights
8) Python 3.9 compatibility:
   - Replace `datetime.UTC` with a central UTC alias
   - Replace PEP 604 unions and builtin generics in Pydantic models
9) Integration data:
   - Tests expect `award_data.csv` (optional), skip if missing
10) Warnings:
   - Register pytest marks
   - Replace Pydantic `.dict()` with `.model_dump()`
   - Decide whether to filter or fix sklearn warnings


## Common failures and fixes

### 1) CLI sub-app reorganization (Typer)
Symptoms:
- “No such command”
- CLI tests failing after reorg

Fix:
- Commands are invoked as `sbir <subapp> <command>`, e.g.:
  - `sbir summary show …`
  - `sbir ingest refresh …`
- Update tests and docs accordingly.
- When mocking, patch the symbol in the module where it is imported by the sub-app command (import-site), not the source definition.

Tip:
- Use `python -m sbir_cet_classifier.cli.app <subapp> <command>` in tests for portability.


### 2) Mocking and patching at the correct import site
Symptoms:
- Mocks don’t take effect
- Unexpected API calls are made

Fix:
- Patch the symbol where the CLI/test imports it, e.g.:
  - `sbir_cet_classifier.cli.commands.ingest.load_config`
  - `sbir_cet_classifier.features.enrichment.NIHClient` (where used)
- For functions that pass kwargs through (e.g., pagination with `offset`, `limit`, `start_date`, `end_date`), make test doubles accept `*args, **kwargs`:
```python
def mock_paginated_call(uei, *args, **kwargs):
    offset = kwargs.get("offset", 0)
    limit = kwargs.get("limit", 100)
    ...
```


### 3) Pandas/exporter pitfalls
Symptoms:
- Attribute errors like `DataFrame` object has no attribute `get`
- Boolean indexing raises due to NaN
- Iteration over NaN in list-like columns

Fix patterns:
- Replace `df.get("col", default)` with column checks:
```python
if "col" in df:
    ...
```
- When using boolean masks, ensure `.fillna(False)`:
```python
mask = df["is_export_controlled"].fillna(False)
```
- For list-like fields that may contain NaN:
```python
vals = row.get("supporting_cet_ids")
if not isinstance(vals, list):
    vals = []
```
- Ensure taxonomy includes CET IDs used in assessments (tests should generate consistent taxonomy fixtures).


### 4) ML/training constraints in tests
Symptoms:
- TF-IDF or feature selection raises errors due to too few docs
- `k` greater than `n_features` warnings

Fix:
- Increase sample sizes in tests to satisfy `min_df` and feature selection.
- Accept sklearn warnings (non-fatal) or reduce `k` for small test datasets.


### 5) Name normalization vs fuzzy matching
Symptoms:
- Tests expect fuzzy match but get exact match

Cause:
- Normalization strips punctuation and business suffixes (LLC, Inc).
- Small differences normalize to identical strings → exact match.

Fix:
- Relax tests to accept `exact_name` when normalization collapses variants.
- For stricter fuzzy behavior, consider token-based or char n-gram similarity (out of scope for CI fixes).


### 6) Confidence scoring expectations
Default weights:
- UEI match: +0.5
- Name exact: +0.3
- Name similarity: `similarity * 0.2`
- Award number match: +0.2
- Address similarity: `similarity * 0.1`
Thresholds:
- high ≥ 0.8, medium ≥ 0.5, low < 0.5

Symptoms:
- Tests expecting higher scores than possible
- Threshold assertions fail near boundaries

Fix:
- Align test expectations with the weights:
  - UEI-only (with small name_similarity) → ~0.5–0.6 (medium)
  - Name-only exact → 0.3 (low)
  - Fuzzy-only (0.85 sim) → 0.85*0.2=0.17 (low)
- For threshold tests, avoid boundary (0.5) flakiness; choose factors that clearly exceed thresholds.


### 7) Python 3.9 compatibility (CI matrix)
Symptoms:
- `ImportError: cannot import name 'UTC' from 'datetime'`
- Pydantic type evaluation errors on `str | None`, `list[str]`, `dict[str, Any]`

Fix:
- Provide a central UTC alias:
```python
# common/datetime_utils.py
from datetime import datetime, timezone
UTC = timezone.utc
```
- Import `UTC` from that helper instead of `from datetime import UTC`.
- Replace PEP 604 unions and builtin generics in Pydantic models:
  - Use `Optional[T]`, `Union[...]`, `List[T]`, `Dict[K, V]`.
- Replace `.dict()` with `.model_dump()` to remove deprecation warnings (Pydantic v2→v3 ready).


### 8) Integration data and gating
Symptoms:
- Tests fail or skip due to missing CSV

Fix:
- Tests expect `award_data.csv` at repo root; integration tests should skip if missing.
- Keep long/large data optional; CI can run unit-only or gated integration via marks/env.


### 9) Pytest marks and warnings
Symptoms:
- `PytestUnknownMarkWarning: integration`
- Noisy but expected sklearn warnings; deprecated APIs

Fix:
- Add `pytest.ini` with mark registration:
```ini
[pytest]
markers =
    integration: marks tests as integration (may require data or external services)
```
- Filter or document expected warnings if needed.
- Replace deprecated calls, e.g., `.dict()` → `.model_dump()` and deprecated storage imports where feasible.


## Reproducing CI locally

- Match Python version (e.g., `pyenv local 3.9.18`).
- Install exact dependencies (use lockfile or `pip install -e .[dev]`).
- Run subsets:
  - `pytest -q -k test_name`
  - `pytest tests/unit -q`
- For CLI tests, prefer module invocation:
  - `python -m sbir_cet_classifier.cli.app summary --help`


## Durable improvements (recommended)

- Add/maintain `pytest.ini`:
  - register `integration` mark
  - optionally narrow warnings/filters
- Pre-commit hooks for:
  - Import-site patching patterns (lint rule or guidance)
  - Prevent direct `from datetime import UTC`
- Unit tests for:
  - Export weight calculation and non-list `supporting_cet_ids` handling
  - Batch processor save paths and NaN-safe operations
- README/CLI docs:
  - Make sub-app structure explicit, with examples
- Centralize date/time handling via `common/datetime_utils.py`


## Quick fix recipes

- Pagination mock with kwargs:
```python
def mock_paginated_call(uei, *args, **kwargs):
    offset = kwargs.get("offset", 0)
    limit = kwargs.get("limit", 100)
    if offset == 0:
        return {"awards": [{"id": i} for i in range(100)], "totalRecords": 150}
    elif offset == 100:
        return {"awards": [{"id": i} for i in range(100, 150)], "totalRecords": 150}
    return {"awards": [], "totalRecords": 150}
```

- NaN-safe boolean masks:
```python
mask = df["is_export_controlled"].fillna(False)
safe_df = df[~mask]
```

- Guard list-like iteration:
```python
vals = row.get("supporting_cet_ids")
vals = vals if isinstance(vals, list) else []
for v in vals:
    ...
```

- Confidence thresholds (clear bands):
```python
# medium: name_exact + small address
factors = {NAME_EXACT: True, ADDRESS_SIMILARITY: 0.2}  # 0.3 + 0.02 = 0.32 (still low)
# better: add award number for medium
factors = {NAME_EXACT: True, AWARD_NUMBER_EXACT: True, ADDRESS_SIMILARITY: 0.2}  # 0.52 (medium)
```


## FAQ

- Q: Why does my fuzzy-only test never reach “medium”?
  - A: With defaults, name_similarity is weighted at 0.2; even 0.9 similarity yields 0.18 total without other factors.

- Q: Why does my mock not intercept the call?
  - A: Patch at the import site used by the module under test, not the original definition module.

- Q: CI fails only on Python 3.9—why?
  - A: `datetime.UTC` is Python 3.11+. Use a shared `UTC` alias and older typing constructs for Pydantic models.

- Q: Integration tests are skipped—how do I force-run them?
  - A: Provide the optional dataset (award_data.csv) and/or add a CI job that downloads it. Otherwise, maintain them as gated tests using `@pytest.mark.integration`.


---

Last updated: Consolidated CI troubleshooting (weights, CLI sub-app, pandas/NaN, Python 3.9)