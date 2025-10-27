# CONFIG: Editing `config/classification.yaml` Safely

Audience: Non-developers (analysts, program staff)  
Purpose: Explain how to safely edit the classification configuration without touching code, and how to validate your changes.

---

## What this file controls

`config/classification.yaml` contains:
- Model parameters (TF‑IDF, feature selection, classifier, calibration)
- Scoring bands (High/Medium/Low thresholds)
- Domain stop words (common words to ignore)
- Rule-based signals:
  - Agency and branch “priors” (score boosts for certain CETs)
  - CET keyword lists (core, related, negative)
  - Context rules (keyword combinations that add a boost)

These rules are loaded at runtime, so changes take effect the next time you run the tooling.

---

## How to validate after editing

Run the validation command from the repository root:

  python -m sbir_cet_classifier.cli.app config validate

You should see a ✅ message for `classification.yaml`. If you see ❌, read the error and fix the indicated line.

Tip: Make small changes, validate, then repeat.

---

## YAML editing basics (safe practices)

- Use two spaces for indentation (never tabs).
- Keep key names exactly as shown.
- Lowercase CET ids with underscores (e.g., artificial_intelligence).
- Quote multi‑word phrases: "quantum computing".
- Keep numbers as integers (no quotes).
- Avoid trailing spaces and stray punctuation (like a rogue colon).
- Do not remove whole sections unless you are certain they are unused.

---

## Schema overview (what each section means)

Top-level keys in `classification.yaml`:

- version
  - Schema/config version (string), e.g., "1.0.0".
- vectorizer
  - ngram_range: [min, max] (e.g., [1, 3])
  - max_features: integer (feature cap)
  - min_df: integer (ignore terms appearing in fewer than N documents)
  - max_df: decimal 0–1 (ignore terms appearing in > X% of documents)
- feature_selection
  - enabled: true/false
  - method: chi2
  - k: top N features to keep
- classifier
  - max_iter, solver, n_jobs, class_weight (logistic regression)
- calibration
  - enabled, method, cv, min_samples_per_class
- scoring
  - bands:
    - high/medium/low: each has min, max, label (percent scale 0–100)
  - max_supporting: number of secondary CET areas returned (integer)
- stop_words
  - List of generic terms to ignore (strings)
- agency_priors
  - Map of Agency Name -> { cet_id: boost_int }
  - Optional special key: _all_cets applies a small boost across all CETs
- branch_priors
  - Map of Branch/Sub‑agency -> { cet_id: boost_int }
- cet_keywords
  - Map of cet_id -> { core: [], related: [], negative: [] }
    - core: strongest positive signals
    - related: additional positive signals (weaker)
    - negative: phrases that indicate “not this CET” context
- context_rules
  - Map of cet_id -> list of [ [required_keywords...], boost_int ]
  - A rule fires when all required keywords are present together

Notes:
- Typical boost ranges are 0–25. Keep boosts small and incremental.
- CET ids must already exist in the taxonomy configuration. Adding a new CET id here without updating the taxonomy will have no effect.

---

## Common edits (with examples)

1) Adjust classification bands (score thresholds)

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

2) Add or tune agency priors (boosts applied for awards from that agency)

  agency_priors:
    National Institutes of Health:
      medical_devices: 25
      biotechnology: 20
    National Science Foundation:
      _all_cets: 5

3) Update CET keyword lists (add strong/weak/negative phrases)

  cet_keywords:
    quantum_computing:
      core:
        - "quantum computing"
        - "quantum algorithm"
      related:
        - "qubit"
        - "quantum circuit"
      negative:
        - "quantum chemistry"

4) Add a context rule (boost when words appear together)

  context_rules:
    medical_devices:
      - [["ai", "diagnostic"], 20]

Remember to validate after any change.

---

## Safe-change checklist

- Keep YAML formatting consistent (two spaces, correct dashes).
- Use known CET ids only (must match taxonomy).
- Keep boosts small; document rationale inline with comments.
- Make one change at a time; run validation each time.
- Share your change and validation output with your team.

---

## Interpreting validation errors

Examples and how to fix them:

- Error: “mapping values are not allowed here” at line X
  - Cause: A stray colon or missing quote on that line.
  - Fix: Check for unmatched quotes or extra colon.

- Error: “expected <block end>, but found ‘-’” at line X
  - Cause: Wrong indentation for a list item.
  - Fix: Align dashes with parent key using two spaces.

- Error: “value is not a valid integer” for a boost
  - Cause: Quoted number or non‑numeric value.
  - Fix: Remove quotes and ensure it’s an integer (e.g., 15).

- Error: “unknown key” (if enforced by schema in a given version)
  - Cause: You added a new top‑level key not recognized.
  - Fix: Remove or rename the key to match documented schema.

---

## Best practices

- Start small: Try adding one keyword and validate.
- Add comments explaining why a change was made (context helps reviewers).
- Prefer core keywords for strong signals; use related for broader coverage.
- Use negative keywords to exclude common false‑positives (e.g., “quantum chemistry” when you want “quantum computing”).
- Re-run a small test classification or review a known set to confirm the change behaves as expected.

---

## Quick reference template

Copy/paste the block below into `classification.yaml` (adjust values as needed). This shows typical shapes; do not duplicate keys that already exist.

  scoring:
    bands:
      high:   { min: 70, max: 100, label: High }
      medium: { min: 40, max: 69,  label: Medium }
      low:    { min: 0,  max: 39,  label: Low }
    max_supporting: 3

  agency_priors:
    Example Agency:
      artificial_intelligence: 10
      _all_cets: 3

  branch_priors:
    Example Research Institute:
      medical_devices: 15

  cet_keywords:
    example_cet:
      core:
        - "example phrase"
      related:
        - "supporting term"
      negative:
        - "unwanted context"

  context_rules:
    example_cet:
      - [["required", "together"], 10]

---

## FAQ

- Can I add a new CET here?
  - No. Additions to CET areas belong in `config/taxonomy.yaml`. This file only tunes how existing CETs are detected/scored.

- What does `_all_cets` mean in priors?
  - A small boost applied to every CET for the specified agency or branch.

- How big should boosts be?
  - Usually 5–25 points. Favor smaller steps, validate, then adjust.

- Do keyword lists need quotes?
  - Single words do not, but multi‑word phrases should be quoted.

---

## Change management

- Commit your changes with a descriptive message (what changed and why).
- Include validation output in the pull request or change note.
- Coordinate with reviewers to verify the effect on known examples.
- Keep a record of before/after behavior when adjusting thresholds or large keyword lists.

---

Last updated: 2025-10-27