# Codebase Refactoring Opportunities

**Date**: 2025-10-08
**Codebase Size**: ~4,122 lines across 34+ Python files
**Potential Reduction**: ~445 lines (10% savings)

---

## Executive Summary

The SBIR CET Classifier codebase is well-structured but contains significant code duplication and opportunities for simplification. Implementing the recommendations below could reduce the codebase by approximately 10% while improving maintainability and consistency.

### Key Findings

| Issue | Occurrences | Lines Affected | Priority |
|-------|-------------|----------------|----------|
| **Duplicate `as_dict()` methods** | 15 | ~200 | **HIGH** |
| **Duplicate service configuration** | 3 | ~60 | **HIGH** |
| **Duplicate JSON log operations** | 8 | ~120 | **HIGH** |
| **DateTime inconsistencies** | 25+ | ~25 | **HIGH** |
| **Filter duplication** | 2 | ~40 | MEDIUM |
| **Total Estimated Savings** | - | **~445 lines** | - |

---

## HIGH PRIORITY Issues

### 1. Eliminate 200 Lines: Create `SerializableDataclass` Base Class

**Problem:** Every dataclass has a manual `as_dict()` method with field-by-field mapping (15 occurrences).

**Current Code (repeated 15+ times):**
```python
def as_dict(self) -> dict:
    return {
        "awardId": self.award_id,
        "title": self.title,
        "agency": self.agency,
        "firmName": self.firm_name,
        # ... manual mapping for every field
    }
```

**Solution:**
```python
# common/serialization.py
from dataclasses import asdict, dataclass
import re

def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

@dataclass
class SerializableDataclass:
    """Base class for dataclasses with automatic camelCase serialization."""

    def as_dict(self) -> dict[str, Any]:
        """Convert to dict with camelCase keys."""
        result = {}
        for key, value in asdict(self).items():
            camel_key = to_camel_case(key)

            # Handle nested SerializableDataclass objects
            if hasattr(value, 'as_dict'):
                result[camel_key] = value.as_dict()
            # Handle lists of SerializableDataclass objects
            elif isinstance(value, list):
                result[camel_key] = [
                    item.as_dict() if hasattr(item, 'as_dict') else item
                    for item in value
                ]
            else:
                result[camel_key] = value

        return result
```

**Usage:**
```python
@dataclass
class AwardDetail(SerializableDataclass):  # Inherit from base
    award_id: str
    title: str
    agency: str
    # ... all other fields
    # No need for as_dict() method!
```

**Impact:** Eliminates ~200 lines of boilerplate code across 15 classes.

---

### 2. Eliminate 60 Lines: Create Service Registry

**Problem:** Service configuration pattern duplicated across 3 files (router.py, routes/awards.py, routes/exports.py).

**Current Code (duplicated 3 times):**
```python
_summary_service: SummaryService | None = None

def configure_summary_service(service: SummaryService) -> None:
    global _summary_service
    _summary_service = service

def get_summary_service() -> SummaryService:
    if _summary_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Summary service not configured"
        )
    return _summary_service
```

**Solution:**
```python
# common/service_registry.py
from typing import Any, TypeVar
from fastapi import HTTPException, status

T = TypeVar('T')

class ServiceRegistry:
    """Centralized service registry with type-safe access."""

    def __init__(self):
        self._services: dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """Register a service instance."""
        self._services[name] = service

    def get(self, name: str, service_type: type[T]) -> T:
        """Get a registered service or raise 503."""
        service = self._services.get(name)
        if service is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{name} service not configured"
            )
        return service

# Global instance
_registry = ServiceRegistry()

def configure_services(
    summary: SummaryService,
    awards: AwardsService,
    exports: ExportOrchestrator
) -> None:
    """Configure all services at startup."""
    _registry.register("summary", summary)
    _registry.register("awards", awards)
    _registry.register("exports", exports)

def get_summary_service() -> SummaryService:
    return _registry.get("summary", SummaryService)

def get_awards_service() -> AwardsService:
    return _registry.get("awards", AwardsService)

def get_export_orchestrator() -> ExportOrchestrator:
    return _registry.get("exports", ExportOrchestrator)
```

**Impact:** Eliminates ~60 lines, makes service management centralized and testable.

---

### 3. Eliminate 120 Lines: Create JSON Log Manager

**Problem:** JSON log operations duplicated across 8 files (backfill.py, refresh.py, exporter.py, taxonomy_reassessment.py, etc.).

**Current Code (duplicated 8 times):**
```python
def _append_to_log(self, entry: dict) -> None:
    log_path = self._artifacts_dir / "backfill_runs.json"
    if log_path.exists():
        data = json.loads(log_path.read_text())
    else:
        data = {"backfill_runs": []}
    data["backfill_runs"].append(entry)
    log_path.write_text(json.dumps(data, indent=2))
```

**Solution:**
```python
# common/json_log.py
from pathlib import Path
import json
from typing import Any

class JsonLogManager:
    """Manages append-only JSON log files."""

    def __init__(self, log_path: Path, key: str):
        self.log_path = log_path
        self.key = key
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, entry: dict[str, Any]) -> None:
        """Append entry to log file."""
        if self.log_path.exists():
            data = json.loads(self.log_path.read_text())
        else:
            data = {self.key: []}

        data[self.key].append(entry)
        self.log_path.write_text(json.dumps(data, indent=2))

    def get_all(self) -> list[dict[str, Any]]:
        """Get all log entries."""
        if not self.log_path.exists():
            return []
        data = json.loads(self.log_path.read_text())
        return data.get(self.key, [])

    def get_latest(self) -> dict[str, Any] | None:
        """Get most recent log entry."""
        entries = self.get_all()
        return entries[-1] if entries else None
```

**Usage:**
```python
# In backfill.py
class BackfillRunner:
    def __init__(self, artifacts_dir: Path):
        self._log = JsonLogManager(
            artifacts_dir / "backfill_runs.json",
            "backfill_runs"
        )

    def record_run(self, entry: dict) -> None:
        self._log.append(entry)  # Simple!
```

**Impact:** Eliminates ~120 lines, ensures consistent log format across all operations.

---

### 4. Fix DateTime Inconsistencies (25+ occurrences)

**Problem:** Mixed use of `datetime.now()`, `datetime.utcnow()`, and `datetime.now(timezone.utc)`.

**Current Code (inconsistent):**
```python
# File 1: datetime.utcnow() - DEPRECATED in Python 3.12
timestamp = datetime.utcnow()

# File 2: datetime.now() - NO TIMEZONE
timestamp = datetime.now()

# File 3: datetime.now(timezone.utc) - CORRECT
timestamp = datetime.now(timezone.utc)

# File 4: datetime.now(tz=timezone.utc) - CORRECT but verbose
timestamp = datetime.now(tz=timezone.utc)
```

**Solution:**
```python
# common/datetime_utils.py
from datetime import datetime, timezone

def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime.

    This is the recommended way to get current time for all
    timestamps in the application.
    """
    return datetime.now(timezone.utc)
```

**Usage:**
```python
from sbir_cet_classifier.common.datetime_utils import utc_now

# Instead of:
timestamp = datetime.utcnow()  # OLD
timestamp = datetime.now()     # OLD

# Use:
timestamp = utc_now()  # CONSISTENT
```

**Files to Update:**
- `features/review_queue.py:64` - replace `datetime.utcnow()`
- `features/exporter.py:113` - replace `datetime.now()`
- `data/ingest.py:156` - replace `datetime.now(timezone.utc)`
- `features/awards.py:320` - replace `datetime.now(tz=timezone.utc)`
- ... and 21 more occurrences

**Impact:** Prevents timezone bugs, prepares for Python 3.12 where `utcnow()` is removed.

---

## MEDIUM PRIORITY Issues

### 5. Eliminate 40 Lines: Shared DataFrame Normalization

**Problem:** Similar DataFrame normalization logic in `awards.py` and `summary.py`.

**Solution:**
```python
# features/dataframe_utils.py
import pandas as pd

def normalize_awards_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize awards DataFrame with consistent date/type handling."""
    df = df.copy()

    # Add fiscal year if missing
    if "fiscal_year" not in df.columns and "award_date" in df.columns:
        df["fiscal_year"] = pd.to_datetime(
            df["award_date"], errors="coerce"
        ).dt.year

    # Normalize award_date to date objects
    if "award_date" in df.columns:
        df["award_date"] = pd.to_datetime(
            df["award_date"], errors="coerce"
        ).dt.date
    else:
        df["award_date"] = pd.Series([None] * len(df))

    # Normalize award_amount to float
    if "award_amount" in df.columns:
        df["award_amount"] = df["award_amount"].astype(float)

    # Normalize keywords
    if "keywords" not in df.columns:
        df["keywords"] = None
    df["keywords"] = df["keywords"].fillna("").apply(normalize_keywords)

    return df

def normalize_keywords(value: str | list[str] | None) -> list[str]:
    """Normalize keywords from various formats to list."""
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [k.strip() for k in value.split(";") if k.strip()]
    return [str(k).strip() for k in value if str(k).strip()]
```

**Impact:** Eliminates ~40 lines of duplicated DataFrame normalization logic.

---

### 6. Create Shared Filter Utility

**Problem:** Similar filtering logic in `awards.py` and `summary.py`.

**Solution:**
```python
# features/filters.py
import pandas as pd
from sbir_cet_classifier.common.schemas import AwardsFilters

def apply_common_filters(
    df: pd.DataFrame,
    fiscal_year_start: int,
    fiscal_year_end: int,
    agencies: list[str] | None = None,
    phases: list[str] | None = None,
    location_states: list[str] | None = None,
) -> pd.DataFrame:
    """Apply common filtering criteria to awards DataFrame."""

    # Fiscal year range (always required)
    df = df[
        (df["fiscal_year"] >= fiscal_year_start) &
        (df["fiscal_year"] <= fiscal_year_end)
    ]

    # Optional filters
    if agencies:
        df = df[df["agency"].isin(agencies)]

    if phases:
        df = df[df["phase"].isin(phases)]

    if location_states:
        df = df[df["firm_state"].isin(location_states)]

    return df
```

**Impact:** Reduces duplication, makes filtering logic testable in isolation.

---

## LOW PRIORITY Issues

### 7. Standardize Exception Handling in CLI

**Current:** Catching bare `Exception` in CLI code
**Better:** Catch specific exceptions (`HTTPException`, `ValueError`, etc.)

### 8. Use CLASSIFICATION_BANDS Constant Consistently

**Current:** `band_for_score()` has hardcoded thresholds
**Better:** Derive logic from `CLASSIFICATION_BANDS` dictionary

### 9. Inline Trivial Helper Functions

**Example:** `_tuple()` in router.py is only used once
**Better:** Inline as `tuple(agency or [])`

### 10. Standardize CET vs Cet Naming

**Current:** Mixed use of `CET` and `Cet` in class names
**Better:** Standardize on `Cet` per PEP8

---

## Action Plan

### Phase 1: High Priority (Week 1) - Eliminate ~405 lines

**Day 1-2:**
1. Create `SerializableDataclass` base class
2. Update all 15 dataclasses to inherit from it
3. Remove manual `as_dict()` methods

**Day 3-4:**
4. Create `ServiceRegistry` class
5. Migrate all service configuration to registry
6. Update router.py and routes/

**Day 5:**
7. Create `JsonLogManager` class
8. Migrate all 8 log operations to use it
9. Create `utc_now()` utility and replace all datetime calls

**Expected Savings:** ~405 lines, major maintainability improvement

### Phase 2: Medium Priority (Week 2) - Eliminate ~40 lines

**Day 1-2:**
1. Create DataFrame normalization utilities
2. Migrate `awards.py` and `summary.py` to use them

**Day 3-4:**
3. Create shared filter utility
4. Update both services to use common filtering

**Expected Savings:** ~40 lines, improved consistency

### Phase 3: Low Priority (Week 3) - Cleanup

**Day 1-5:**
1. Improve exception handling specificity
2. Standardize naming conventions
3. Inline trivial helpers
4. Update CLASSIFICATION_BANDS usage

**Expected Savings:** Improved code quality, minor line reduction

---

## Testing Strategy

For each refactoring:

1. **Before:** Run full test suite (`pytest tests/ -v`)
2. **During:** Create tests for new utilities first (TDD)
3. **After:** Verify all 35 tests still pass
4. **Validate:** Run ingestion pipeline to ensure no behavioral changes

```bash
# Validation script
pytest tests/ -v --tb=short
python ingest_awards.py
python -c "
import pandas as pd
df = pd.read_parquet('data/processed/assessments.parquet')
assert len(df) == 203640, 'Award count changed!'
assert df['primary_cet_id'].value_counts().iloc[0] > 150000, 'Distribution changed!'
print('✅ Validation passed: No behavioral changes')
"
```

---

## Expected Benefits

| Benefit | Metric |
|---------|--------|
| **Code Reduction** | ~445 lines (10% of codebase) |
| **Maintainability** | Eliminate 15 duplicated `as_dict()` methods |
| **Consistency** | Single datetime utility used everywhere |
| **Testability** | Utilities can be unit tested in isolation |
| **Bug Prevention** | Fix timezone handling before Python 3.12 migration |
| **Onboarding** | New developers see patterns, not repetition |

---

## Risks and Mitigation

| Risk | Mitigation |
|------|------------|
| **Breaking existing tests** | Run full test suite after each change |
| **Behavioral changes** | Validate with production-like data |
| **Import circular dependencies** | Use `common/` for shared utilities |
| **Merge conflicts** | Complete Phase 1 before other work |

---

## Positive Findings ✅

The codebase already demonstrates excellent practices:

- ✅ Consistent use of dataclasses throughout
- ✅ Type hints on all functions and methods
- ✅ Clear module organization (api/, cli/, features/, data/)
- ✅ Comprehensive docstrings
- ✅ Good use of Pydantic for validation
- ✅ Frozen dataclasses for immutability
- ✅ Proper `__all__` exports
- ✅ No TODO comments (clean backlog)
- ✅ Good separation of concerns (API/CLI/business logic)

The refactoring recommendations build on this solid foundation to further improve maintainability.

---

## Recommendation

**Start with Phase 1 (Week 1) immediately:**

The high-priority refactorings provide the most value:
- 405 lines eliminated (~9% of codebase)
- Fixes datetime bug before Python 3.12
- Makes future development much faster

Phase 2 and 3 can be done opportunistically as those files are touched for other reasons.

---

**Report Generated**: 2025-10-08
**Analyzed**: 34+ Python files, ~4,122 lines
**Estimated Savings**: ~445 lines (10% reduction)
**Status**: Ready for implementation
