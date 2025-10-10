"""Gap analytics utilities supporting CET drill-down flows."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sbir_cet_classifier.common.serialization import SerializableDataclass


@dataclass(frozen=True)
class GapInsight(SerializableDataclass):
    metric: str
    current_value: float
    target_value: float
    narrative: str

    def as_dict(self) -> dict:
        """Override to apply custom rounding for float values."""
        result = super().as_dict()
        result["currentValue"] = round(self.current_value, 2)
        result["targetValue"] = round(self.target_value, 2)
        return result


class GapAnalytics:
    """Generates gap narratives comparing current coverage against targets."""

    def __init__(self, target_shares: Mapping[str, float] | None = None, *, default_target: float = 0.5) -> None:
        self._target_shares = target_shares or {}
        self._default_target = default_target

    def share_gap(
        self,
        *,
        cet_id: str,
        share_percent: float,
    ) -> GapInsight:
        target_ratio = self._target_shares.get(cet_id, self._default_target)
        target_percent = target_ratio * 100
        diff = share_percent - target_percent
        if diff >= 0:
            narrative = (
                f"{cet_id.replace('_', ' ').title()} coverage meets the {target_percent:.0f}% target "
                f"by {diff:.2f} percentage points."
            )
        else:
            narrative = (
                f"{cet_id.replace('_', ' ').title()} coverage trails the {target_percent:.0f}% target "
                f"by {abs(diff):.2f} percentage points for the selected filters."
            )
        return GapInsight(
            metric="share_vs_target",
            current_value=share_percent,
            target_value=target_percent,
            narrative=narrative,
        )

    def manual_review_gap(self, *, cet_id: str, pending_reviews: int) -> GapInsight | None:
        if pending_reviews <= 0:
            return None
        narrative = (
            f"{pending_reviews} award{'s' if pending_reviews != 1 else ''} in {cet_id.replace('_', ' ').title()} "
            "require manual review before the area can be marked complete."
        )
        return GapInsight(
            metric="pending_manual_reviews",
            current_value=float(pending_reviews),
            target_value=0.0,
            narrative=narrative,
        )


__all__ = ["GapAnalytics", "GapInsight"]
