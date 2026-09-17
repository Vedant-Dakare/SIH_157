"""Counterfactuals: binary search for the value that would clear a flag.

Only threshold-comparator rule signals are computable. Composites,
absence (NS) findings and insufficient-data results return computable=False
with an explicit reason — never fabricated.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

NS_PREFIX = "NS-"
COMP_PREFIX = "COMP-"
_MAX_ITERATIONS = 64


class CounterfactualResult(BaseModel):
    """What would have to change for a finding to clear."""

    finding_id: str = Field(min_length=1)
    computable: bool = False
    threshold_value: float = 0.0
    required_value: float = 0.0
    metric_name: str = ""
    plain_language: str = ""
    reason_if_null: str = ""


def _fires(value: float, threshold: float, comparator: str) -> bool:
    """Firing predicate for a threshold comparator."""
    if comparator == "<=":
        return bool(value <= threshold)
    return bool(value >= threshold)


def _metric_name(result: Any) -> str:
    """Best-effort metric name from the signal's required features."""
    try:
        from satsa.signals.registry import get_signal

        signal = get_signal(str(getattr(result, "signal_id", "")))
        if signal is not None and getattr(signal, "required_features", []):
            return str(signal.required_features[0])
    except Exception:
        pass
    return "signal value"


def counterfactual_for(
    result: Any,
    comparator: str = ">=",
    peer_p25: float | None = None,
) -> CounterfactualResult:
    """Binary-search the threshold-crossing value for one finding."""
    finding_id = str(getattr(result, "finding_id", "unknown"))
    signal_id = str(getattr(result, "signal_id", ""))
    observed = float(getattr(result, "value", 0.0) or 0.0)
    threshold = float(getattr(result, "threshold", 0.0) or 0.0)
    metric = _metric_name(result)

    if bool(getattr(result, "insufficient_data", False)):
        return CounterfactualResult(
            finding_id=finding_id,
            reason_if_null="insufficient data: no stable threshold to search against",
        )
    if not bool(getattr(result, "is_flagged", False)):
        return CounterfactualResult(
            finding_id=finding_id, reason_if_null="signal is not currently firing"
        )
    if signal_id.startswith(COMP_PREFIX):
        return CounterfactualResult(
            finding_id=finding_id,
            reason_if_null="composite signals combine member flags; clear a member finding instead",
        )
    if signal_id.startswith(NS_PREFIX):
        return CounterfactualResult(
            finding_id=finding_id,
            reason_if_null="absence findings describe missing evidence and have no threshold value",
        )
    if not _fires(observed, threshold, comparator):
        return CounterfactualResult(
            finding_id=finding_id,
            reason_if_null="observed value does not currently breach the threshold",
        )
    # Bisection between a non-firing bound and the observed firing value.
    span = max(abs(observed - threshold), abs(threshold), 1.0) * 2.0
    if comparator == "<=":
        lo, hi = observed, threshold + span
    else:
        lo, hi = threshold - span, observed
    if _fires(lo, threshold, comparator):
        lo = lo - span * 8.0
    crossing = threshold
    for _ in range(_MAX_ITERATIONS):
        mid = (lo + hi) / 2.0
        if _fires(mid, threshold, comparator):
            crossing = mid
            if comparator == "<=":
                lo = mid
            else:
                hi = mid
        else:
            if comparator == "<=":
                hi = mid
            else:
                lo = mid
    epsilon = max(abs(crossing), 1.0) * 1e-6
    required = crossing - epsilon if comparator == ">=" else crossing + epsilon
    assert not _fires(required, threshold, comparator)
    peer_note = f" (cohort p25 {peer_p25})" if peer_p25 is not None else ""
    direction = "fallen to <=" if comparator == ">=" else "risen to >="
    return CounterfactualResult(
        finding_id=finding_id,
        computable=True,
        threshold_value=threshold,
        required_value=float(required),
        metric_name=metric,
        plain_language=(
            f"If {metric} had {direction} {required:.4g} instead of the observed "
            f"{observed:.4g} (threshold {threshold:.4g}){peer_note}, "
            f"{signal_id} would not fire for this entity."
        ),
        reason_if_null="",
    )
