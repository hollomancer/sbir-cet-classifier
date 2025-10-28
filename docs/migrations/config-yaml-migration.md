# Configuration & Imports Migration Guide

This page documents breaking and noteworthy changes to:
- Configuration YAML files (e.g., `config/classification.yaml`, `config/taxonomy.yaml`)
- Code-level imports and typing that may require project-wide updates

Use this guide when upgrading the project across versions, preparing a PR to change config shapes, or reconciling local forks with the current main branch.

Audience: Developers, maintainers
Last updated: 2025-10-28


## Contents

- Versioning & policy
- Configuration migrations
  - classification.yaml schema changes
  - taxonomy.yaml changes
  - environment & storage configuration
  - validation and rollout
- Code import and typing migrations
  - Python 3.9 compatibility
  - Pydantic v2+ forward-compat
  - CLI reorganization and import-site mocking
- Recipes (copy/paste)
- Checklists


## Versioning & Policy

- The classification configuration includes a `version` field (string). We recommend semantic versioning semantics:
  - MAJOR: Breaking config shape changes
  - MINOR: Backward-compatible additions (new optional keys, extended enums)
  - PATCH: Documentation updates, default value changes (when backward compatible)
- Every change to YAML structures or expected types should:
  - Increment the config `version`
  - Provide a migration entry in this file (what changed, why, how to migrate)
  - Ship a validation rule (the CLI `config validate` must definitively fail on invalid shapes)
- Changes to code-level imports and typing (that affect build/tooling) should include:
  - A one-liner in the project CHANGELOG
  - A codemod recipe in this guide


## Configuration Migrations

### Background

The configuration folder `config/` contains the project’s runtime tuning:
- `classification.yaml`: Controls vectorizer, feature selection, classifier, calibration, domain rules (keywords, priors), scoring bands, and more.
- `taxonomy.yaml`: Defines CET entries, hierarchy, status, dates.
- Optional application/storage YAMLs: I/O roots, caches, feature flags (varies by deployment).

Validation command:
- Python module invocation (portable):  
  `python -m sbir_cet_classifier.cli.app config validate`
- Installed entrypoint (when available):  
  `sbir config validate`


### Migration Index (classification.yaml)

This index summarizes common change themes and example migration paths. If your branch includes any of these, bump the `version` and document the migration notes in your PR.

1) Score band structure (non-breaking to breaking)
- Non-breaking: Adjust band thresholds (min/max), band labels
- Breaking: Rename keys or change nesting (e.g., `scoring.bands.high -> scoring.bands.top`)
  - Migration: Provide a one-to-one mapping table; reject unknown keys in validation; default missing keys conservatively.

2) Domain signals expansion
- Adding `context_rules`: New optional key under `classification.yaml`
  - Migration: None required if optional; validation should confirm shape when present
- Expanding `agency_priors` / `branch_priors` shapes:
  - Migration: Supply defaults if new nested keys are optional; ensure new shapes are validated

3) Vectorizer / feature selection constraints
- Increasing `min_df`, introducing `max_df`:
  - Migration: Document CI/test dataset size impact; provide “small dataset” overrides (e.g., via env or test config)

4) Keyword list normalization
- Enforce consistent quoting for multi-word phrases:
  - Migration: YAML lint/format rule; validator warns on likely mistakes

5) CET ID reference strictness
- Requiring that CET IDs referenced in classification rules exist in `taxonomy.yaml`:
  - Migration: Validator error on unknown CET ID; instruct author to update taxonomy first


### Migration Index (taxonomy.yaml)

1) CET entry normalization
- `cet_id` transitions (e.g., `QuantumComputing -> quantum_computing`)
  - Migration: Provide an alias map for a transitional release or instruct a one-time update across rules; fail validation when stale IDs persist

2) Status & lifecycle
- Enforce `effective_date` and optional `retired_date` ordering
  - Migration: Validator error/warning; provide an auto-fix tool (optional)

3) Hierarchy requirements
- Require `parent_cet_id` for non-root entries
  - Migration: Add parent references or annotate root status explicitly


### Environments & Storage

Environments may define:
- Storage roots for parquet/CSV exports
- Cache directories
- Feature flags (e.g., enabling enrichment clients)

Migration best practices:
- Prefer CLI flags for temporary overrides (`--storage-dir`, `--out`)
- Use env variables for secrets and environment-specific paths
- Keep CI configs immutable or documented in this repo


### Validation & Rollout

- Always run: `python -m sbir_cet_classifier.cli.app config validate`
- PR reviewers should:
  - Inspect diffs for structural changes
  - Confirm `version` bumps when shapes change
  - Request before/after behavior notes for scoring or rule adjustments
- For large changes, consider a two-step rollout:
  1) Taxonomy update
  2) Classification rules update


## Code Import & Typing Migrations

### Python 3.9 Compatibility

CI runs include Python 3.9. Ensure code works without Python ≥3.10/3.11-only features.

1) datetime UTC usage
- DO NOT: `from datetime import UTC` (Python 3.11+)
- DO: Use a shared alias:
  ```python
  # sbir_cet_classifier/common/datetime_utils.py
  from datetime import timezone
  UTC = timezone.utc
  ```
  And import: `from sbir_cet_classifier.common.datetime_utils import UTC`

2) PEP 604 unions and builtin generics (breaks Pydantic evaluation on 3.9)
- DO NOT: `str | None`, `list[str]`, `dict[str, Any]` in Pydantic models on 3.9
- DO: `Optional[str]`, `List[str]`, `Dict[str, Any]`
  - Also add: `from typing import Optional, List, Dict, Union`

3) Pydantic v2+ forward-compat
- Replace `.dict()` with `.model_dump()`
- Keep type validators compatible with Pydantic v2 (e.g., `@field_validator`, `@model_validator`)

Codemod summary:
- `from datetime import UTC` → `from sbir_cet_classifier.common.datetime_utils import UTC`
- `X | None` → `Optional[X]` (and add typing imports)
- `list[...]` / `dict[...]` → `List[...]` / `Dict[...]` where Pydantic evaluates annotations
- `.dict()` → `.model_dump()`


### CLI Reorganization & Import-Site Mocking

The CLI now uses a Typer sub-app hierarchy:
- `sbir <subapp> <command>` (e.g., `sbir summary show`, `sbir ingest refresh`)

Test & mocking implications:
- Patch at the import site (module under test), not the original symbol’s definition module
  - Example: `sbir_cet_classifier.cli.commands.ingest.load_config` instead of patching the source in `common.config`
- CLI invocations in tests should reflect the sub-app + command structure


## Recipes

### Validate config after edits

```bash
python -m sbir_cet_classifier.cli.app config validate
# or, if installed:
sbir config validate
```

### Replace UTC imports

- Before:
  ```python
  from datetime import UTC, datetime
  ```
- After:
  ```python
  from datetime import datetime
  from sbir_cet_classifier.common.datetime_utils import UTC
  ```

### Replace PEP 604 unions (models)

- Before:
  ```python
  from pydantic import BaseModel, Field
  class Award(BaseModel):
      abstract: str | None = None
      keywords: list[str] = Field(default_factory=list)
  ```
- After:
  ```python
  from typing import Optional, List
  from pydantic import BaseModel, Field
  class Award(BaseModel):
      abstract: Optional[str] = None
      keywords: List[str] = Field(default_factory=list)
  ```

### Replace Pydantic dict

- Before: `record = item.dict()`
- After: `record = item.model_dump()`

### CLI invocation migration

- Before: `sbir config_validate`
- After: `sbir config validate`

- Before: `sbir summary_show --cet hypersonics`
- After: `sbir summary show --cet-id hypersonics`


## Checklists

### When changing classification.yaml/taxonomy.yaml
- [ ] Bump `version` for breaking shape changes
- [ ] Update this migration guide with a brief entry
- [ ] Provide a one-to-one mapping table for key renames
- [ ] Add/adjust validation rules so bad shapes fail fast
- [ ] Document before/after behavior (scoring, selection impacts)
- [ ] Run `config validate` locally and in CI

### When changing code imports/typing
- [ ] Replace `from datetime import UTC` with shared alias
- [ ] Replace PEP 604 unions/builtin generics in Pydantic models
- [ ] Replace `.dict()` with `.model_dump()`
- [ ] Update tests and mocks to patch at import-site
- [ ] Run unit & integration tests on Python 3.9 target

### When adjusting CLI
- [ ] Update docs: `docs/cli/README.md`
- [ ] Ensure tests use sub-app invocation
- [ ] Validate help/usage and examples
- [ ] Note changes in CHANGELOG


---

For questions or to propose a schema change, open a PR that:
- Adds a short entry to this guide
- Includes validation updates and tests
- Explains the expected downstream impacts (CI, data pipelines, scripts)