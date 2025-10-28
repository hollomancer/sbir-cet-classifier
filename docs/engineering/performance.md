# Engineering Performance Guide

This guide captures practical techniques to measure, improve, and maintain performance in the SBIR CET Classifier. It focuses on the data pipeline (ingest → enrich → classify → export), model choices, and CLI workflows that show up in CI and production-like runs.

Audience: engineers and maintainers
Scope: CPU/memory efficiency, I/O throughput, algorithmic choices, test-time strategies


## Principles

- Measure first, then optimize. Always baseline with timers or profilers before changing code.
- Optimize the hot path only. Focus on the 20% of code causing 80% of runtime.
- Prefer vectorized, batch operations over row-by-row loops.
- Keep data formats columnar and typed (Parquet + Arrow types).
- Avoid hidden densification (sparse → dense), implicit copies, and unnecessary work.


## Measuring and profiling

- Micro-timing: use `time.perf_counter()` around narrow regions; log durations and counts with structured logging.
- Whole-test timing: `pytest -q -k <pattern>` and `pytest --durations=20` to identify slow tests.
- CPU sampling: `py-spy` or `scalene` in local runs to find hotspots without invasive instrumentation.
- Algorithm-level counters: log key sizes (rows, columns, feature counts), sparsity, memory footprints.
- Baseline checks in PRs: capture “before/after” timings for changed functions with a small, representative dataset.


## Data I/O

- Prefer Parquet over CSV for all internal storage:
  - Columnar layout, typed columns, predicate pushdown, and compression.
  - Compression: ZSTD (best ratio) or Snappy (fast).
  - Partition by high-selectivity columns (e.g., `fiscal_year`) for faster reads.
- When reading CSVs (for bootstrap):
  - Use `usecols` to load only needed columns.
  - Provide explicit dtypes where possible to avoid expensive inference.
  - Use `nrows` for smoke tests; read in chunks (`chunksize`) for large files.
- Avoid repeated disk scans:
  - Cache derived tables (e.g., normalized awards) in Parquet.
  - Use a simple metadata file to capture source version, row counts, transform version.


## Pandas performance patterns

- Vectorize:
  - Favor column operations, `where`, `mask`, `map`, `isin`, `groupby` over `apply(axis=1)` or loops.
  - Use `itertuples()` (not `iterrows()`) if you must loop; but first try vectorization.
- Types:
  - Convert low-cardinality strings (e.g., agency, phase, state) to `category`.
  - Downcast numerics (`to_numeric(..., downcast='integer'/'float')`) to cut memory.
  - Ensure datetimes are parsed once (e.g., `to_datetime(..., utc=True)`).
- Merges:
  - Select only required columns before `merge`.
  - Build indexes (`set_index`) for repeated joins with the same key.
- Booleans and NaN:
  - Always `.fillna(False)` before boolean indexing.
  - Avoid `DataFrame.get(...)` (dict‑only); check column presence then select.
- GroupBy and aggregations:
  - Pre-filter columns to reduce materialized group frames.
  - Use named aggregations to avoid post-rename passes.
- Copy avoidance:
  - Use `inplace=False` but structure transforms to minimize intermediate copies (compose operations).
  - Drop intermediates early with `del df_col` when safe; avoid holding multiple large copies in scope.

Example patterns (conceptual):
- Compute `data_incomplete` without row loops:
  - `has_text = df["abstract"].notna() & (df["abstract"].str.strip() != "") & df["keywords"].notna()`
  - `df["data_incomplete"] = ~has_text | df["award_id"].map(review_map).apply(pending_fn)`


## Exporter patterns

- Precompute taxonomy maps once: `taxonomy.set_index("cet_id")["name"].to_dict()`.
- Sanitize list-like columns before use:
  - `vals = row.get("supporting_cet_ids"); vals = vals if isinstance(vals, list) else []`.
- Avoid per-row Python loops when adding weights:
  - Build a DataFrame of `(award_id, cet_id)` pairs via `explode`, map weights with a dictionary, then aggregate with `groupby`.
- Boolean masks:
  - `mask = df["is_export_controlled"].fillna(False)`; avoid `df[df["is_export_controlled"]]` on NaNs.


## Text and string handling

- Normalize once, reuse:
  - Precompute normalized firm names and cache them; avoid repeated `.lower()` + regex per step.
- Vectorizer inputs:
  - Use a single join function to build text (title + abstract + keywords) consistently.
- Tokenization:
  - If experimenting with char n-grams or token-level fuzzy features, do so behind a feature flag and cache artifacts.


## ML pipeline efficiency

- TF‑IDF:
  - Tune `max_features` (e.g., 50k–200k for big corpora; far less for tests).
  - `min_df` / `max_df` should match corpus size; too high/low wastes features.
  - Keep output sparse; avoid operations that call `.toarray()` or densify.
- Feature Selection:
  - Use `SelectKBest` with `k <= n_features`. For tiny tests, prefer conditional `k = min(k, n_features)`.
- Classifier:
  - LogisticRegression:
    - `solver='saga'` for large sparse problems; `liblinear` for small/linearly separable sets.
    - Use `class_weight='balanced'` only if needed; it can slow convergence.
    - `n_jobs` may not parallelize effectively for all solvers; prefer BLAS-level threading controls.
- Calibration:
  - `CalibratedClassifierCV` adds CV passes; restrict `cv` and sample size for test runs.
  - Consider platt scaling on a held-out split if full CV is too slow.
- Reuse fitted artifacts:
  - Persist vectorizer vocabulary and model where stability is desirable; avoid re-fitting every run if inputs are unchanged.


## Parallelism and threading

- Control BLAS/OpenMP threads to avoid oversubscription:
  - Environment variables: `OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `OPENBLAS_NUM_THREADS` set to the number of physical cores or less.
- sklearn `n_jobs`:
  - Be mindful of combined parallelism (model + BLAS). Test configurations to hit optimal runtime without thrashing.
- Batch external calls:
  - For enrichment clients, batch or cache requests; avoid per-record HTTP round trips when possible.


## SQLite cache (solicitation cache)

- Index the lookup keys (e.g., `(api_source, solicitation_id)`).
- Store compressed payloads only if space is an issue; decompression adds CPU overhead.
- Add a simple TTL or version field to invalidate stale entries cheaply.
- Manage DB connection lifetime: reuse a single connection per run to avoid overhead.


## CLI runtime tips

- Guard long operations behind `--limit`, `--dry-run`, `--since` (dates) for development.
- Push expensive optional tasks behind explicit flags. Default to fast paths.
- Avoid chatty per-row logs; prefer summary logs with counts and durations.
- Consider progress reporting only for interactive runs; disable in CI for cleaner logs.


## Memory management

- Estimate memory budgets:
  - DataFrame memory: `df.memory_usage(deep=True).sum()`
  - Sparse matrices: track `nnz` and dtype; avoid `.toarray()` at all costs.
- Release intermediates:
  - Drop large temporaries ASAP; isolate scopes so GC can free memory.
- Use `category` for repeated strings; this can reduce memory by 5–20× for those columns.


## Test-time strategies

- Keep unit tests small and fast:
  - Tiny samples for TF‑IDF; ensure `min_df` and `SelectKBest(k)` don’t break on small N.
- Gate integration tests:
  - Use marks (e.g., `integration`) and skip if large datasets are missing (e.g., `award_data.csv`).
- Provide deterministic seeds and fixture data:
  - Reduce variance to keep performance deltas attributable to code changes.


## Observability and logging

- Log key performance fields as structured JSON:
  - `records_in`, `records_out`, durations for stages, memory estimates, feature counts.
- Keep a rolling “latest run” JSON log for smoke-diffing recent runs.
- Add a “slow path” flag: if a function falls back to a slower algorithm, log it once with context.


## Performance checklists

Before merging a change that touches performance-critical code:

- Measurement
  - [ ] Added or updated micro/meso timing around hot path
  - [ ] Captured before/after numbers with the same input
- Algorithm
  - [ ] Replaced row loops with vectorized ops where possible
  - [ ] Avoided densifying sparse matrices
  - [ ] Tuned or bounded `min_df`, `max_df`, `k` for tests and prod
- I/O
  - [ ] Parquet used for intermediates; partitioning considered
  - [ ] CSV reads limited by `usecols`, `nrows` (in tests)
- Memory
  - [ ] Applied categoricals and downcasts to major columns
  - [ ] Dropped intermediates promptly
- Parallelism
  - [ ] Verified no oversubscription (BLAS + sklearn + process level)
  - [ ] Set thread env vars in CI or launcher scripts if needed
- Tests
  - [ ] Unit tests remain fast; integration tests gated
  - [ ] No brittle expectations around exact step-by-step logs


## Troubleshooting guide

- TF‑IDF too slow / memory-heavy:
  - Reduce `max_features`, increase `min_df`, ensure sparse pipeline throughout.
- Feature selection error (`k > n_features`):
  - Bound `k` by actual feature count in code or test config.
- Name/fuzzy ops slow:
  - Cache normalized strings; avoid per-call regex; consider vectorized `.str` operations.
- Exporter slow on CET weighting:
  - Avoid iterating rows; use `explode`, map, `groupby` to compute weights in bulk.
- CI timeouts:
  - Add `--limit` flags to CLI calls; mark long tests; reduce calibration CV folds.


## References

- Parquet & Arrow: columnar formats for analytics
- pandas user guide: vectorization, categoricals, groupby patterns
- scikit‑learn: sparse pipelines, solvers, calibration tradeoffs
- BLAS/OpenMP threading: controlling threads in numeric libraries


---

Last updated: engineering performance practices consolidated for the SBIR CET Classifier