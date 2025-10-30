"""
Configuration CLI commands (e.g. `config validate`).

This module provides a small Typer subcommand group for validating and
inspecting the YAML configuration files used by the application.
"""

from __future__ import annotations

import typer

from sbir_cet_classifier.common.configuration_manager import (
    get_config_manager,
    ConfigurationError,
)

app = typer.Typer(help="Inspect and validate configuration files")


@app.command("validate")
def validate() -> None:
    """Validate YAML configuration files used by the application.

    This command uses the centralized configuration manager to validate
    all configuration files with improved error reporting.

        python -m sbir_cet_classifier.cli.app config validate
    """
    typer.echo("Validating YAML configuration files...\n")
    
    config_manager = get_config_manager()
    validation_results = config_manager.validate_all_configs()
    
    has_errors = False
    
    for config_name, result in validation_results.items():
        if result == "OK":
            typer.echo(f"✅ {config_name}.yaml")
            
            # Show additional details for successful validations
            try:
                if config_name == "taxonomy":
                    config = config_manager.get_taxonomy_config()
                    typer.echo(f"   Version: {getattr(config, 'version', 'N/A')}")
                    typer.echo(f"   Effective date: {getattr(config, 'effective_date', 'N/A')}")
                    categories = getattr(config, "categories", None)
                    typer.echo(f"   Categories: {len(categories) if categories is not None else 'N/A'}")
                    
                elif config_name == "classification":
                    config = config_manager.get_classification_config()
                    try:
                        ngrams = config.vectorizer.ngram_range
                        stop_words_count = len(config.stop_words)
                        bands = ", ".join(config.scoring.bands.keys())
                        typer.echo(f"   Vectorizer: {ngrams} n-grams")
                        typer.echo(f"   Stop words: {stop_words_count} terms")
                        typer.echo(f"   Bands: {bands}")
                    except Exception:
                        typer.echo("   Configuration loaded successfully")
                        
                elif config_name == "enrichment":
                    config = config_manager.get_enrichment_config()
                    typer.echo(f"   Version: {getattr(config, 'version', 'N/A')}")
                    try:
                        topic_domains = getattr(config, "topic_domains", {}) or {}
                        agency_focus = getattr(config, "agency_focus", {}) or {}
                        typer.echo(f"   Topic domains: {len(topic_domains)}")
                        typer.echo(f"   Agencies: {len(agency_focus)}")
                    except Exception:
                        typer.echo("   Configuration loaded successfully")
                        
                elif config_name == "classification_rules":
                    config = config_manager.get_classification_rules()
                    typer.echo(f"   CET keyword sets: {len(config.cet_keywords)}")
                    typer.echo(f"   Agency priors: {len(config.agency_priors)} agencies")
                    typer.echo(f"   Context rules: {len(config.context_rules)} CET areas")
                    
            except Exception:
                # If we can't get details, that's OK - validation passed
                pass
        else:
            has_errors = True
            typer.echo(f"❌ {config_name}.yaml: {result}")
    
    if has_errors:
        typer.echo("\n❌ Some configuration files have validation errors!")
        raise typer.Exit(code=1)
    else:
        typer.echo("\n✅ All configuration files are valid!")


@app.command("show")
def show(
    section: str = typer.Option(
        "all",
        "--section",
        "-s",
        help="Which section to show: taxonomy|classification|enrichment|rules|cet_keywords|priors|context_rules|all",
    ),
    limit: int = typer.Option(10, "--limit", "-n", help="Limit items shown for long lists"),
) -> None:
    """Show configuration sections and rule summaries for quick inspection."""
    sec = (section or "all").strip().lower()

    config_manager = get_config_manager()
    
    # Taxonomy section
    if sec in ("taxonomy", "all"):
        try:
            tax_config = config_manager.get_taxonomy_config()
            categories = getattr(tax_config, "categories", []) or []
            typer.echo("🧭 taxonomy.yaml")
            typer.echo(f"   Version: {getattr(tax_config, 'version', 'N/A')}")
            typer.echo(f"   Effective date: {getattr(tax_config, 'effective_date', 'N/A')}")
            typer.echo(f"   Categories: {len(categories)}")
            if categories:
                typer.echo("   Sample categories:")
                for cat in categories[:limit]:
                    cat_id = getattr(cat, "id", "N/A")
                    cat_name = getattr(cat, "name", "N/A")
                    typer.echo(f"     - {cat_id}: {cat_name}")
        except Exception as exc:
            typer.echo(f"❌ taxonomy.yaml: {exc}")

    # Classification (hyperparameters) section
    if sec in ("classification", "all"):
        try:
            clf_config = config_manager.get_classification_config()
            typer.echo("\n⚙️  classification.yaml")
            try:
                ngrams = clf_config.vectorizer.ngram_range
            except Exception:
                ngrams = "N/A"
            try:
                stop_words_count = len(clf_config.stop_words)
            except Exception:
                stop_words_count = "N/A"
            try:
                bands = list(clf_config.scoring.bands.keys())
            except Exception:
                bands = []
            typer.echo(f"   Vectorizer n-grams: {ngrams}")
            typer.echo(f"   Stop words: {stop_words_count}")
            typer.echo(f"   Bands: {', '.join(bands) if bands else 'N/A'}")
        except Exception as exc:
            typer.echo(f"❌ classification.yaml: {exc}")

    # Enrichment section
    if sec in ("enrichment", "all"):
        try:
            enr_config = config_manager.get_enrichment_config()
            topic_domains = getattr(enr_config, "topic_domains", {}) or {}
            agency_focus = getattr(enr_config, "agency_focus", {}) or {}
            typer.echo("\n🧩 enrichment.yaml")
            typer.echo(f"   Version: {getattr(enr_config, 'version', 'N/A')}")
            typer.echo(f"   Topic domains: {len(topic_domains)}")
            typer.echo(f"   Agencies: {len(agency_focus)}")
            if topic_domains:
                typer.echo("   Sample topic domains:")
                for k in list(topic_domains.keys())[:limit]:
                    typer.echo(f"     - {k}")
        except Exception as exc:
            typer.echo(f"❌ enrichment.yaml: {exc}")

    # Rules (priors, keywords, context rules) section
    if sec in ("rules", "cet_keywords", "priors", "context_rules", "all"):
        try:
            rules = config_manager.get_classification_rules()
            # Overall rules summary
            if sec in ("rules", "all"):
                typer.echo("\n🧠 classification rules (from classification.yaml)")
                typer.echo(f"   CET keyword sets: {len(rules.cet_keywords)}")
                typer.echo(f"   Agency priors: {len(rules.agency_priors)} agencies")
                typer.echo(f"   Branch priors: {len(rules.branch_priors)} branches")
                typer.echo(f"   Context rules: {len(rules.context_rules)} CET areas")

            # CET keywords detail
            if sec in ("cet_keywords", "all"):
                cet_ids = list(rules.cet_keywords.keys())
                typer.echo("\n   CET keywords:")
                for cet_id in cet_ids[:limit]:
                    bucket = rules.cet_keywords.get(cet_id)
                    core = getattr(bucket, "core", []) if bucket is not None else []
                    related = getattr(bucket, "related", []) if bucket is not None else []
                    typer.echo(f"     - {cet_id}: core={len(core)}, related={len(related)}")
                    if core:
                        typer.echo(f"         core sample: {', '.join(core[:min(3, len(core))])}")

            # Priors detail
            if sec in ("priors", "all"):
                typer.echo("\n   Agency priors:")
                for agency in list(rules.agency_priors.keys())[:limit]:
                    typer.echo(f"     - {agency}: {len(rules.agency_priors[agency])} CET boosts")
                if rules.branch_priors:
                    typer.echo("   Branch priors:")
                    for branch in list(rules.branch_priors.keys())[:limit]:
                        typer.echo(
                            f"     - {branch}: {len(rules.branch_priors[branch])} CET boosts"
                        )

            # Context rules detail
            if sec in ("context_rules", "all"):
                typer.echo("\n   Context rules:")
                for cet_id, rule_list in list(rules.context_rules.items())[:limit]:
                    typer.echo(f"     - {cet_id}: {len(rule_list)} rule(s)")
                    if rule_list:
                        r = rule_list[0]
                        req = getattr(r, "required_keywords", None) or []
                        boost = getattr(r, "boost", 0)
                        typer.echo(f"         sample: requires={req}, boost={boost}")
        except Exception as exc:
            typer.echo(f"❌ classification rules: {exc}")


@app.command("check")
def check() -> None:
    """Comprehensive configuration validation with detailed error reporting.
    
    This command provides more detailed validation than the basic 'validate'
    command, including schema validation and configuration consistency checks.
    """
    typer.echo("Running comprehensive configuration validation...\n")
    
    config_manager = get_config_manager()
    
    # Get validation errors
    errors = config_manager.get_validation_errors()
    
    if not errors:
        typer.echo("✅ All configurations are valid!")
        
        # Show cache statistics
        stats = config_manager.get_cache_stats()
        typer.echo(f"\n📊 Cache Statistics:")
        typer.echo(f"   Cached configurations: {stats['cache_size']}")
        typer.echo(f"   Available configurations: {len(config_manager.list_available_configs())}")
        
        return
    
    # Show detailed errors
    typer.echo("❌ Configuration validation errors found:\n")
    
    for config_name, error_msg in errors.items():
        typer.echo(f"🔴 {config_name}.yaml:")
        typer.echo(f"   {error_msg}\n")
    
    typer.echo("Please fix the above errors and run validation again.")
    raise typer.Exit(code=1)


@app.command("reload")
def reload() -> None:
    """Force reload all cached configurations.
    
    This command clears the configuration cache and forces a fresh reload
    of all configuration files. Useful during development or after making
    configuration changes.
    """
    config_manager = get_config_manager()
    config_manager.reload_all()
    
    typer.echo("✅ Configuration cache cleared and reloaded!")
    
    # Show available configurations
    available = config_manager.list_available_configs()
    typer.echo(f"\n📁 Available configurations: {', '.join(available)}")


@app.command("performance")
def performance() -> None:
    """Show configuration loading performance metrics.
    
    This command displays cache hit rates, load times, and other performance
    statistics for configuration operations.
    """
    config_manager = get_config_manager()
    stats = config_manager.get_cache_stats()
    
    typer.echo("📊 Configuration Performance Metrics\n")
    
    # Basic cache info
    typer.echo(f"Cache size: {stats['cache_size']} configurations")
    typer.echo(f"Cached configs: {', '.join(stats['cached_configs'])}")
    
    # Performance metrics if available
    if 'performance' in stats:
        perf = stats['performance']
        typer.echo(f"\n⚡ Performance Statistics:")
        typer.echo(f"   Total loads: {perf['total_loads']}")
        typer.echo(f"   Cache hit rate: {perf['cache_hit_rate']:.2%}")
        typer.echo(f"   Average load time: {perf['average_load_time']:.4f}s")
        
        if perf['load_times_by_config']:
            typer.echo(f"\n⏱️  Load Times by Configuration:")
            for config_name, load_time in perf['load_times_by_config'].items():
                hits = perf['cache_hits_by_config'].get(config_name, 0)
                misses = perf['cache_misses_by_config'].get(config_name, 0)
                typer.echo(f"   {config_name}: {load_time:.4f}s (hits: {hits}, misses: {misses})")
    else:
        typer.echo("\n⚠️  Performance monitoring is disabled")


@app.command("optimize")
def optimize() -> None:
    """Optimize configuration cache and preload frequently used configs.
    
    This command removes stale cache entries and preloads commonly used
    configurations to improve performance.
    """
    config_manager = get_config_manager()
    
    typer.echo("🔧 Optimizing configuration cache...")
    
    # Get stats before optimization
    stats_before = config_manager.get_cache_stats()
    cache_size_before = stats_before['cache_size']
    
    # Optimize cache
    config_manager.optimize_cache()
    
    # Preload common configurations
    typer.echo("   Preloading common configurations...")
    config_manager.preload_configs(['taxonomy', 'classification', 'enrichment'])
    
    # Get stats after optimization
    stats_after = config_manager.get_cache_stats()
    cache_size_after = stats_after['cache_size']
    
    typer.echo(f"✅ Cache optimization complete!")
    typer.echo(f"   Cache size: {cache_size_before} → {cache_size_after}")
    typer.echo(f"   Preloaded: {', '.join(stats_after['cached_configs'])}")


__all__ = ["app"]
