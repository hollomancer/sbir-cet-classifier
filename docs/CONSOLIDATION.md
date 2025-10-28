# Consolidation & Migration Guide

Status: in-progress  
Purpose: document the consolidation of duplicated vectorizer and scoring code, list archived modules, and show canonical replacements and migration steps for maintainers and consumers.

This document is the single source-of-truth for recent consolidation work (vectorizers, CET scorers, and associated helpers). It explains what was archived, what remains canonical, how to migrate imports and tests, and recommended next steps.

---

## High-level summary

- Goal: remove parallel, drifting implementations of similar functionality and centralize behavior in well-tested, canonical modules.
- Outcome:
  - Canonical implementations established and exported from `src/sbir_cet_classifier/models` (see `models/__init__.py`).
  - Experimental/duplicate modules moved to `docs/archive/` and replaced by thin shims or direct canonical imports.
  - CLI and classification flow now optionally use the explainable `RuleBasedScorer` and produce `rule_score`/`hybrid_score` when enabled.
  - CI updated to run tests on Python 3.11 (the codebase uses Python 3.11+ syntax).

---

## Canonical modules (use these)

Import these from `sbir_cet_classifier.models` (preferred public surface):

- `MultiSourceTextVectorizer` — canonical multi-source TF-IDF vectorizer  
  Path: `src/sbir_cet_classifier/models/vectorizers.py`

- `CETRelevanceScorer` — semantic relevance scoring for solicitation text  
  Path: `src/sbir_cet_classifier/models/cet_relevance_scorer.py`

- `RuleBasedScorer` — explainable, YAML-driven rule-based CET scoring  
  Path: `src/sbir_cet_classifier/models/rules_scorer.py`

- `ApplicabilityModel` — ML model wrapper (TF-IDF + Logistic Regression / calibration)  
  Path: `src/sbir_cet_classifier/models/applicability.py`

- `EnhancedCETClassifier` & `SolicitationEnhancedScorer` — thin helpers that use canonical vectorizer  
  Path: `src/sbir_cet_classifier/models/enhanced_scoring.py`

Note: `src/sbir_cet_classifier/models/__init__.py` re-exports the canonical items above for simple imports.

---

## Archived / deprecated modules (do not import from `src`)

The following experimental or duplicated modules were archived and/or removed from the package `src/`. They remain in `docs/archive/` for reference only.

- `enhanced_vectorization.py` (experimental CET-aware TF-IDF, WeightedTextCombiner, CETAwareTfidfVectorizer, SolicitationEnhancedTfidfVectorizer)  
  - Archive location: `docs/archive/enhanced_vectorization.py`  
  - Reason: duplicated logic; replaced by `MultiSourceTextVectorizer` and `RuleBasedScorer`.  
  - Migration: use `MultiSourceTextVectorizer` instead; if you relied on internal CET boosting, migrate to an explicit rule-score via `RuleBasedScorer` or calculate engineered features.

- (Any other experimental/older files should be listed here if present in `docs/archive/`.)

Compatibility shims:
- A small shim module `src/sbir_cet_classifier/models/enhanced_vectorization.py` exists that:
  - Emits `DeprecationWarning` on import
  - Provides thin compatibility wrappers that delegate to `MultiSourceTextVectorizer`
  - Purpose: ease migration for downstream code that still imports the old names; plan to remove the shim after a deprecation window.

---

## Import migration examples

Replace old imports like:
```python
# Deprecated/archived (do not use)
from sbir_cet_classifier.models.enhanced_vectorization import CETAwareTfidfVectorizer
from sbir_cet_classifier.models.enhanced_vectorization import SolicitationEnhancedTfidfVectorizer
```

With canonical imports:
```python
from sbir_cet_classifier.models import MultiSourceTextVectorizer
# or directly
from sbir_cet_classifier.models.vectorizers import MultiSourceTextVectorizer
```

If you used CET keyword boosting inside the vectorizer, migrate to:
- `RuleBasedScorer` for explainable per-CET scores (0–100)
- Or compute explicit feature columns (e.g., counts/presence of CET keywords) and include them in your model pipeline.

Example: compute rule score and combine with ML score in a hybrid:
```python
from sbir_cet_classifier.models import RuleBasedScorer
scorer = RuleBasedScorer()
rule_scores = scorer.score_text(text, agency="Department of Energy")
# Combine with ML probability (0..100) via a linear blend:
hybrid = (1 - w) * ml_score + w * rule_scores[primary_cet]
```

---

## Tests: update guidance

- Replace test imports that reference archived classes with canonical ones:
  - `tests/unit/test_enhanced_vectorization.py` → use `MultiSourceTextVectorizer`
  - `tests/unit/test_enhanced_scoring.py` → ensure it imports `EnhancedCETClassifier` (thin helper) and the canonical `MultiSourceTextVectorizer` where necessary.

- New tests added for rule/hybrid outputs:
  - `tests/unit/sbir_cet_classifier/data/test_classify_with_rules.py` — validates `rule_score` and `hybrid_score` columns and metric presence.

- Run the full test-suite on Python 3.11:
  - Locally (recommended): use pyenv or Docker to run Python 3.11
  - CI: `.github/workflows/ci-python.yml` runs tests on Python 3.11.

---

## Deprecation policy & timeline

Recommended approach:
1. Immediately: keep compatibility shim in `src` that warns on import (done).
2. Short window (1 release cycle): monitor uses, update internal code and tests to canonical APIs, and notify contributors via CHANGELOG and README.
3. After the window: remove shim and archived implementations from `src` entirely (archive preserved under `docs/archive/`).

Example deprecation messages:
- On import:
  - "module X is deprecated — import Y instead. This shim will be removed in vN."
- On class instantiation:
  - "Class Z is deprecated; see docs/CONSOLIDATION.md for migration steps."

---

## Recommended checklist for maintainers (actionable)

- [ ] Replace all internal imports referencing archived modules with canonical imports:
  - Search for `enhanced_vectorization` / `CETAware` / `WeightedTextCombiner` and update.
- [ ] Run unit & integration tests on Python 3.11 and fix any breakages.
- [ ] Add deprecation notes in package `CHANGELOG.md` and/or release notes.
- [ ] Keep `docs/archive/enhanced_vectorization.py` as reference (do not reintroduce into `src/`).
- [ ] After 1 release cycle, remove the shim file `src/.../enhanced_vectorization.py` and update docs accordingly.
- [ ] Communicate the change to any external consumers (email/Slack/PR description) if this package is consumed outside this repo.

---

## Notes on behavior differences & migration caveats

- CET keyword matching in the old experimental vectorizer used substring boosting heuristics. The canonical approach separates concerns:
  - `MultiSourceTextVectorizer` provides consistent TF-IDF features across sources.
  - `RuleBasedScorer` provides explainable, config-driven CET signals (priors, core/related/negative keywords, context rules).
  - If you previously relied on implicit keyword boosting inside TF-IDF, you should:
    - Add explicit engineered features (keyword presence counts) to your dataset, or
    - Use `RuleBasedScorer` and optionally blend rule and ML scores.

- Small API differences:
  - The canonical vectorizer uses a `feature_names_out()` interface and exposes `abstract_vectorizer`, `keywords_vectorizer`, etc., where appropriate.
  - The shim retains minimal old API shapes but is deprecated.

---

## Example quick migration (code snippet)

Before:
```python
from src.sbir_cet_classifier.models.enhanced_vectorization import CETAwareTfidfVectorizer
vec = CETAwareTfidfVectorizer(cet_keywords_boost=2.0)
X = vec.fit_transform(documents)  # documents: list[str]
```

After:
```python
from sbir_cet_classifier.models import MultiSourceTextVectorizer
# Build per-source documents (dict with abstract/keywords/solicitation_text)
vec = MultiSourceTextVectorizer(abstract_weight=0.7, keywords_weight=0.3, include_solicitation=False)
X = vec.fit_transform(docs)  # docs: list[dict]
```
If you want CET keyword emphasis, compute rule scores:
```python
from sbir_cet_classifier.models import RuleBasedScorer
sc = RuleBasedScorer()
scores = sc.score_text("text content here", agency="Department of Energy")
```

---

## Where to look for archived code

- `docs/archive/enhanced_vectorization.py` — the full historical implementation preserved for review and comparison.
- `docs/archive/enhanced_vectorization.py.MOVED` — migration notes and rationale.

---

## Contacts / owners

- Primary maintainers (for consolidation plan and merge approvals):
  - Repo maintainers / engineering leads (see repo OWNERS or top-level README)
- For migration help or backwards-compat issues:
  - Open a PR referencing this doc and the tests that need changes; tag the maintainers.

---

## Final notes

- Consolidation reduces duplication, clarifies responsibilities, and improves maintainability.
- Keep the archive stable and do not resurrect archived implementations into `src/`.
- Prefer explicit, test-covered behavior (rules or engineered features) over hidden heuristics inside a vectorizer.

If you want, I can:
- Produce the PR that adds deprecation warnings and a short CHANGELOG entry, or
- Run a repo-wide `grep` and produce a concrete file-by-file list of import sites to update (I already ran a focused scan for TF-IDF usage—let me expand it to other patterns if you want).