"""Phase 5 reason-code tests (new file, prior phases untouched)."""

from __future__ import annotations

import json
from types import SimpleNamespace


def _fake(signal_id: str) -> SimpleNamespace:
    """Minimal flagged result for one signal id."""
    return SimpleNamespace(
        finding_id=f"f-{signal_id}",
        entity_id="cse_probe",
        signal_id=signal_id,
        value=0.9,
        threshold=0.5,
        score=0.9,
        severity="HIGH",
        confidence="MEDIUM",
        sample_size=12,
        window_start="2024-05-03",
        window_end="2024-05-31",
        is_flagged=True,
        insufficient_data=False,
        metadata={},
    )


def _leaves(tree: object, acc: set[str]) -> None:
    """Collect string leaves of a boolean expression tree."""
    if isinstance(tree, str):
        acc.add(tree)
    elif isinstance(tree, dict):
        for branch in tree.get("AND", tree.get("OR", [])):
            _leaves(branch, acc)


def test_render_plain_non_empty_for_every_signal() -> None:
    """Every registered signal type renders a report paragraph."""
    from satsa.explain.reason_codes import from_result, render_plain
    from satsa.signals.registry import get_enabled_signals

    for signal in get_enabled_signals():
        reason = from_result(_fake(signal.id), signal.name)
        text = render_plain(reason)
        assert isinstance(text, str)
        assert signal.id in text
        assert reason.peer_baseline.keys() == {"median", "p95", "n", "cohort_id"}


def test_composite_tree_valid_and_leaves_real() -> None:
    """Expression tree is JSON-serialisable; leaves are real signal ids."""
    from satsa.explain.reason_codes import from_composite, render_plain
    from satsa.signals.composite import DEFAULT_COMPOSITES
    from satsa.signals.registry import get_enabled_signals

    known = {s.id for s in get_enabled_signals()} | set(DEFAULT_COMPOSITES) | {"HIGH_BAND"}
    members = {sid: _fake(sid) for sid in ("EG-003", "EG-013", "NS-005")}
    composite = from_composite("COMP-001", "Superficial compliance", members)
    assert composite.expression
    assert json.loads(json.dumps(composite.expression_tree))
    leaves: set[str] = set()
    _leaves(composite.expression_tree, leaves)
    assert leaves
    assert leaves <= known
    assert len(composite.leaf_codes) == 3
    assert render_plain(composite).strip()
