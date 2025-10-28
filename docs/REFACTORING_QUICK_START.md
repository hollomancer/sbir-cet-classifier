# Refactoring Quick Start Guide

> **Goal:** Reduce codebase by 25% while improving quality and maintainability

## Week 1: Low-Risk, High-Impact Changes

### Day 1-2: Storage Layer Consolidation

**File:** `src/sbir_cet_classifier/data/storage.py`

**Action:**
1. Create `ParquetStorage[T]` generic class
2. Replace 8 writer/reader classes with factory methods
3. Update tests to use new API
4. Run full test suite

**Expected Outcome:**
- ✅ Reduce 500 lines → 150 lines (70% reduction)
- ✅ All 232 tests still passing
- ✅ Type-safe storage operations

**Commands:**
```bash
# Run storage tests before
pytest tests/unit/test_storage.py -v

# Make changes to storage.py

# Run storage tests after
pytest tests/unit/test_storage.py -v

# Run full suite
pytest tests/ -v
```

---

### Day 3: CLI Reorganization

**Files:** `src/sbir_cet_classifier/cli/`

**Action:**
1. Create `cli/commands/` directory
2. Move command functions into feature-based files:
   - `app.py` (classify) → `commands/classify.py`
   - Keep `app.py` minimal (just Typer setup)
3. Update imports
4. Test CLI commands

**Expected Outcome:**
- ✅ Clear command organization
- ✅ Each file has single responsibility
- ✅ All CLI commands work

**Commands:**
```bash
# Test CLI before
python -m sbir_cet_classifier.cli.app --help
python -m sbir_cet_classifier.cli.app summary --help

# Make changes

# Test CLI after
python -m sbir_cet_classifier.cli.app --help
pytest tests/unit/test_cli* -v
```

---

### Day 4: Test Fixture Consolidation

**File:** `tests/conftest.py`

**Action:**
1. Create shared fixtures:
   - `sample_award()`
   - `sample_cet_area()`
   - `temp_storage(tmp_path)`
   - `mock_enrichment_client()`
2. Remove duplicated fixtures from individual test files
3. Update tests to use shared fixtures

**Expected Outcome:**
- ✅ Reduce fixture duplication by 50%
- ✅ Consistent test data
- ✅ All tests passing

**Commands:**
```bash
# Run tests before
pytest tests/ -v

# Create conftest.py with shared fixtures

# Update individual test files

# Run tests after
pytest tests/ -v --cov=src
```

---

## Week 2: Configuration Unification

### Day 5-7: Unified Configuration Manager

**Files:** 
- `src/sbir_cet_classifier/common/config.py`
- `src/sbir_cet_classifier/common/yaml_config.py`
- `src/sbir_cet_classifier/common/classification_config.py`

**Action:**
1. Create `ConfigurationManager` class
2. Consolidate path resolution logic
3. Merge env-based and YAML-based configs
4. Update all imports across codebase
5. Add backward-compatible wrappers

**Expected Outcome:**
- ✅ Single configuration system
- ✅ Clear precedence: env > YAML > defaults
- ✅ Consistent caching
- ✅ All tests passing

**Migration Strategy:**
```python
# Old way (still works)
from sbir_cet_classifier.common.config import load_config
config = load_config()

# New way (preferred)
from sbir_cet_classifier.common.config import get_config
config = get_config()
taxonomy = config.taxonomy
classification = config.classification
```

**Commands:**
```bash
# Test config loading
python -c "from sbir_cet_classifier.common.config import get_config; print(get_config().storage_paths)"

# Run config tests
pytest tests/unit/test_classification_config.py -v

# Run full suite
pytest tests/ -v
```

---

### Day 8-9: Scoring System Unification

**Files:**
- `src/sbir_cet_classifier/models/scorer.py` (new)
- `src/sbir_cet_classifier/models/applicability.py`
- `src/sbir_cet_classifier/models/rules_scorer.py`
- `src/sbir_cet_classifier/data/classification.py`

**Action:**
1. Create `CETScorer` facade class
2. Move hybrid logic from `classification.py` into scorer
3. Add strategy pattern for ml/rules/hybrid modes
4. Update classification pipeline to use unified scorer

**Expected Outcome:**
- ✅ Single API for all scoring
- ✅ Remove hybrid logic from classification.py
- ✅ Easy to switch strategies
- ✅ All classification tests passing

**Commands:**
```bash
# Test scoring before
pytest tests/unit/sbir_cet_classifier/models/test_applicability.py -v
pytest tests/unit/test_rule_based_scorer.py -v

# Create scorer.py

# Test scoring after
pytest tests/unit/sbir_cet_classifier/models/ -v
pytest tests/integration/test_classification_accuracy.py -v
```

---

## Week 3: Enrichment & Dependencies

### Day 10-11: Enrichment Service Consolidation

**Files:**
- `src/sbir_cet_classifier/features/enrichment.py`
- `src/sbir_cet_classifier/features/batch_enrichment.py`
- `src/sbir_cet_classifier/features/fallback_enrichment.py`

**Action:**
1. Create unified `EnrichmentService` with strategies
2. Refactor `EnrichmentOrchestrator` → `APIEnrichmentProvider`
3. Consolidate batch logic
4. Add clear strategy selection

**Expected Outcome:**
- ✅ Single entry point for enrichment
- ✅ Strategy pattern for single/batch/fallback
- ✅ Reduced code duplication
- ✅ All enrichment tests passing

**Commands:**
```bash
# Test enrichment before
pytest tests/integration/sbir_cet_classifier/enrichment/ -v

# Refactor

# Test enrichment after
pytest tests/integration/sbir_cet_classifier/enrichment/ -v
pytest tests/unit/enrichment/ -v
```

---

### Day 12-13: Dependency Injection

**Files:** All service classes

**Action:**
1. Add optional constructor parameters for dependencies
2. Default to creating instances if not provided
3. Update tests to inject mocks
4. Document DI pattern in DEVELOPMENT.md

**Expected Outcome:**
- ✅ Easier testing with mocks
- ✅ Clear dependencies
- ✅ Backward compatible
- ✅ Test coverage increases

**Pattern:**
```python
# Before
class Service:
    def __init__(self):
        self.dependency = Dependency()

# After
class Service:
    def __init__(self, dependency: Dependency | None = None):
        self.dependency = dependency or Dependency()
```

---

### Day 14: Error Handling Standardization

**Files:** All modules

**Action:**
1. Create exception hierarchy in `common/exceptions.py`
2. Replace generic exceptions with domain exceptions
3. Update CLI error formatting
4. Update API error responses

**Expected Outcome:**
- ✅ Consistent error handling
- ✅ Better error messages
- ✅ Easier debugging

**Commands:**
```bash
# Test error handling
pytest tests/ -v --tb=short
```

---

## Week 4: Polish & Documentation

### Day 15: Model Standardization

**Action:**
1. Convert key dataclasses to Pydantic models
2. Add validation to all data models
3. Ensure consistent serialization

**Files to update:**
- `models/applicability.py` - TrainingExample, ApplicabilityScore
- `features/enrichment.py` - EnrichedAward
- `data/taxonomy.py` - CETTaxonomy

**Commands:**
```bash
pytest tests/unit/sbir_cet_classifier/models/ -v
pytest tests/unit/sbir_cet_classifier/features/ -v
```

---

### Day 16-17: Documentation

**Action:**
1. Standardize all docstrings to Google style
2. Add module-level docstrings
3. Update README with refactoring notes
4. Document new patterns in DEVELOPMENT.md

**Checklist:**
- [ ] All public functions have docstrings
- [ ] All classes have docstrings
- [ ] All modules have header docstrings
- [ ] Examples in docstrings work
- [ ] Type hints are accurate

---

## Daily Checklist

Before each refactoring:
- [ ] Create feature branch: `git checkout -b refactor/[name]`
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Note current test count and coverage

After each refactoring:
- [ ] Run affected tests: `pytest [test_path] -v`
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Verify 232/232 tests still passing
- [ ] Check coverage: `pytest --cov=src --cov-report=html`
- [ ] Run linter: `ruff check src/`
- [ ] Format code: `ruff format src/`
- [ ] Commit with descriptive message
- [ ] Push and create PR

---

## Verification Commands

```bash
# Full test suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=src/sbir_cet_classifier --cov-report=html --cov-report=term

# Fast tests only (skip slow integration)
pytest tests/ -m "not slow" -v

# Specific test file
pytest tests/unit/test_storage.py -v

# Code quality
ruff check src/ tests/
ruff format src/ tests/ --check

# Type checking (if mypy configured)
mypy src/

# Line count
find src -name "*.py" -exec wc -l {} + | tail -1
find tests -name "*.py" -exec wc -l {} + | tail -1
```

---

## Success Metrics

Track these after each major refactoring:

| Metric | Before | Target | Current |
|--------|--------|--------|---------|
| Source LOC | 14,000 | 10,500 | ___ |
| Test LOC | 13,000 | 11,000 | ___ |
| Test Coverage | 85% | 90% | ___ |
| Config Systems | 3 | 1 | ___ |
| Storage Classes | 8 | 2 | ___ |
| Enrichment Modules | 5 | 1 | ___ |

---

## Rollback Plan

If tests fail after refactoring:

```bash
# Check what changed
git status
git diff

# Stash changes
git stash

# Verify tests pass on main
git checkout main
pytest tests/ -v

# Go back to branch
git checkout refactor/[name]
git stash pop

# Fix issues or rollback
git reset --hard HEAD~1
```

---

## Getting Help

If stuck on any refactoring:

1. **Check examples:** See `REFACTORING_EXAMPLES.md` for detailed code samples
2. **Review tests:** Look at existing tests for patterns
3. **Git history:** Check how similar changes were done: `git log --all --grep="refactor"`
4. **Ask questions:** Document blockers and discuss in PR

---

## Final Checklist

Before marking refactoring complete:

- [ ] All 232 tests passing
- [ ] Coverage ≥90%
- [ ] No linter errors
- [ ] Code formatted with ruff
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] All files have proper headers
- [ ] No TODO comments left
- [ ] Performance benchmarks still meet targets
- [ ] CLI commands all work
- [ ] API endpoints all work

---

## Post-Refactoring

After completing all refactorings:

1. Run full integration tests
2. Update version number
3. Tag release: `git tag v1.2.0-refactored`
4. Update STATUS.md with metrics
5. Celebrate! 🎉

**Expected outcomes:**
- 25% less code
- 90%+ test coverage
- Easier maintenance
- Better developer experience
- Faster onboarding