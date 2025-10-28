# Refactoring Examples - Before & After

This document provides concrete code examples for the refactoring opportunities identified in `REFACTORING_OPPORTUNITIES.md`.

---

## Example 1: Configuration Consolidation

### Before: Three Separate Systems

```python
# common/config.py
from functools import lru_cache

@lru_cache(maxsize=1)
def load_config() -> AppConfig:
    storage = StoragePaths(
        raw=_resolve_path("SBIR_DATA_RAW_DIR", _DEFAULT_RAW),
        processed=_resolve_path("SBIR_DATA_PROCESSED_DIR", _DEFAULT_PROCESSED),
        artifacts=_resolve_path("SBIR_DATA_ARTIFACTS_DIR", _DEFAULT_ARTIFACTS),
    )
    enrichment = _load_enrichment_config()
    return AppConfig(storage=storage, enrichment=enrichment)

# common/yaml_config.py
def load_classification_config(path: Path | None = None) -> ClassificationConfig:
    import os
    if path is None:
        env_dir = os.getenv("SBIR_CONFIG_DIR")
        if env_dir:
            path = Path(env_dir) / "classification.yaml"
        else:
            path = Path(__file__).parent.parent.parent.parent / "config" / "classification.yaml"
    
    resolved = Path(path).resolve()
    key = str(resolved)
    cache = getattr(load_classification_config, "_cache", {})
    if key in cache:
        return cache[key]
    # ... more code

# common/classification_config.py
def load_classification_rules(path: Path | None = None) -> ClassificationRules:
    if path is None:
        env_dir = os.getenv("SBIR_CONFIG_DIR")
        if env_dir:
            path = Path(env_dir) / "classification.yaml"
        else:
            path = Path(__file__).parent.parent.parent.parent / "config" / "classification.yaml"
    # ... duplicate path resolution
```

### After: Unified Configuration Manager

```python
# common/config.py
from pathlib import Path
from typing import Optional
from functools import cached_property
import os
import yaml
from pydantic import BaseModel


class ConfigPaths:
    """Centralized config path resolution."""
    
    @staticmethod
    def resolve(filename: str, env_var: str = "SBIR_CONFIG_DIR") -> Path:
        """Resolve config file path with env override support."""
        env_dir = os.getenv(env_var)
        if env_dir:
            return Path(env_dir) / filename
        
        # Default: <repo-root>/config/<filename>
        repo_root = Path(__file__).parent.parent.parent
        return repo_root / "config" / filename
    
    @staticmethod
    def resolve_data(subdir: str, env_var: str, default: Path) -> Path:
        """Resolve data directory with env override."""
        raw_value = os.getenv(env_var)
        path = Path(raw_value).expanduser() if raw_value else default
        path.mkdir(parents=True, exist_ok=True)
        return path.resolve()


class ConfigurationManager:
    """Unified configuration manager with caching."""
    
    def __init__(self):
        self._cache = {}
        
    def _load_yaml(self, key: str, filename: str, model_class) -> BaseModel:
        """Generic YAML loader with caching."""
        if key not in self._cache:
            path = ConfigPaths.resolve(filename)
            with path.open() as f:
                data = yaml.safe_load(f)
            self._cache[key] = model_class(**data)
        return self._cache[key]
    
    @cached_property
    def storage_paths(self) -> StoragePaths:
        """Get storage paths (env vars override defaults)."""
        return StoragePaths(
            raw=ConfigPaths.resolve_data("raw", "SBIR_DATA_RAW_DIR", Path("data/raw")),
            processed=ConfigPaths.resolve_data("processed", "SBIR_DATA_PROCESSED_DIR", Path("data/processed")),
            artifacts=ConfigPaths.resolve_data("artifacts", "SBIR_DATA_ARTIFACTS_DIR", Path("artifacts")),
        )
    
    @cached_property
    def taxonomy(self) -> TaxonomyConfig:
        """Get taxonomy configuration."""
        return self._load_yaml("taxonomy", "taxonomy.yaml", TaxonomyConfig)
    
    @cached_property
    def classification(self) -> ClassificationConfig:
        """Get classification configuration."""
        return self._load_yaml("classification", "classification.yaml", ClassificationConfig)
    
    @cached_property
    def enrichment(self) -> EnrichmentConfig:
        """Get enrichment configuration (merged from YAML + env vars)."""
        yaml_config = self._load_yaml("enrichment_yaml", "enrichment.yaml", EnrichmentConfigYAML)
        
        # Merge with env vars (env vars take precedence)
        api_key = os.getenv("SBIR_SAM_API_KEY")
        if api_key:
            return EnrichmentConfig(
                api_key=api_key,
                base_url=os.getenv("SBIR_SAM_API_BASE_URL", yaml_config.default_base_url),
                rate_limit=int(os.getenv("SBIR_SAM_API_RATE_LIMIT", yaml_config.rate_limit)),
                # ... other merged fields
            )
        return EnrichmentConfig.from_yaml(yaml_config)
    
    def reload(self):
        """Clear cache and reload all configs."""
        self._cache.clear()
        # Clear cached_property values
        for attr in ['storage_paths', 'taxonomy', 'classification', 'enrichment']:
            if attr in self.__dict__:
                del self.__dict__[attr]


# Global singleton
_config_manager = ConfigurationManager()


def get_config() -> ConfigurationManager:
    """Get global configuration manager."""
    return _config_manager


# Convenience functions for backward compatibility
def load_config() -> AppConfig:
    """Legacy function - returns app config."""
    cfg = get_config()
    return AppConfig(
        storage=cfg.storage_paths,
        enrichment=cfg.enrichment,
    )
```

**Benefits:**
- Single path resolution implementation
- Consistent caching across all configs
- Clear precedence: env vars > YAML > defaults
- Easy testing with dependency injection
- 200 lines → 100 lines

---

## Example 2: Storage Layer Simplification

### Before: Multiple Writer Classes

```python
# data/storage.py (500+ lines)

class BaseParquetWriter:
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        
    def _convert_to_dataframe(self, records, schema):
        # 30 lines of conversion logic
        ...
    
    def write(self, records, schema):
        # 18 lines of write logic
        ...
    
    def append(self, records, schema):
        # 25 lines of append logic
        ...

class AwardeeProfileWriter(BaseParquetWriter):
    def __init__(self, file_path: Path):
        super().__init__(file_path)
        self.schema = ParquetSchemaManager.get_awardee_profile_schema()
    
    def write(self, profiles: List[AwardeeProfile]) -> None:
        super().write(profiles, self.schema)
    
    def append(self, profiles: List[AwardeeProfile]) -> None:
        super().append(profiles, self.schema)

class ProgramOfficeWriter(BaseParquetWriter):
    # Identical pattern, different schema
    ...

class SolicitationWriter(BaseParquetWriter):
    # Identical pattern, different schema
    ...

class EnrichedDataWriter:
    """Facade that delegates to specific writers."""
    def __init__(self, data_dir: Path):
        self.awardee_writer = AwardeeProfileWriter(data_dir / "awardees.parquet")
        self.program_writer = ProgramOfficeWriter(data_dir / "programs.parquet")
        # ... more writers
    
    def write_awardee_profiles(self, profiles):
        self.awardee_writer.write(profiles)
```

### After: Generic Storage with Type Safety

```python
# data/storage.py (150 lines)

from typing import TypeVar, Generic, List, Dict, Any, Type
from pathlib import Path
import pandas as pd
import pyarrow as pa
from pydantic import BaseModel


T = TypeVar('T', bound=BaseModel)


class ParquetStorage(Generic[T]):
    """Generic Parquet storage for any Pydantic model.
    
    Example:
        >>> storage = ParquetStorage(path, AwardeeProfile, schema)
        >>> storage.write([profile1, profile2])
        >>> profiles = storage.read()
    """
    
    def __init__(
        self, 
        file_path: Path, 
        model_class: Type[T],
        schema: pa.Schema,
    ):
        self.file_path = Path(file_path)
        self.model_class = model_class
        self.schema = schema
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def write(self, records: List[T]) -> None:
        """Write records to Parquet."""
        if not records:
            return
        
        # Convert Pydantic models to dicts
        data = [r.model_dump(mode='python') for r in records]
        df = pd.DataFrame(data)
        
        df.to_parquet(
            self.file_path,
            schema=self.schema,
            index=False,
            compression='snappy',
            engine='pyarrow',
        )
    
    def append(self, records: List[T]) -> None:
        """Append records to existing file."""
        if not records:
            return
        
        existing = self.read() if self.file_path.exists() else []
        all_records = existing + records
        self.write(all_records)
    
    def read(self, filters: Dict[str, Any] = None) -> List[T]:
        """Read records with optional filtering."""
        if not self.file_path.exists():
            return []
        
        df = pd.read_parquet(self.file_path, engine='pyarrow')
        
        # Apply filters if provided
        if filters:
            for col, value in filters.items():
                df = df[df[col] == value]
        
        # Convert back to Pydantic models
        return [self.model_class(**row) for row in df.to_dict('records')]
    
    def update(self, records: List[T], key_field: str = 'id') -> None:
        """Update existing records by key."""
        if not records:
            return
        
        existing = self.read()
        update_keys = {getattr(r, key_field) for r in records}
        
        # Keep existing records not in update set
        updated = [r for r in existing if getattr(r, key_field) not in update_keys]
        updated.extend(records)
        
        self.write(updated)


class StorageFactory:
    """Factory for creating typed storage instances."""
    
    @staticmethod
    def create_awardee_storage(data_dir: Path) -> ParquetStorage[AwardeeProfile]:
        return ParquetStorage(
            data_dir / "awardee_profiles.parquet",
            AwardeeProfile,
            ParquetSchemaManager.get_awardee_profile_schema(),
        )
    
    @staticmethod
    def create_program_office_storage(data_dir: Path) -> ParquetStorage[ProgramOffice]:
        return ParquetStorage(
            data_dir / "program_offices.parquet",
            ProgramOffice,
            ParquetSchemaManager.get_program_office_schema(),
        )
    
    @staticmethod
    def create_solicitation_storage(data_dir: Path) -> ParquetStorage[Solicitation]:
        return ParquetStorage(
            data_dir / "solicitations.parquet",
            Solicitation,
            ParquetSchemaManager.get_solicitation_schema(),
        )


# Usage example
data_dir = Path("data/processed")
awardee_storage = StorageFactory.create_awardee_storage(data_dir)
awardee_storage.write([profile1, profile2])
profiles = awardee_storage.read(filters={'state': 'CA'})
```

**Benefits:**
- 500 lines → 150 lines (70% reduction)
- Type-safe operations
- Single implementation to maintain
- Easier testing
- No facade pattern needed

---

## Example 3: Enrichment Service Consolidation

### Before: Scattered Logic

```python
# features/enrichment.py
class EnrichmentOrchestrator:
    def enrich_award(self, award):
        # 50 lines of enrichment logic
        ...

# features/batch_enrichment.py
class BatchEnrichmentOptimizer:
    def enrich_batch(self, awards):
        # 80 lines duplicating orchestrator logic
        # with batching
        ...

# features/fallback_enrichment.py
def enrich_with_fallback(award):
    # 30 lines of fallback logic
    ...

# Usage is unclear
orchestrator = EnrichmentOrchestrator()
result1 = orchestrator.enrich_award(award)

# Or use batch?
optimizer = BatchEnrichmentOptimizer()
results = optimizer.enrich_batch(awards)

# Or use fallback?
result2 = enrich_with_fallback(award)
```

### After: Unified Service with Strategies

```python
# features/enrichment.py

from enum import Enum
from typing import List, Protocol


class EnrichmentStrategy(Enum):
    """Available enrichment strategies."""
    SINGLE = "single"      # One-at-a-time enrichment
    BATCH = "batch"        # Batch with deduplication
    FALLBACK = "fallback"  # In-memory fallback only


class EnrichmentProvider(Protocol):
    """Protocol for enrichment providers."""
    
    def enrich_award(self, award: Award) -> EnrichedAward:
        """Enrich a single award."""
        ...


class APIEnrichmentProvider:
    """Enrichment using external APIs with cache."""
    
    def __init__(self, cache: SolicitationCache, metrics: EnrichmentMetrics):
        self.cache = cache
        self.metrics = metrics
        self.nih_client = None
    
    def enrich_award(self, award: Award) -> EnrichedAward:
        """Enrich award from API or cache."""
        # Original EnrichmentOrchestrator logic here
        api_source = self._determine_api_source(award)
        solicitation_id = self._extract_solicitation_id(award)
        
        # Check cache
        cached = self.cache.get(api_source, solicitation_id)
        if cached:
            self.metrics.record_cache_hit(api_source)
            return self._build_enriched_award(award, cached)
        
        # Fetch from API
        data = self._fetch_from_api(api_source, solicitation_id)
        if data:
            self.cache.put(api_source, solicitation_id, data.description, data.keywords)
            return self._build_enriched_award(award, data)
        
        return EnrichedAward(award=award, enrichment_status="enrichment_failed")


class FallbackEnrichmentProvider:
    """Enrichment using in-memory heuristics."""
    
    def enrich_award(self, award: Award) -> EnrichedAward:
        """Enrich using topic/agency heuristics."""
        # Fallback logic from fallback_enrichment.py
        description = self._infer_from_topic(award.topic_code)
        keywords = self._infer_from_agency(award.agency)
        
        return EnrichedAward(
            award=award,
            enrichment_status="enriched",
            solicitation_description=description,
            solicitation_keywords=keywords,
            api_source="fallback",
        )


class EnrichmentService:
    """Unified enrichment service with pluggable strategies.
    
    Example:
        >>> service = EnrichmentService(strategy=EnrichmentStrategy.BATCH)
        >>> enriched = service.enrich(awards)
        >>> print(f"Enriched {len(enriched)} awards")
    """
    
    def __init__(
        self,
        strategy: EnrichmentStrategy = EnrichmentStrategy.BATCH,
        cache: SolicitationCache | None = None,
        metrics: EnrichmentMetrics | None = None,
    ):
        self.strategy = strategy
        self.cache = cache or SolicitationCache()
        self.metrics = metrics or EnrichmentMetrics()
        
        # Initialize providers
        self.api_provider = APIEnrichmentProvider(self.cache, self.metrics)
        self.fallback_provider = FallbackEnrichmentProvider()
    
    def enrich(self, awards: List[Award] | Award) -> List[EnrichedAward] | EnrichedAward:
        """Enrich award(s) using configured strategy.
        
        Args:
            awards: Single award or list of awards
            
        Returns:
            Enriched award(s) in same format as input
        """
        is_single = isinstance(awards, Award)
        award_list = [awards] if is_single else awards
        
        if self.strategy == EnrichmentStrategy.SINGLE:
            results = self._enrich_single(award_list)
        elif self.strategy == EnrichmentStrategy.BATCH:
            results = self._enrich_batch(award_list)
        else:  # FALLBACK
            results = self._enrich_fallback(award_list)
        
        return results[0] if is_single else results
    
    def _enrich_single(self, awards: List[Award]) -> List[EnrichedAward]:
        """Enrich one at a time with fallback on failure."""
        results = []
        for award in awards:
            try:
                enriched = self.api_provider.enrich_award(award)
                if enriched.enrichment_status == "enrichment_failed":
                    # Fallback to heuristics
                    enriched = self.fallback_provider.enrich_award(award)
                results.append(enriched)
            except Exception as e:
                # Full fallback on exception
                logger.warning(f"Enrichment error for {award.award_id}: {e}")
                results.append(self.fallback_provider.enrich_award(award))
        return results
    
    def _enrich_batch(self, awards: List[Award]) -> List[EnrichedAward]:
        """Enrich with deduplication by solicitation."""
        # Group by (api_source, solicitation_id)
        groups = self._group_by_solicitation(awards)
        
        # Enrich unique solicitations only
        solicitation_cache = {}
        for (api_source, sol_id), group_awards in groups.items():
            representative = group_awards[0]
            enriched = self.api_provider.enrich_award(representative)
            solicitation_cache[(api_source, sol_id)] = enriched
        
        # Apply to all awards in original order
        results = []
        for award in awards:
            key = self._get_solicitation_key(award)
            if key and key in solicitation_cache:
                template = solicitation_cache[key]
                results.append(EnrichedAward(
                    award=award,
                    enrichment_status=template.enrichment_status,
                    solicitation_description=template.solicitation_description,
                    solicitation_keywords=template.solicitation_keywords,
                    api_source=template.api_source,
                ))
            else:
                results.append(self.fallback_provider.enrich_award(award))
        
        return results
    
    def _enrich_fallback(self, awards: List[Award]) -> List[EnrichedAward]:
        """Enrich using fallback provider only."""
        return [self.fallback_provider.enrich_award(a) for a in awards]
    
    def flush_metrics(self) -> Path:
        """Flush enrichment metrics."""
        return self.metrics.flush()


# Simple usage
service = EnrichmentService()
enriched_awards = service.enrich(awards)  # Auto-detects single vs batch
```

**Benefits:**
- Clear entry point for all enrichment
- Strategy pattern for different modes
- Easy to test each provider
- Consistent error handling
- Remove 3 separate modules → 1 unified service

---

## Example 4: Unified Scoring API

### Before: Multiple Scoring Implementations

```python
# models/applicability.py
model = ApplicabilityModel()
model.fit(examples)
score = model.predict(award_id, text)

# models/rules_scorer.py
scorer = RuleBasedScorer()
scores = scorer.score_text(text, agency="DoD")

# models/enhanced_scoring.py
classifier = EnhancedCETClassifier(include_solicitation_text=True)
classifier.fit(data, y, categories)
probs = classifier.predict_proba(awards)

# data/classification.py - hybrid logic mixed in
ml_score = ml_model.predict(...)
rule_score = rule_scorer.score_text(...)
hybrid = ml_score * (1 - weight) + rule_score * weight
```

### After: Unified Scorer with Composition

```python
# models/scorer.py

from typing import Literal, Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ScoringResult:
    """Result of CET scoring."""
    award_id: str
    primary_cet_id: str
    primary_score: float
    classification: Literal["High", "Medium", "Low"]
    supporting_cets: List[Tuple[str, float]]
    method: Literal["ml", "rules", "hybrid"]
    metadata: Dict[str, Any]


class CETScorer:
    """Unified CET scoring with multiple strategies.
    
    Supports three scoring modes:
    - ML: TF-IDF + Logistic Regression
    - Rules: Keyword matching + priors
    - Hybrid: Weighted combination of ML + Rules
    
    Example:
        >>> scorer = CETScorer(mode="hybrid", hybrid_weight=0.3)
        >>> result = scorer.score(award)
        >>> print(f"{result.primary_cet_id}: {result.primary_score}")
    """
    
    def __init__(
        self,
        mode: Literal["ml", "rules", "hybrid"] = "hybrid",
        hybrid_weight: float = 0.5,
        *,
        ml_model: ApplicabilityModel | None = None,
        rule_scorer: RuleBasedScorer | None = None,
    ):
        """Initialize scorer.
        
        Args:
            mode: Scoring strategy to use
            hybrid_weight: Weight for rule component in hybrid mode (0-1)
            ml_model: Optional pre-trained ML model
            rule_scorer: Optional pre-configured rule scorer
        """
        self.mode = mode
        self.hybrid_weight = hybrid_weight
        
        # Initialize components
        self.ml_model = ml_model or ApplicabilityModel()
        self.rule_scorer = rule_scorer or RuleBasedScorer()
        
        # Validate hybrid weight
        if not 0.0 <= hybrid_weight <= 1.0:
            raise ValueError("hybrid_weight must be between 0 and 1")
    
    def fit(self, examples: List[TrainingExample]) -> "CETScorer":
        """Train ML model (no-op for rules-only mode).
        
        Args:
            examples: Training examples
            
        Returns:
            Self for chaining
        """
        if self.mode in ("ml", "hybrid"):
            self.ml_model.fit(examples)
        return self
    
    def score(
        self,
        award: Award,
        enriched: EnrichedAward | None = None,
    ) -> ScoringResult:
        """Score award with configured strategy.
        
        Args:
            award: Award to score
            enriched: Optional enriched award data
            
        Returns:
            Scoring result with primary CET and confidence
        """
        # Build text
        text = self._build_text(award, enriched)
        
        # Route to appropriate scorer
        if self.mode == "ml":
            return self._score_ml(award.award_id, text)
        elif self.mode == "rules":
            return self._score_rules(award.award_id, text, award.agency, award.sub_agency)
        else:  # hybrid
            return self._score_hybrid(award.award_id, text, award.agency, award.sub_agency)
    
    def batch_score(
        self,
        awards: List[Award],
        enriched_awards: List[EnrichedAward] | None = None,
    ) -> List[ScoringResult]:
        """Score multiple awards efficiently.
        
        Args:
            awards: Awards to score
            enriched_awards: Optional enriched data (same order as awards)
            
        Returns:
            List of scoring results
        """
        if enriched_awards is None:
            enriched_awards = [None] * len(awards)
        
        if self.mode == "ml":
            # Use batch prediction for efficiency
            texts = [self._build_text(a, e) for a, e in zip(awards, enriched_awards)]
            records = [(a.award_id, t) for a, t in zip(awards, texts)]
            ml_scores = self.ml_model.batch_predict(records)
            return [self._ml_to_result(s) for s in ml_scores]
        else:
            # Process individually (rules/hybrid don't have batch optimization)
            return [self.score(a, e) for a, e in zip(awards, enriched_awards)]
    
    def _score_ml(self, award_id: str, text: str) -> ScoringResult:
        """Score using ML model only."""
        ml_score = self.ml_model.predict(award_id, text)
        return self._ml_to_result(ml_score)
    
    def _score_rules(
        self,
        award_id: str,
        text: str,
        agency: str,
        sub_agency: str | None,
    ) -> ScoringResult:
        """Score using rules only."""
        scores = self.rule_scorer.score_text(text, agency=agency, branch=sub_agency)
        top_cets = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        primary_cet, primary_score = top_cets[0]
        supporting = top_cets[1:4]
        
        return ScoringResult(
            award_id=award_id,
            primary_cet_id=primary_cet,
            primary_score=primary_score,
            classification=self._classify_score(primary_score),
            supporting_cets=supporting,
            method="rules",
            metadata={"all_scores": scores},
        )
    
    def _score_hybrid(
        self,
        award_id: str,
        text: str,
        agency: str,
        sub_agency: str | None,
    ) -> ScoringResult:
        """Score using weighted combination of ML and rules."""
        # Get both scores
        ml_score = self.ml_model.predict(award_id, text)
        rule_scores = self.rule_scorer.score_text(text, agency=agency, branch=sub_agency)
        
        # Blend scores for each CET
        blended_scores = {}
        
        # Start with ML scores
        ml_dict = {ml_score.primary_cet_id: ml_score.primary_score}
        ml_dict.update(dict(ml_score.supporting_ranked))
        
        # Combine all CETs from both sources
        all_cets = set(ml_dict.keys()) | set(rule_scores.keys())
        
        for cet_id in all_cets:
            ml_val = ml_dict.get(cet_id, 0.0)
            rule_val = rule_scores.get(cet_id, 0.0)
            
            # Weighted blend
            blended_scores[cet_id] = (
                ml_val * (1 - self.hybrid_weight) + 
                rule_val * self.hybrid_weight
            )
        
        # Rank and extract top results
        top_cets = sorted(blended_scores.items(), key=lambda x: x[1], reverse=True)
        primary_cet, primary_score = top_cets[0]
        supporting = top_cets[1:4]
        
        return ScoringResult(
            award_id=award_id,
            primary_cet_id=primary_cet,
            primary_score=primary_score,
            classification=self._classify_score(primary_score),
            supporting_cets=supporting,
            method="hybrid",
            metadata={
                "ml_primary": ml_score.primary_cet_id,
                "ml_score": ml_score.primary_score,
                "rule_scores": rule_scores,
                "hybrid_weight": self.hybrid_weight,
            },
        )
    
    def _build_text(self, award: Award, enriched: EnrichedAward | None) -> str:
        """Build text from award and enrichment."""
        parts = []
        
        if award.abstract:
            parts.append(award.abstract)
        
        if award.keywords:
            parts.extend(award.keywords)
        
        if enriched and enriched.solicitation_description:
            parts.append(enriched.solicitation_description)
        
        if enriched and enriched.solicitation_keywords:
            parts.extend(enriched.solicitation_keywords)
        
        return " ".join(parts)
    
    def _classify_score(self, score: float) -> Literal["High", "Medium", "Low"]:
        """Classify numeric score into band."""
        if score >= 70:
            return "High"
        elif score >= 40:
            return "Medium"
        else:
            return "Low"
    
    def _ml_to_result(self, ml_score: ApplicabilityScore) -> ScoringResult:
        """Convert ML score to unified result."""
        return ScoringResult(
            award_id=ml_score.award_id,
            primary_cet_id=ml_score.primary_cet_id,
            primary_score=ml_score.primary_score,
            classification=ml_score.classification,
            supporting_cets=ml_score.supporting_ranked,
            method="ml",
            metadata={},
        )


# Usage examples

# Simple ML scoring
scorer = CETScorer(mode="ml")
scorer.fit(training_examples)
result = scorer.score(award)

# Rule-based scoring
scorer = CETScorer(mode="rules")
result = scorer.score(award)  # No fit needed

# Hybrid scoring (default)
scorer = CETScorer(mode="hybrid", hybrid_weight=0.3)
scorer.fit(training_examples)
result = scorer.score(award, enriched_award)

# Batch scoring
results = scorer.batch_score(awards, enriched_awards)
```

**Benefits:**
- Single API for all scoring modes
- Clear composition of ML and rule-based
- Easy to switch strategies
- Batch optimization for ML mode
- Remove hybrid logic from classification.py
- Type-safe results

---

## Example 5: Dependency Injection Pattern

### Before: Hard-coded Dependencies

```python
# features/enrichment.py
class EnrichmentOrchestrator:
    def __init__(self):
        self.cache = SolicitationCache()  # Hard-coded dependency
        self.metrics = EnrichmentMetrics()  # Hard-coded dependency
        self.nih_client = NIHClient()  # Hard-coded dependency

# Testing is difficult
def test_enrichment():
    # Can't easily mock cache or metrics
    orchestrator = EnrichmentOrchestrator()
    # Have to patch at module level
    with patch('features.enrichment.SolicitationCache'):
        ...
```

### After: Constructor Injection

```python
# features/enrichment.py
class EnrichmentOrchestrator:
    """Enrichment orchestrator with dependency injection.
    
    Example:
        >>> # Production use
        >>> orchestrator = EnrichmentOrchestrator()
        
        >>> # Testing with mocks
        >>> mock_cache = Mock(spec=SolicitationCache)
        >>> orchestrator = EnrichmentOrchestrator(cache=mock_cache)
    """
    
    def __init__(
        self,
        cache: SolicitationCache | None = None,
        metrics: EnrichmentMetrics | None = None,
        nih_client: NIHClient | None = None,
    ):
        """Initialize with dependencies.
        
        Args:
            cache: Solicitation cache (creates default if None)
            metrics: Metrics tracker (creates default if None)
            nih_client: NIH API client (creates default if None)
        """
        self.cache = cache or SolicitationCache()
        self.metrics = metrics or EnrichmentMetrics()
        self.nih_client = nih_client  # Lazy init on first use


# Testing is now easy
def test_enrichment_with_cache_hit():
    # Create mocks
    mock_cache = Mock(spec=SolicitationCache)
    mock_cache.get.return_value = SolicitationData(...)
    
    mock_metrics = Mock(spec=EnrichmentMetrics)
    
    # Inject dependencies
    orchestrator = EnrichmentOrchestrator(
        cache=mock_cache,
        metrics=mock_metrics,
    )
    
    # Test
    result = orchestrator.enrich_award(award)
    
    # Verify interactions
    mock_cache.get.assert_called_once()
    mock_metrics.record_cache_hit.assert_called_once()
```

---

## Summary

These examples demonstrate practical refactoring patterns that:

1. **Reduce duplication** - Single implementation instead of multiple similar classes
2. **Improve testability** - Dependency injection enables easy mocking
3. **Enhance clarity** - Clear APIs with explicit strategies
4. **Maintain compatibility** - Backward-compatible wrappers where needed
5. **Type safety** - Generics and protocols for compile-time checking

Each refactoring can be done incrementally with full test coverage maintained throughout.