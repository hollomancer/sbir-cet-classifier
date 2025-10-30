"""Centralized configuration manager with caching and validation.

This module provides a unified configuration management system that consolidates
YAML loading, implements intelligent caching with file modification detection,
and provides type-safe configuration access methods.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, TypeVar, Type, Union
from functools import lru_cache
from dataclasses import dataclass, field

import yaml
from pydantic import BaseModel, ValidationError

from .yaml_config import (
    TaxonomyConfig,
    ClassificationConfig, 
    EnrichmentConfig,
)
from .classification_config import ClassificationRules

T = TypeVar('T', bound=BaseModel)


class ConfigurationError(Exception):
    """Configuration-related errors."""
    pass


@dataclass
class PerformanceMetrics:
    """Performance metrics for configuration operations."""
    load_times: Dict[str, float] = field(default_factory=dict)
    cache_hits: Dict[str, int] = field(default_factory=dict)
    cache_misses: Dict[str, int] = field(default_factory=dict)
    total_loads: int = 0
    total_cache_hits: int = 0
    
    def record_load(self, config_name: str, load_time: float, cache_hit: bool) -> None:
        """Record a configuration load operation."""
        self.load_times[config_name] = load_time
        self.total_loads += 1
        
        if cache_hit:
            self.cache_hits[config_name] = self.cache_hits.get(config_name, 0) + 1
            self.total_cache_hits += 1
        else:
            self.cache_misses[config_name] = self.cache_misses.get(config_name, 0) + 1
    
    def get_average_load_time(self, config_name: Optional[str] = None) -> float:
        """Get average load time for a specific config or overall."""
        if config_name:
            return self.load_times.get(config_name, 0.0)
        
        if not self.load_times:
            return 0.0
        
        return sum(self.load_times.values()) / len(self.load_times)
    
    def get_cache_hit_rate(self) -> float:
        """Get overall cache hit rate."""
        if self.total_loads == 0:
            return 0.0
        
        return self.total_cache_hits / self.total_loads


class ConfigurationManager:
    """Centralized configuration management with caching and validation.
    
    Provides intelligent caching with file modification detection, type-safe
    configuration access, and hot-reloading capabilities.
    """
    
    def __init__(self, config_dir: Optional[Path] = None, enable_performance_monitoring: bool = True):
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files. If None,
                       uses SBIR_CONFIG_DIR environment variable or defaults
                       to config/ in project root.
            enable_performance_monitoring: Whether to track performance metrics
        """
        self.config_dir = self._resolve_config_dir(config_dir)
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._performance_monitoring = enable_performance_monitoring
        self._metrics = PerformanceMetrics() if enable_performance_monitoring else None
        self._loaders = {
            'taxonomy': self._load_taxonomy_config,
            'classification': self._load_classification_config,
            'enrichment': self._load_enrichment_config,
        }
    
    def _resolve_config_dir(self, config_dir: Optional[Path]) -> Path:
        """Resolve configuration directory path."""
        if config_dir is not None:
            return Path(config_dir).resolve()
        
        # Check environment variable
        env_dir = os.getenv("SBIR_CONFIG_DIR")
        if env_dir:
            return Path(env_dir).resolve()
        
        # Default to project root config directory
        return Path(__file__).parent.parent.parent.parent / "config"
    
    def _get_config_path(self, config_name: str) -> Path:
        """Get full path for a configuration file."""
        return self.config_dir / f"{config_name}.yaml"
    
    def _get_file_mtime(self, path: Path) -> float:
        """Get file modification time, return 0 if file doesn't exist."""
        try:
            return path.stat().st_mtime
        except (OSError, FileNotFoundError):
            return 0.0
    
    def _is_cache_valid(self, config_name: str) -> bool:
        """Check if cached configuration is still valid."""
        if config_name not in self._cache:
            return False
        
        config_path = self._get_config_path(config_name)
        current_mtime = self._get_file_mtime(config_path)
        cached_mtime = self._timestamps.get(config_name, 0.0)
        
        return current_mtime <= cached_mtime
    
    def _is_cache_valid_for_path(self, cache_key: str, config_path: Path) -> bool:
        """Check if cached configuration is still valid for a specific path."""
        if cache_key not in self._cache:
            return False
        
        current_mtime = self._get_file_mtime(config_path)
        cached_mtime = self._timestamps.get(cache_key, 0.0)
        
        return current_mtime <= cached_mtime
    
    def _load_yaml_file(self, path: Path) -> Dict[str, Any]:
        """Load and parse YAML file with error handling."""
        try:
            if not path.exists():
                raise ConfigurationError(f"Configuration file not found: {path}")
            
            with path.open('r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if data is None:
                return {}
            
            if not isinstance(data, dict):
                raise ConfigurationError(f"Configuration file must contain a YAML object: {path}")
            
            return data
        
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in {path}: {e}") from e
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration from {path}: {e}") from e
    
    def _load_taxonomy_config(self, path: Path) -> TaxonomyConfig:
        """Load taxonomy configuration from YAML file."""
        data = self._load_yaml_file(path)
        return TaxonomyConfig(**data)
    
    def _load_classification_config(self, path: Path) -> ClassificationConfig:
        """Load classification configuration from YAML file."""
        data = self._load_yaml_file(path)
        return ClassificationConfig(**data)
    
    def _load_enrichment_config(self, path: Path) -> EnrichmentConfig:
        """Load enrichment configuration from YAML file."""
        data = self._load_yaml_file(path)
        return EnrichmentConfig(**data)
    
    def _load_classification_rules(self, path: Path) -> ClassificationRules:
        """Load classification rules from YAML file."""
        data = self._load_yaml_file(path)
        
        # Build a payload containing only the keys we care about
        payload: Dict[str, Any] = {
            "version": data.get("version"),
            "agency_priors": data.get("agency_priors", {}),
            "branch_priors": data.get("branch_priors", {}),
            "cet_keywords": data.get("cet_keywords", {}),
            "context_rules": data.get("context_rules", {}),
        }
        
        return ClassificationRules(**payload)
    
    def get_config(self, config_name: str, force_reload: bool = False) -> Any:
        """Get configuration with automatic caching and reload detection.
        
        Args:
            config_name: Name of configuration (taxonomy, classification, enrichment, etc.)
            force_reload: Force reload even if cache is valid
            
        Returns:
            Validated configuration object
            
        Raises:
            ConfigurationError: If configuration cannot be loaded or validated
        """
        start_time = time.time() if self._performance_monitoring else 0
        cache_hit = False
        
        try:
            # Check cache validity
            if not force_reload and self._is_cache_valid(config_name):
                cache_hit = True
                return self._cache[config_name]
            
            # Use specialized loader if available
            if config_name in self._loaders:
                try:
                    config_path = self._get_config_path(config_name)
                    config = self._loaders[config_name](config_path)
                    
                    # Update cache
                    self._cache[config_name] = config
                    self._timestamps[config_name] = self._get_file_mtime(config_path)
                    
                    return config
                
                except Exception as e:
                    raise ConfigurationError(f"Error loading {config_name} configuration: {e}") from e
            
            # Fallback to generic YAML loading
            config_path = self._get_config_path(config_name)
            data = self._load_yaml_file(config_path)
            
            # Update cache
            self._cache[config_name] = data
            self._timestamps[config_name] = self._get_file_mtime(config_path)
            
            return data
        
        finally:
            # Record performance metrics
            if self._performance_monitoring and self._metrics:
                load_time = time.time() - start_time
                self._metrics.record_load(config_name, load_time, cache_hit)
    
    def get_taxonomy_config(self, force_reload: bool = False) -> TaxonomyConfig:
        """Get taxonomy configuration with type safety."""
        return self.get_config('taxonomy', force_reload)
    
    def get_classification_config(self, force_reload: bool = False) -> ClassificationConfig:
        """Get classification configuration with type safety."""
        return self.get_config('classification', force_reload)
    
    def get_enrichment_config(self, force_reload: bool = False) -> EnrichmentConfig:
        """Get enrichment configuration with type safety."""
        return self.get_config('enrichment', force_reload)
    
    def get_classification_rules(self, force_reload: bool = False) -> ClassificationRules:
        """Get classification rules configuration with type safety."""
        # Classification rules are loaded from the classification.yaml file
        config_path = self._get_config_path('classification')
        
        # Check cache validity
        cache_key = 'classification_rules'
        if not force_reload and self._is_cache_valid_for_path(cache_key, config_path):
            return self._cache[cache_key]
        
        # Load and parse
        config = self._load_classification_rules(config_path)
        
        # Update cache
        self._cache[cache_key] = config
        self._timestamps[cache_key] = self._get_file_mtime(config_path)
        
        return config
    
    def reload_all(self) -> None:
        """Force reload all cached configurations."""
        self._cache.clear()
        self._timestamps.clear()
    
    def validate_config(self, config_name: str, config_class: Type[T]) -> T:
        """Validate configuration against Pydantic model.
        
        Args:
            config_name: Name of configuration file
            config_class: Pydantic model class for validation
            
        Returns:
            Validated configuration object
            
        Raises:
            ConfigurationError: If validation fails
        """
        config_path = self._get_config_path(config_name)
        data = self._load_yaml_file(config_path)
        
        try:
            return config_class(**data)
        except ValidationError as e:
            raise ConfigurationError(f"Validation failed for {config_name}: {e}") from e
    
    def validate_all_configs(self) -> Dict[str, Union[str, Exception]]:
        """Validate all known configuration files.
        
        Returns:
            Dictionary mapping config names to validation results.
            Success is indicated by "OK", failures by the exception.
        """
        results = {}
        
        # Validate known configuration types
        config_validators = {
            'taxonomy': TaxonomyConfig,
            'classification': ClassificationConfig,
            'enrichment': EnrichmentConfig,
        }
        
        # Special handling for classification_rules (uses classification.yaml)
        try:
            self.get_classification_rules()
            results['classification_rules'] = "OK"
        except Exception as e:
            results['classification_rules'] = e
        
        for config_name, config_class in config_validators.items():
            try:
                self.validate_config(config_name, config_class)
                results[config_name] = "OK"
            except Exception as e:
                results[config_name] = e
        
        return results
    
    def get_validation_errors(self) -> Dict[str, str]:
        """Get validation errors for all configurations.
        
        Returns:
            Dictionary mapping config names to error messages.
            Only failed validations are included.
        """
        results = self.validate_all_configs()
        errors = {}
        
        for config_name, result in results.items():
            if result != "OK":
                errors[config_name] = str(result)
        
        return errors
    
    def list_available_configs(self) -> list[str]:
        """List all available configuration files."""
        configs = []
        for file_path in self.config_dir.glob("*.yaml"):
            configs.append(file_path.stem)
        return sorted(configs)
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        stats = {
            'cached_configs': list(self._cache.keys()),
            'cache_size': len(self._cache),
            'timestamps': dict(self._timestamps),
        }
        
        if self._performance_monitoring and self._metrics:
            stats.update({
                'performance': {
                    'total_loads': self._metrics.total_loads,
                    'cache_hit_rate': self._metrics.get_cache_hit_rate(),
                    'average_load_time': self._metrics.get_average_load_time(),
                    'load_times_by_config': dict(self._metrics.load_times),
                    'cache_hits_by_config': dict(self._metrics.cache_hits),
                    'cache_misses_by_config': dict(self._metrics.cache_misses),
                }
            })
        
        return stats
    
    def get_performance_metrics(self) -> Optional[PerformanceMetrics]:
        """Get performance metrics if monitoring is enabled."""
        return self._metrics
    
    def optimize_cache(self) -> None:
        """Optimize cache by removing stale entries and preloading frequently used configs."""
        if not self._performance_monitoring or not self._metrics:
            return
        
        # Remove configs that haven't been accessed recently
        current_time = time.time()
        stale_threshold = 3600  # 1 hour
        
        stale_configs = []
        for config_name, timestamp in self._timestamps.items():
            if current_time - timestamp > stale_threshold:
                # Check if this config is frequently accessed
                hits = self._metrics.cache_hits.get(config_name, 0)
                misses = self._metrics.cache_misses.get(config_name, 0)
                
                # Keep frequently accessed configs even if stale
                if hits + misses < 5:  # Low usage threshold
                    stale_configs.append(config_name)
        
        # Remove stale configs
        for config_name in stale_configs:
            self._cache.pop(config_name, None)
            self._timestamps.pop(config_name, None)
    
    def preload_configs(self, config_names: Optional[list[str]] = None) -> None:
        """Preload configurations to improve performance.
        
        Args:
            config_names: List of config names to preload. If None, preloads all known configs.
        """
        if config_names is None:
            config_names = list(self._loaders.keys())
        
        for config_name in config_names:
            try:
                self.get_config(config_name)
            except Exception:
                # Ignore errors during preloading
                pass


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager(config_dir: Optional[Path] = None) -> ConfigurationManager:
    """Get global configuration manager instance.
    
    Args:
        config_dir: Configuration directory (only used on first call)
        
    Returns:
        Global ConfigurationManager instance
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigurationManager(config_dir)
    
    return _config_manager


def reset_config_manager() -> None:
    """Reset global configuration manager (mainly for testing)."""
    global _config_manager
    _config_manager = None


__all__ = [
    'ConfigurationManager',
    'ConfigurationError',
    'get_config_manager',
    'reset_config_manager',
]