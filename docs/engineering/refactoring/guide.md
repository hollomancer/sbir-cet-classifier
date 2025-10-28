# Refactoring Guide

This guide consolidates our refactoring principles, playbooks, and codebase-specific opportunities. Use it as a living reference for designing, planning, and executing safe, incremental improvements that reduce complexity and prevent regressions.

Audience: engineers and maintainers
Scope: Python 3.9+ compatibility, CLI (Typer) commands, data/ML pipeline, exporter, enrichment, tests/CI

---

## Goals

- Make the code easier to change tomorrow than it is today.
- Improve correctness and performance without altering externally observable behavior.
- Reduce incidental complexity by consolidating patterns and removing duplication.
- Establish guardrails (tests, types, linters) that make future refactors cheaper.

---

## Principles

- Incrementality first: prefer a series of small, reversible changes over large rewrites.
- Behavior preservation: write/adjust tests to lock in behavior before moving code.
- Separate policy from mechanism: separate “what” (business rules) from “how” (I/O, frameworks).
- Strangle pattern: wrap old flows with a façade, implement new modules alongside, gradually swap call sites.
- Single source of truth: deduplicate configuration, algorithms, helpers, and docs.
- Prefer composition over inheritance; explicit over implicit; pure over side-effectful.

---

## Planning checklist

Before you change code, confirm these:

1) Scope and intent
- What’s the target pain (API confusion, performance, duplication, unsafe typing)?
- Can we split the work into 2–4 small PRs?
- What invariant tests do we need to lock current behavior?

2) Safety rails
- Tests exist for the affected paths (unit + key integration). If not, add them first.
- Add logging around inputs/outputs of modules that will move.
- Add type hints (even partial) to the public functions you’ll touch.

3) Blast radius and rollout
- Identify downstream modules and teams that rely on this.
- Document migration notes in the PR (what moved, new APIs, deprecated paths).
- Provide a fallback or adapter for at least one release (when practical).

---

## House rules

- Keep refactors mechanical when possible (codemod-friendly).
- Keep PRs ≤ ~400 LOC net change unless there’s a strong reason not to.
- Maintain green tests at every step; prefer feature flags for behavior changes.
- Update docs when APIs or CLIs move; remove redundant documents and dead code.
- Use conventional commits with clear scopes: `refactor:`, `chore:`, `test:`, `docs:`.

---

## Anti-patterns to eliminate

- Patching at the wrong import site in tests (mocks never take effect).
- Using `DataFrame.get()` or dict-style patterns on pandas DataFrames.
- Iterating Python-side over list-like columns without NaN guards.
- Densifying sparse matrices inadvertently in ML pipelines.
- Direct imports of `datetime.UTC` (Python 3.11+) and PEP 604 unions in models on Python 3.9.
- Broad, stateful fixtures that create cross-test coupling.

---

## Mechanical refactors (safe “wins”)

These are low-risk changes that improve reliability and compatibility.

1) Timezone and typing compatibility
- Replace `from datetime import UTC` with a central alias:
  - `from sbir_cet_classifier.common.datetime_utils import UTC`
- Replace PEP 604 unions and builtin generics in Pydantic models:
  - `str | None` → `Optional[str]`, `list[str]` → `List[str]`, `dict[str, Any]` → `Dict[str, Any]`
- Replace `model.dict()` with `model.model_dump()` (Pydantic v2+ forward-compatible).

2) Pandas correctness
- Replace `df.get("col", default)` with `"col" in df` + direct selection.
- Always apply `.fillna(False)` before boolean indexing:
  - `mask = df["is_export_controlled"].fillna(False)`
- Normalize list-like columns:
  - `vals = row.get("supporting_cet_ids"); vals = vals if isinstance(vals, list) else []`

3) Confidence scoring tests alignment
- Ensure test expectations reflect actual `ScoreWeights` and thresholds.
- Avoid thresholds at exact boundaries (e.g., 0.5) to reduce float flakiness.

4) CLI consistency (Typer sub-apps)
- Migrate flat commands to `sbir <subapp> <command>`.
- Adjust tests to invoke sub-apps and patch at import site.

---

## Architecture guidelines

- CLI (adapters) should be extremely thin: parse args → call service functions → format output.
- Services (domain/application layer) should be pure or side-effect-light; take inputs, return outputs.
- I/O modules (storage, HTTP clients, caches) should be pluggable and mockable; one responsibility per module.
- Keep data models (Pydantic) in `common`/`data` packages; avoid circular imports by depending upward only through interfaces/protocols.
- Centralize cross-cutting concerns: datetime/UTC handling, logging utilities, serialization.

---

## Refactoring playbooks

### 1) CLI (Typer) re-organization

Symptoms:
- Confusing invocation, repeated CLI logic, tight coupling with I/O.

Steps:
- Extract command logic into pure functions in services/modules.
- Keep CLI functions as thin wrappers (parse → call → print).
- Introduce `--limit`, `--dry-run`, `--verbose` flags consistently.
- Ensure tests call service functions directly for unit coverage, and use Typer `CliRunner` for CLI-level tests.
- Patch mocks at the CLI command module import site.

Outcome:
- Better testability, clearer separation, stable scripts/automation.

---

### 2) Exporter vectorization

Symptoms:
- Slow loops, fragile handling of NaNs and lists.

Steps:
- Convert per-row logic to vectorized transforms with `map`, `fillna`, `explode`, and `groupby`.
- Precompute taxonomy maps (`set_index` + `to_dict`) once per run.
- Guard list-like columns: coerce to lists, drop NaNs early.
- Ensure any filtering mask is NaN-safe: `.fillna(False)`.

Outcome:
- 10–100× speedups on large frames, fewer edge-case bugs.

---

### 3) Enrichment and caching seams

Symptoms:
- Hard-to-test HTTP calls, repeated requests, unclear failure modes.

Steps:
- Introduce thin HTTP client interfaces and a cache layer (e.g., SQLite).
- In services, depend on interfaces (protocols) rather than concrete clients.
- Batch calls where possible; add circuit-breaker/backoff if needed.
- Add structured logs for “miss” vs “hit” with counts and durations.

Outcome:
- Faster, deterministic tests; clearer prod behavior; fewer flaky failures.

---

### 4) ML pipeline hygiene

Symptoms:
- Feature selection errors on small test datasets; dense conversions.

Steps:
- Gate `k` by `n_features` for small datasets; log when adjusted.
- Keep sparse matrices through the pipeline; avoid `.toarray()`.
- Validate `min_df`/`max_df` settings vs dataset size (tests vs prod).
- Add sanity checks/logs: feature counts, sparsity, class balance.

Outcome:
- Robust tests; stable training; predictable performance.

---

### 5) Confidence scoring and thresholds

Symptoms:
- Tests assume scores that don’t match configured weights; fragile thresholds.

Steps:
- Document default weights and thresholds in code comments and docs.
- Adjust tests to assert ranges consistent with implemented math.
- Avoid proximity to thresholds; include margin in test inputs.

Outcome:
- Stable scoring tests; self-documenting behavior.

---

## Example refactor plans

1) “Fix slow exporter and inconsistent CET weights” (2–3 PRs)
- PR1: Add unit tests for exporter weight calc and NaN-safe handling. Add taxonomy map helper.
- PR2: Replace row loops with vectorized `explode` + `map` + `groupby`. Add logging and docstring examples.
- PR3: Remove any duplicated code and dead branches, update docs.

2) “Make CLI ingestion testable and reliable” (2 PRs)
- PR1: Move business logic into a `IngestionService`. Keep CLI as thin wrapper. Add unit tests for the service.
- PR2: Switch tests to patch import-sites; use `CliRunner` for CLI-only tests. Add `--limit`, `--dry-run`.

3) “Python 3.9 compat and Pydantic forward-compat” (1–2 PRs)
- PR1: Add shared `UTC` alias; switch imports; replace PEP 604 unions and built-in generics in models.
- PR2: Replace `.dict()` calls with `.model_dump()`; update integration tests and docs.

---

## Testing strategy during refactors

- Golden tests for pure transformations (input → output snapshots) with small fixtures.
- Property tests for idempotent transformations (e.g., normalize → apply twice == once).
- Contract tests for public APIs/CLI: assert schema, status codes, exit codes, key fields.
- Performance smoke tests on representative samples (track durations across PRs).
- Avoid brittle tests that assert internal call order; test outcomes, not implementation details.

---

## Logging and observability

- Add structured logs (JSON) at key module boundaries:
  - Inputs/outputs (counts, sizes), durations, feature counts, cache hits/misses.
- Keep a simple JSON log manager for “latest run” snapshots in local dev.
- Avoid per-row logs in hot paths; prefer summarized counters.

---

## Tooling and automation

- Pre-commit hooks:
  - Black/ruff/isort (style, import order, low-risk fixes).
  - Simple regex checks to reject direct `from datetime import UTC` and PEP 604 unions in Pydantic models.
- pytest.ini:
  - Register `integration` mark.
  - Optional warning filters (document any ignored warnings).
- CI:
  - Job for fast unit tests by default.
  - Optional gated integration job that downloads large artifacts if needed.

---

## When not to refactor

- When the behavior is not locked by tests and you can’t add them quickly.
- When deadlines push you toward unreviewable large rewrites.
- When the system is undergoing large, concurrent changes (high merge risk).

If you must proceed, isolate changes behind feature flags and guardrails, and plan a short rollback path.

---

## Definition of done (for refactors)

- Tests pass (unit + affected integrations) and coverage is not worse.
- Performance is same or improved on representative samples.
- Docs updated (CLI usage, configuration, migrations if applicable).
- No new TODOs left in code—create issues for follow-ups.
- CHANGELOG/PR description clearly explains what moved and how to migrate.

---

## References

- docs/ci/troubleshooting.md — common CI failures and durable fixes
- docs/config/README.md — canonical configuration guide
- docs/migrations/config-yaml-migration.md — config and import/typing migration recipes
- docs/engineering/performance.md — performance patterns and checklists

---
Last updated: Refactoring guide consolidation