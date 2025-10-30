#!/usr/bin/env python3
"""
Classification rules/config loader.

This module provides a small, well-typed loader for the rule-based parts of
the classification configuration file (the priors, CET keyword lists and
context rules). The main entrypoint is `load_classification_rules()` which
returns a `ClassificationRules` Pydantic model.

The loader is intentionally defensive: the repository's `config/classification.yaml`
may contain additional sections (vectorizer / classifier hyperparameters).
This loader only extracts the rule-related sections and normalizes them into
a predictable structure suitable for the rule-based scorer.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator, ConfigDict


# ----------------------------
# Data models
# ----------------------------
class CETKeywords(BaseModel):
    """Keyword buckets for a single CET area."""

    core: list[str] = Field(default_factory=list)
    related: list[str] = Field(default_factory=list)
    negative: list[str] = Field(default_factory=list)


class ContextRule(BaseModel):
    """A single context rule: required keywords and boost points."""

    required_keywords: list[str]
    boost: int


class ClassificationRules(BaseModel):
    """
    Structured, validated view of classification rules.

    Only the rule-related keys are required here. The loader will ignore
    unrelated keys present in the YAML file.
    """

    model_config = ConfigDict(extra="allow")

    version: str | None = None
    agency_priors: dict[str, dict[str, int]] = Field(default_factory=dict)
    branch_priors: dict[str, dict[str, int]] = Field(default_factory=dict)
    cet_keywords: dict[str, CETKeywords] = Field(default_factory=dict)
    context_rules: dict[str, list[ContextRule]] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_inputs(cls, values: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize raw YAML structure into the expected shapes:
        - Ensure `cet_keywords` is a mapping from cet_id -> {core, related, negative}
        - Ensure `context_rules` converts list-pairs into ContextRule instances
        """
        # Normalize cet_keywords if present
        raw_cet = values.get("cet_keywords") or values.get("cet_keyword") or {}
        normalized_cet: dict[str, dict[str, list[str]]] = {}
        if isinstance(raw_cet, dict):
            for cet_id, buckets in raw_cet.items():
                if not isinstance(buckets, dict):
                    # unexpected shape: coerce to empty buckets
                    normalized_cet[cet_id] = {"core": [], "related": [], "negative": []}
                    continue
                normalized_cet[cet_id] = {
                    "core": buckets.get("core") or [],
                    "related": buckets.get("related") or [],
                    "negative": buckets.get("negative") or [],
                }
        values["cet_keywords"] = normalized_cet

        # Normalize context_rules
        raw_context = values.get("context_rules") or {}
        normalized_ctx: dict[str, list[dict[str, Any]]] = {}
        if isinstance(raw_context, dict):
            for cet_id, rules in raw_context.items():
                normalized_list: list[dict[str, Any]] = []
                if not rules:
                    normalized_ctx[cet_id] = []
                    continue
                # Each rule in YAML is expected to be a 2-element list: [ [kw1, kw2], boost ]
                for rule in rules:
                    if isinstance(rule, list | tuple) and len(rule) >= 2:
                        req = rule[0]
                        boost = rule[1]
                        # Ensure required keywords is a list of strings
                        if isinstance(req, str):
                            req_list = [req]
                        elif isinstance(req, list | tuple):
                            req_list = [str(x) for x in req]
                        else:
                            req_list = []
                        try:
                            boost_int = int(boost)
                        except Exception:
                            boost_int = 0
                        normalized_list.append({"required_keywords": req_list, "boost": boost_int})
                    elif isinstance(rule, dict) and "required_keywords" in rule and "boost" in rule:
                        # already shaped
                        normalized_list.append(
                            {
                                "required_keywords": list(rule["required_keywords"]),
                                "boost": int(rule["boost"]),
                            }
                        )
                    else:
                        # Unknown shape, skip
                        continue
                normalized_ctx[cet_id] = normalized_list
        values["context_rules"] = normalized_ctx

        # Agency/branch priors: ensure integer values
        for priorkey in ("agency_priors", "branch_priors"):
            raw = values.get(priorkey) or {}
            norm: dict[str, dict[str, int]] = {}
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if isinstance(v, dict):
                        norm_inner: dict[str, int] = {}
                        for cet_k, cet_v in v.items():
                            try:
                                norm_inner[str(cet_k)] = int(cet_v)
                            except Exception:
                                # if non-int, ignore / treat as zero
                                continue
                        norm[str(k)] = norm_inner
            values[priorkey] = norm

        return values


# ----------------------------
# Loader
# ----------------------------
def load_classification_rules(path: Path | None = None) -> ClassificationRules:
    """
    Load and validate classification rule configuration.

    Args:
        path: explicit path to a classification YAML file. If None, the default
              config path is resolved from SBIR_CONFIG_DIR (if set), otherwise
              <repo-root>/config/classification.yaml

    Returns:
        ClassificationRules object with normalized priors, keywords and rules.
    """
    # For backward compatibility, if a specific path is provided, use direct loading
    if path is not None:
        resolved_path = Path(path).resolve()

        # Cache results per resolved path to allow multiple configs in one process
        cache = getattr(load_classification_rules, "_cache", {})
        key = str(resolved_path)
        if key in cache:
            return cache[key]

        if not resolved_path.exists():
            raise FileNotFoundError(f"Classification config not found at: {resolved_path}")

        with resolved_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

        # Build a payload containing only the keys we care about. This avoids errors
        # when the YAML file contains many unrelated sections.
        payload: dict[str, Any] = {
            "version": data.get("version"),
            "agency_priors": data.get("agency_priors", {}),
            "branch_priors": data.get("branch_priors", {}),
            "cet_keywords": data.get("cet_keywords", {}),
            "context_rules": data.get("context_rules", {}),
        }

        rules = ClassificationRules(**payload)
        cache[key] = rules
        setattr(load_classification_rules, "_cache", cache)
        return rules
    
    # Use centralized configuration manager for default loading
    from .configuration_manager import get_config_manager
    config_manager = get_config_manager()
    return config_manager.get_classification_rules()


# ----------------------------
# Convenience helpers
# ----------------------------
def get_cet_keywords_map(path: Path | None = None) -> dict[str, CETKeywords]:
    """
    Return the CET keyword mapping as a dictionary of CET id -> CETKeywords model.
    """
    rules = load_classification_rules(path=path)
    return rules.cet_keywords


def get_agency_priors(path: Path | None = None) -> dict[str, dict[str, int]]:
    """Return agency priors mapping."""
    return load_classification_rules(path=path).agency_priors


def get_branch_priors(path: Path | None = None) -> dict[str, dict[str, int]]:
    """Return branch priors mapping."""
    return load_classification_rules(path=path).branch_priors


def get_context_rules(path: Path | None = None) -> dict[str, list[ContextRule]]:
    """Return context rules mapping."""
    return load_classification_rules(path=path).context_rules


__all__ = [
    "CETKeywords",
    "ClassificationRules",
    "ContextRule",
    "get_agency_priors",
    "get_branch_priors",
    "get_cet_keywords_map",
    "get_context_rules",
    "load_classification_rules",
]
