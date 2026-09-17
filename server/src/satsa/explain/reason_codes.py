"""Pydantic reason codes plus zero-LLM plain-language rendering."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field


class ReasonCode(BaseModel):
    """Supervisor-level explanation of one finding."""

    code: str = Field(min_length=1)
    label: str = Field(min_length=1)
    observed: float | str = 0.0
    threshold: float | str = 0.0
    comparator: str = Field(default=">=")
    peer_baseline: dict[str, Any] = Field(default_factory=dict)
    window: str = ""
    severity: str = "INFO"
    confidence: str = "LOW"
    plain_language: str = ""


class CompositeReasonCode(ReasonCode):
    """Reason code for a composite finding with an expandable expression tree."""

    code: str = Field(min_length=1)
    expression: str = ""
    expression_tree: dict[str, Any] = Field(default_factory=dict)
    leaf_codes: list[ReasonCode] = Field(default_factory=list)


def _peer_baseline(result: Any, bundle: Any) -> dict[str, Any]:
    """Build {median, p95, n, cohort_id} best-effort from evidence metadata."""
    comparison = dict(getattr(bundle, "cohort_comparison", {}) or {})
    metadata = dict(getattr(result, "metadata", {}) or {})
    merged = dict(metadata)
    merged.update(comparison)
    median = merged.get(
        "peer_median", merged.get("median", merged.get("peer_median_night_fraction"))
    )
    p95 = merged.get("p95", merged.get("peer_p95"))
    try:
        median_f = float(median) if median is not None else 0.0
    except (TypeError, ValueError):
        median_f = 0.0
    try:
        p95_f = float(p95) if p95 is not None else 0.0
    except (TypeError, ValueError):
        p95_f = 0.0
    n = merged.get("cohort_n", merged.get("n", getattr(result, "sample_size", 0)))
    try:
        n_i = int(n)
    except (TypeError, ValueError):
        n_i = 0
    cohort_id = str(merged.get("cohort_id", merged.get("cohort", "unknown")))
    return {"median": median_f, "p95": p95_f, "n": n_i, "cohort_id": cohort_id}


def _plain_sentence(code: str, label: str, observed: Any, threshold: Any, severity: str) -> str:
    """One non-technical sentence describing the finding."""
    return (
        f"Signal {code} ({label}) was observed at {observed} against an "
        f"expected bound of {threshold} with {severity} severity; "
        "a supervisor should review the cited evidence rows."
    )


def from_result(
    result: Any,
    signal_name: str = "",
    bundle: Any | None = None,
    comparator: str = ">=",
) -> ReasonCode:
    """Build a ReasonCode from a SignalResult plus optional evidence bundle."""
    observed = getattr(result, "value", 0.0)
    threshold = getattr(result, "threshold", 0.0)
    code = str(getattr(result, "signal_id", "UNKNOWN"))
    label = signal_name or code
    severity = str(getattr(result, "severity", "INFO"))
    window = f"{getattr(result, 'window_start', '')}..{getattr(result, 'window_end', '')}"
    observed_v = observed if isinstance(observed, int | float | str) else 0.0
    threshold_v = threshold if isinstance(threshold, int | float | str) else 0.0
    baseline = (
        _peer_baseline(result, bundle)
        if bundle is not None
        else {"median": 0.0, "p95": 0.0, "n": 0, "cohort_id": "unknown"}
    )
    return ReasonCode(
        code=code,
        label=label,
        observed=observed_v,
        threshold=threshold_v,
        comparator=comparator,
        peer_baseline=baseline,
        window=window,
        severity=severity,
        confidence=str(getattr(result, "confidence", "LOW")),
        plain_language=_plain_sentence(code, label, observed, threshold, severity),
    )


def from_composite(
    comp_id: str,
    comp_name: str,
    member_results: dict[str, Any],
    signal_names: dict[str, str] | None = None,
    window: str = "",
) -> CompositeReasonCode:
    """Build a CompositeReasonCode with one expandable leaf per member signal."""
    from satsa.signals.composite import DEFAULT_COMPOSITES

    names = signal_names or {}
    definition = DEFAULT_COMPOSITES.get(comp_id, {})
    leaves = [
        from_result(res, names.get(sid, sid), comparator=">=")
        for sid, res in member_results.items()
    ]
    order = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    severities = [leaf.severity for leaf in leaves]
    top = max(severities, key=lambda s: order.get(s, 0)) if severities else "INFO"
    return CompositeReasonCode(
        code=comp_id,
        label=comp_name or comp_id,
        observed=len([r for r in member_results.values() if bool(getattr(r, "is_flagged", False))]),
        threshold=len(member_results),
        comparator=">=",
        peer_baseline={"median": 0.0, "p95": 0.0, "n": 0, "cohort_id": "unknown"},
        window=window,
        severity=top,
        confidence="MEDIUM",
        plain_language=(
            f"Composite {comp_id} ({comp_name}) combines {len(leaves)} member signals; "
            "each member below can be expanded to its full reason code."
        ),
        expression=str(definition.get("render", comp_id)),
        expression_tree=json.loads(json.dumps(definition.get("tree", {}))),
        leaf_codes=leaves,
    )


def render_plain(code: ReasonCode) -> str:
    """Render a complete report-ready paragraph (template only, zero LLM)."""
    lines = [
        f"Finding {code.code} — {code.label}.",
        code.plain_language,
        f"Observed {code.observed} versus threshold {code.threshold} "
        f"(comparator {code.comparator}) in window {code.window}; "
        f"severity {code.severity}, confidence {code.confidence}.",
    ]
    baseline = code.peer_baseline or {}
    lines.append(
        f"Peer baseline: median {baseline.get('median', 0.0)}, "
        f"p95 {baseline.get('p95', 0.0)}, n={baseline.get('n', 0)} "
        f"(cohort {baseline.get('cohort_id', 'unknown')})."
    )
    if isinstance(code, CompositeReasonCode):
        lines.append(f"Logic: {code.expression}.")
        for leaf in code.leaf_codes:
            lines.append(f"  - {leaf.code}: {leaf.plain_language}")
    return "\n".join(line for line in lines if line.strip())
