# Configuration Guide

This is the consolidated source of truth for how configuration works in the SBIR CET Classifier project. It explains what can be configured, where the configuration lives, how to validate changes, and how to roll out updates safely.

Audience: developers, analysts, program staff  
Scope: configuration files in `config/` and how they are used in the CLI and services


## Contents

- Configuration model and precedence
- Files in `config/` and what they control
  - `classification.yaml`
  - `taxonomy.yaml`
  - application/storage settings (if present)
- Validating configuration changes
- Safe-edit guidelines and examples
- Environments and overrides (local, CI, prod)
- Change management and rollout
- Migration notes and YAML schema changes


## Configuration model and precedence

At runtime, configuration is resolved from multiple sources. The usual precedence (lowest → highest) is:

1) Built-in defaults (library/package defaults)  
2) Files in `config/` (e.g., `classification.yaml`, `taxonomy.yaml`, app/storage YAML if present)  
3) Environment variables (e.g., to override paths/flags)  
4) CLI flags (command-specific overrides)

Not all commands use all layers; some rely only on core YAML files and runtime flags. When in doubt, run with `--help` or `config show` to inspect what a command is reading.


## Files in `config/` and what they control

### 1) `classification.yaml`

This file controls the end-to-end classification behavior:

- Model parameters
  - TF‑IDF vectorizer (ngram_range, max_features, min_df, max_df)
  - Feature selection (enabled, method, k)
  - Classifier settings (e.g., logistic regression: max_iter, solver, class_weight)
  - Calibration (enabled, method, cv, min_samples_per_class)
- Scoring
  - Score bands: High / Medium / Low (0–100 scale)
  - Max number of supporting CETs to return
- Domain stop words (terms to ignore)
- Rule-based signals
  - Agency and branch priors (boosts for certain CETs)
  - CET keyword sets (core, related, negative)
  - Context rules (keyword co-occurrence triggers with boosts)

Changes here typically do not require code changes; they take effect the next time you run the CLI or service.

See “Safe-edit guidelines” below for examples and formatting tips.


### 2) `taxonomy.yaml`

This file defines the CET taxonomy that the classifier references:

- CET entries (cet_id, name, definition)
- Parent-child relationships (if applicable)
- Versioning and effective/retired dates
- Status (active/retired)

Important:
- CET IDs referenced in `classification.yaml` (e.g., in priors, keyword rules) must exist here.
- If you add a new CET in the taxonomy, you likely need to augment `classification.yaml` to give it useful signals (keywords, priors, etc.).


### 3) Application / storage settings (if present)

Some deployments manage application- or storage-specific configuration via YAML (e.g., `app.yaml`, `storage.yaml`) or environment variables:

- Storage roots (where parquet/CSV are persisted)
- Cache directories for intermediate artifacts
- Feature toggles for optional integrations
- API base URLs/keys (often via env vars, not checked into the repo)

These settings vary by environment. For CI and local dev, sensible defaults are often sufficient, and commands may allow explicit paths (e.g., `--out`, `--storage-dir`) to avoid editing global config.


## Validating configuration changes

After editing any YAML in `config/`, run:

- Via Python module (portable in all environments):
  - `python -m sbir_cet_classifier.cli.app config validate`

- If the `sbir` entrypoint is installed:
  - `sbir config validate`

You should see ✅ on success. If you see ❌, fix the indicated line(s) and re-run. Tip: make one change at a time, validate, then repeat.


## Safe-edit guidelines (with examples)

These best practices help avoid YAML errors and subtle behavior regressions.

- Use two spaces for indentation (never tabs).
- Keep key names exactly as shown by the schema.
- CET IDs should be lowercase snake_case (e.g., `quantum_computing`).
- Quote multi-word phrases in keyword lists: `"quantum error correction"`.
- Keep numbers as integers (no quotes).
- Avoid trailing spaces and rogue punctuation (e.g., stray colon).
- Do not remove entire sections unless you know they are unused.

Common examples in `classification.yaml`:

1) Adjust classification bands:

```
scoring:
  bands:
    high:
      min: 80
      max: 100
      label: High
    medium:
      min: 50
      max: 79
      label: Medium
    low:
      min: 0
      max: 49
      label: Low
```

2) Add/tune agency priors:

```
agency_priors:
  National Science Foundation:
    _all_cets: 5
  Department of Defense:
    hypersonics: 20
```

3) Add CET keywords:

```
cet_keywords:
  quantum_computing:
    core:
      - "quantum computing"
      - "quantum algorithm"
    related:
      - qubit
      - "quantum circuit"
    negative:
      - "quantum chemistry"
```

4) Add a context rule:

```
context_rules:
  medical_devices:
    - [["ai", "diagnostic"], 20]
```

Tip: For small data/test runs, ensure `vectorizer.min_df` and feature selection `k` are compatible with the number of available documents (CI tests often run tiny samples).


## Environments and overrides

- Local development
  - Keep working YAMLs in `config/`.
  - Use CLI flags to temporarily override paths/limits without editing shared files.
  - Use the module entrypoint when not installed: `python -m sbir_cet_classifier.cli.app …`.

- CI
  - Prefer immutable configs or environment-scoped substitutions (e.g., `SBIR_*` env vars).
  - Gate large-data integration tests or provide artifacts explicitly.
  - Validate configuration as part of pre-merge checks.

- Production
  - Manage secrets (API keys) via environment variables or a secret manager—do not commit credential values into YAML.
  - Only promote versioned configurations once validated.


## Change management and rollout

- Commit message should explain “what and why” (e.g., band thresholds changed, added keywords, tuned priors).
- Include validation output or a note that you ran `config validate`.
- Coordinate with reviewers to confirm the effect on known examples (before/after).
- For large changes (e.g., taxonomy updates), consider a two-step rollout:
  1) Add taxonomy entries.
  2) Add classification signals and tune thresholds.

- For data-linked tests and demos, align docs and scripts with the current canonical CSV name (`award_data.csv`). Some tests skip if it’s not present; that is expected in CI unless provided by the job.


## Migration notes and YAML schema changes

When configuration shapes evolve (key names, structures), you’ll need a guided migration. See:

- `docs/migrations/config-yaml-migration.md`

That document tracks:
- Schema version changes
- Required vs optional fields over time
- One-to-one key renames or structural transformations
- Short “recipes” for common breaking changes


## FAQ

- Can I add a new CET only in `classification.yaml`?
  - No—add to `taxonomy.yaml` first; then wire signals in `classification.yaml`.

- What if my change makes the classifier too “hot” (many highs)?
  - Lower boosts, adjust band thresholds, and re-validate on a representative sample.

- How do I see what the CLI is actually using at runtime?
  - Prefer a `config show` command if available in your version, or run with verbose logging and inspect resolved settings.

- Do I need to restart anything after changing YAML?
  - For CLI commands, no—changes take effect on the next invocation. For persistent services, restart the process/pod.


## Quick reference

- Validate configuration:
  - `python -m sbir_cet_classifier.cli.app config validate`

- Typical edit order for a new CET:
  1) Add to `taxonomy.yaml`
  2) Add keywords/prior/context rules in `classification.yaml`
  3) Validate and test on a small sample
  4) Adjust thresholds if needed

- Prefer `award_data.csv` naming for large CSVs referenced by integration tests (tests will skip if the file is absent).


---

Last updated: Consolidated configuration guide (merged and linked to YAML migration)