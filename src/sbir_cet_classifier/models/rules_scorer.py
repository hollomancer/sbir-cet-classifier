"""Rule-based CET scorer using priors, keywords, and context rules.

This scorer consumes the configuration loaded from `config/classification.yaml`
via the helper in `sbir_cet_classifier.common.classification_config` and
produces per-CET scores on a 0-100 scale.

Scoring model (additive, then clamped to [0, 100]):
- Agency priors: +boosts configured for an agency, and optional `_all_cets` baseline
- Branch priors: +boosts configured for a branch/sub-agency
- Keyword signals per CET (unique phrase presence, not raw counts):
  - core matches: +CORE_HIT_POINTS per unique match, up to CORE_HIT_CAP matches
  - related matches: +RELATED_HIT_POINTS per unique match, up to RELATED_HIT_CAP matches
  - negative matches: -NEGATIVE_HIT_PENALTY per unique match, up to NEGATIVE_HIT_CAP matches
- Context rules: +boost when all required keywords for a rule are present

Notes:
- Keyword matching is simple case-insensitive substring presence for robustness.
- Priors and context boosts are taken verbatim from config (integers).
- Final per-CET scores are clamped to [0, 100].

Example:
    >>> scorer = RuleBasedScorer()
    >>> text = "This project develops quantum algorithms on a new quantum processor."
    >>> scores = scorer.score_text(text, agency="Department of Energy", branch=None)
    >>> scores.get("quantum_computing", 0) > 0
    True
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from sbir_cet_classifier.common.classification_config import (
    CETKeywords,
    ClassificationRules,
    ContextRule,
    get_agency_priors,
    get_branch_priors,
    get_cet_keywords_map,
    get_context_rules,
    load_classification_rules,
)


class RuleBasedScorer:
    """Compute rule-based CET scores using priors, keywords, and context rules."""

    # Keyword contribution parameters (tunable, conservative defaults)
    CORE_HIT_POINTS: float = 6.0
    RELATED_HIT_POINTS: float = 3.0
    NEGATIVE_HIT_PENALTY: float = 8.0

    CORE_HIT_CAP: int = 5
    RELATED_HIT_CAP: int = 5
    NEGATIVE_HIT_CAP: int = 3

    def __init__(self, rules: Optional[ClassificationRules] = None) -> None:
        """Initialize scorer with classification rules.

        Args:
            rules: Optional pre-loaded ClassificationRules. If None, loads from default YAML.
        """
        self._rules: ClassificationRules = rules or load_classification_rules()

        # Extract and cache structures for fast lookups
        self._cet_keywords: Dict[str, CETKeywords] = get_cet_keywords_map()
        self._agency_priors: Dict[str, Dict[str, int]] = get_agency_priors()
        self._branch_priors: Dict[str, Dict[str, int]] = get_branch_priors()
        self._context_rules: Dict[str, List[ContextRule]] = get_context_rules()

        # Build maps for case-insensitive agency/branch lookup
        self._agency_key_map: Dict[str, str] = self._build_case_insensitive_key_map(
            self._agency_priors.keys()
        )
        self._branch_key_map: Dict[str, str] = self._build_case_insensitive_key_map(
            self._branch_priors.keys()
        )

        # Precompute the set of CET ids we will score
        cet_ids_from_keywords = set(self._cet_keywords.keys())
        cet_ids_from_agency = {
            cet
            for mapping in self._agency_priors.values()
            for cet in mapping.keys()
            if cet != "_all_cets"
        }
        cet_ids_from_branch = {
            cet
            for mapping in self._branch_priors.values()
            for cet in mapping.keys()
            if cet != "_all_cets"
        }
        cet_ids_from_context = set(self._context_rules.keys())
        self._all_cet_ids: List[str] = sorted(
            cet_ids_from_keywords | cet_ids_from_agency | cet_ids_from_branch | cet_ids_from_context
        )

    @staticmethod
    def _build_case_insensitive_key_map(keys: Iterable[str]) -> Dict[str, str]:
        """Build a mapping from lowercase key -> original key for case-insensitive lookup."""
        m: Dict[str, str] = {}
        for k in keys:
            lk = k.lower()
            # If collisions occur (different originals with same lowercase), prefer first seen
            if lk not in m:
                m[lk] = k
        return m

    @staticmethod
    def _present(text_lower: str, phrase: str) -> bool:
        """Case-insensitive substring presence check."""
        p = phrase.strip().lower()
        if not p:
            return False
        return p in text_lower

    def _resolve_agency_key(self, agency: Optional[str]) -> Optional[str]:
        if not agency:
            return None
        exact = self._agency_priors.get(agency)
        if exact is not None:
            return agency
        return self._agency_key_map.get(agency.lower())

    def _resolve_branch_key(self, branch: Optional[str]) -> Optional[str]:
        if not branch:
            return None
        exact = self._branch_priors.get(branch)
        if exact is not None:
            return branch
        return self._branch_key_map.get(branch.lower())

    def _apply_priors(
        self,
        cet_id: str,
        *,
        agency_key: Optional[str],
        branch_key: Optional[str],
    ) -> float:
        """Return the total prior boost for a CET from agency and branch."""
        total = 0.0

        if agency_key:
            amap = self._agency_priors.get(agency_key, {})
            total += float(amap.get("_all_cets", 0))
            total += float(amap.get(cet_id, 0))

        if branch_key:
            bmap = self._branch_priors.get(branch_key, {})
            total += float(bmap.get("_all_cets", 0))
            total += float(bmap.get(cet_id, 0))

        return total

    def _keyword_contribution(self, cet_id: str, text_lower: str) -> float:
        """Compute keyword-based contribution for a CET."""
        kw = self._cet_keywords.get(cet_id)
        if kw is None:
            return 0.0

        # Unique matches only; simple presence (not counting repeats)
        core_hits = sum(1 for term in (kw.core or []) if self._present(text_lower, term))
        related_hits = sum(1 for term in (kw.related or []) if self._present(text_lower, term))
        negative_hits = sum(1 for term in (kw.negative or []) if self._present(text_lower, term))

        core_hits = min(core_hits, self.CORE_HIT_CAP)
        related_hits = min(related_hits, self.RELATED_HIT_CAP)
        negative_hits = min(negative_hits, self.NEGATIVE_HIT_CAP)

        score = (
            core_hits * self.CORE_HIT_POINTS
            + related_hits * self.RELATED_HIT_POINTS
            - negative_hits * self.NEGATIVE_HIT_PENALTY
        )
        return float(score)

    def _context_contribution(self, cet_id: str, text_lower: str) -> float:
        """Compute boost from context rules when all required keywords are present."""
        rules = self._context_rules.get(cet_id) or []
        total = 0.0
        for rule in rules:
            req = getattr(rule, "required_keywords", []) or []
            if not req:
                continue
            if all(self._present(text_lower, r) for r in req):
                try:
                    total += float(getattr(rule, "boost", 0))
                except Exception:
                    continue
        return total

    def score_text(
        self,
        text: str,
        *,
        agency: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> Dict[str, float]:
        """Score a text for all CETs using rules; returns per-CET scores in [0, 100].

        Args:
            text: Input text to score (abstract, description, etc.)
            agency: Optional agency name (e.g., "Department of Defense")
            branch: Optional sub-agency/branch (e.g., "Air Force")

        Returns:
            Mapping of cet_id -> score (float in 0..100)
        """
        if not text:
            # Still apply pure priors if provided, otherwise zeros
            text_lower = ""
        else:
            text_lower = " ".join(text.lower().split())

        agency_key = self._resolve_agency_key(agency)
        branch_key = self._resolve_branch_key(branch)

        scores: Dict[str, float] = {}

        for cet_id in self._all_cet_ids:
            total = 0.0
            total += self._apply_priors(cet_id, agency_key=agency_key, branch_key=branch_key)
            total += self._keyword_contribution(cet_id, text_lower)
            total += self._context_contribution(cet_id, text_lower)

            # Clamp to [0, 100]
            if total < 0.0:
                total = 0.0
            elif total > 100.0:
                total = 100.0
            scores[cet_id] = float(total)

        return scores

    def score_and_rank_top(
        self,
        text: str,
        *,
        agency: Optional[str] = None,
        branch: Optional[str] = None,
        top_n: int = 3,
    ) -> List[Tuple[str, float]]:
        """Return top-N CETs with highest rule-based scores.

        Args:
            text: Input text to score
            agency: Optional agency name
            branch: Optional branch name
            top_n: Number of top CETs to return

        Returns:
            List of (cet_id, score) sorted descending
        """
        all_scores = self.score_text(text, agency=agency, branch=branch)
        ranked = sorted(all_scores.items(), key=lambda kv: kv[1], reverse=True)
        return ranked[: max(0, int(top_n))]


__all__ = ["RuleBasedScorer"]
