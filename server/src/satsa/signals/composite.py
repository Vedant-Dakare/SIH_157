"""Composite signals: boolean expression trees over member SignalResults."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from satsa.signals._evidence import make_bundle
from satsa.signals.base import EvidenceBundle, Family, Signal, SignalContext, SignalResult

Operator = Literal["AND", "OR"]

DEFAULT_COMPOSITES: dict[str, dict[str, Any]] = {
    "COMP-001": {
        "name": "Superficial compliance",
        "tree": {"AND": ["EG-003", {"OR": ["NS-005", "NS-006"]}, "EG-013"]},
        "render": "(EG-003 AND EG-013) AND (NS-005 OR NS-006)",
    },
    "COMP-002": {
        "name": "Silent critical estate",
        "tree": {"AND": ["NS-001", "NS-010", "HIGH_BAND"]},
        "render": "NS-001 AND NS-010 AND asset_criticality_band=HIGH",
    },
    "COMP-003": {
        "name": "Metric theatre",
        "tree": {"AND": ["EG-007", "EG-010", "EG-006"]},
        "render": "EG-007 AND EG-010 AND EG-006",
    },
}

_SEVERITY_ORDER = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def evaluate_tree(tree: Any, fired: dict[str, bool]) -> bool:
    """Evaluate a boolean expression tree against member fired flags."""
    if isinstance(tree, str):
        if tree == "HIGH_BAND":
            return bool(fired.get("HIGH_BAND", False))
        return bool(fired.get(tree, False))
    if isinstance(tree, dict):
        if "AND" in tree:
            return all(evaluate_tree(branch, fired) for branch in tree["AND"])
        if "OR" in tree:
            return any(evaluate_tree(branch, fired) for branch in tree["OR"])
    return False


def composite_severity(members: list[SignalResult]) -> str:
    """Max member severity dampened by missing (non-fired) members."""
    if not members:
        return "LOW"
    fired = [m for m in members if m.is_flagged]
    if not fired:
        return "LOW"
    top = max(fired, key=lambda m: _SEVERITY_ORDER.get(m.severity, 0))
    dampen = len(fired) / max(1, len(members))
    order = _SEVERITY_ORDER.get(top.severity, 0)
    if dampen < 1.0:
        order = max(0, order - 1)
    for name, level in _SEVERITY_ORDER.items():
        if level == order:
            return name
    return top.severity


def _leaf_row(sid: str, leaf: dict[str, Any]) -> dict[str, Any]:
    """Render one composite leaf as an evidence row."""
    return {
        "signal_id": sid,
        "finding_id": leaf.get("finding_id", ""),
        "is_flagged": leaf.get("is_flagged", False),
    }


class CompositeSignal(Signal):
    """Config-driven composite over named member signals."""

    id = "COMP-BASE"
    name = "Composite base"
    family: ClassVar[Family] = "composite"
    required_features: ClassVar[list[str]] = []
    default_severity = "HIGH"

    comp_id: str = "COMP-BASE"
    expression: Any = {}
    render_str: str = ""

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Evaluate the expression tree over member results in ctx metadata."""
        raise NotImplementedError("Use evaluate_composite with member results")

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return leaf-expandable evidence stored during evaluation."""
        leaves = result.metadata.get("leaves", {})
        supporting = [
            _leaf_row(sid, leaf) for sid, leaf in leaves.items() if leaf.get("is_flagged")
        ]
        counter = [
            _leaf_row(sid, leaf)
            for sid, leaf in leaves.items()
            if not leaf.get("is_flagged")
        ]
        return make_bundle(self.comp_id, result, supporting, counter)


def evaluate_composite(
    comp_id: str,
    member_results: dict[str, SignalResult],
    ctx: SignalContext,
    high_band: bool = False,
) -> SignalResult:
    """Evaluate one composite rule; severity = dampened max member severity."""
    from satsa.signals.base import _finding_id

    definition = DEFAULT_COMPOSITES[comp_id]
    extra = dict(ctx.config.get("composite_rules", {}) or {})
    if comp_id in extra:
        definition = extra[comp_id]
    fired = {sid: bool(res.is_flagged) for sid, res in member_results.items()}
    fired["HIGH_BAND"] = bool(high_band)
    is_fired = evaluate_tree(definition["tree"], fired)
    members = [r for sid, r in member_results.items() if sid in str(definition["tree"])]
    severity = composite_severity(members) if is_fired else "LOW"
    weakest_conf = "LOW"
    conf_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    flagged_members = [r for r in members if r.is_flagged]
    if flagged_members:
        weakest = min(flagged_members, key=lambda r: conf_order.get(r.confidence, 0))
        weakest_conf = weakest.confidence
    leaves = {
        sid: {
            "finding_id": r.finding_id,
            "is_flagged": r.is_flagged,
            "value": r.value,
            "severity": r.severity,
        }
        for sid, r in member_results.items()
    }
    return SignalResult(
        finding_id=_finding_id(comp_id, ctx.entity_id, ctx.window_start, ctx.seed),
        entity_id=ctx.entity_id,
        signal_id=comp_id,
        value=1.0 if is_fired else 0.0,
        threshold=1.0,
        score=1.0 if is_fired else 0.0,
        severity=severity,
        confidence=weakest_conf,
        sample_size=int(sum(r.sample_size for r in members)),
        window_start=ctx.window_start,
        window_end=ctx.window_end,
        is_flagged=bool(is_fired),
        contributing_rows_ref=[r.finding_id for r in flagged_members],
        insufficient_data=False,
        metadata={"render": definition["render"], "tree": definition["tree"], "leaves": leaves},
    )
