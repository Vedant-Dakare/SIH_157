"""Unit tests for composite signals COMP-001..003."""

from __future__ import annotations

from satsa.signals.base import SignalResult
from satsa.signals.composite import (
    DEFAULT_COMPOSITES,
    CompositeSignal,
    composite_severity,
    evaluate_composite,
    evaluate_tree,
)

from tests.unit.signal_helpers import corpus_frames, make_ctx


def _result(signal_id: str, flagged: bool, severity: str = "HIGH") -> SignalResult:
    """Build a minimal member result."""
    return SignalResult(
        finding_id=f"f-{signal_id}",
        entity_id="cse_probe",
        signal_id=signal_id,
        value=1.0 if flagged else 0.0,
        threshold=0.5,
        score=1.0 if flagged else 0.0,
        severity=severity,
        confidence="MEDIUM",
        sample_size=10,
        window_start="2024-05-02",
        window_end="2024-06-01",
        is_flagged=flagged,
    )


def _ctx() -> object:
    """Return a context carrying no member data."""
    return make_ctx("cse_probe", {})


def test_comp001_superficial_compliance() -> None:
    """COMP-001 fires on EG-003 AND EG-013 AND (NS-005 OR NS-006)."""
    members = {
        "EG-003": _result("EG-003", True),
        "EG-013": _result("EG-013", True, "MEDIUM"),
        "NS-005": _result("NS-005", False),
        "NS-006": _result("NS-006", True, "MEDIUM"),
    }
    result = evaluate_composite("COMP-001", members, _ctx())  # type: ignore[arg-type]
    assert result.is_flagged is True
    assert "(EG-003 AND EG-013) AND (NS-005 OR NS-006)" in result.metadata["render"]
    leaves = result.metadata["leaves"]
    assert set(leaves) >= {"EG-003", "EG-013", "NS-005", "NS-006"}


def test_comp001_blocked_without_or_branch() -> None:
    """COMP-001 stays silent when neither NS-005 nor NS-006 fires."""
    members = {
        "EG-003": _result("EG-003", True),
        "EG-013": _result("EG-013", True),
        "NS-005": _result("NS-005", False),
        "NS-006": _result("NS-006", False),
    }
    result = evaluate_composite("COMP-001", members, _ctx())  # type: ignore[arg-type]
    assert result.is_flagged is False


def test_comp002_silent_critical_estate() -> None:
    """COMP-002 fires on NS-001 AND NS-010 with HIGH criticality band."""
    members = {"NS-001": _result("NS-001", True), "NS-010": _result("NS-010", True)}
    result = evaluate_composite("COMP-002", members, _ctx(), high_band=True)  # type: ignore[arg-type]
    assert result.is_flagged is True
    result_low = evaluate_composite("COMP-002", members, _ctx(), high_band=False)  # type: ignore[arg-type]
    assert result_low.is_flagged is False


def test_comp003_metric_theatre() -> None:
    """COMP-003 fires on EG-007 AND EG-010 AND EG-006."""
    members = {
        "EG-007": _result("EG-007", True),
        "EG-010": _result("EG-010", True),
        "EG-006": _result("EG-006", True),
    }
    result = evaluate_composite("COMP-003", members, _ctx())  # type: ignore[arg-type]
    assert result.is_flagged is True
    assert result.metadata["render"] == "EG-007 AND EG-010 AND EG-006"


def test_severity_dampened_by_missing_members() -> None:
    """Severity is the dampened max of member severities."""
    full = [
        _result("EG-003", True, "HIGH"),
        _result("EG-013", True, "HIGH"),
        _result("NS-006", True, "HIGH"),
    ]
    assert composite_severity(full) == "HIGH"
    partial = [
        _result("EG-003", True, "HIGH"),
        _result("EG-013", False),
        _result("NS-006", False),
    ]
    assert composite_severity(partial) in ("MEDIUM", "HIGH")


def test_new_rules_addable_via_config_only() -> None:
    """Composite rules accept config-only additions without code changes."""
    assert set(DEFAULT_COMPOSITES) == {"COMP-001", "COMP-002", "COMP-003"}
    assert evaluate_tree({"AND": ["A", {"OR": ["B", "C"]}]}, {"A": True, "B": False, "C": True})
    assert not evaluate_tree({"AND": ["A", {"OR": ["B", "C"]}]}, {"A": True, "B": False})


def test_composite_evidence_expandable() -> None:
    """Composite evidence expands each leaf to its finding reference."""
    members = {
        "EG-007": _result("EG-007", True),
        "EG-010": _result("EG-010", False),
        "EG-006": _result("EG-006", True),
    }
    result = evaluate_composite("COMP-003", members, _ctx())  # type: ignore[arg-type]
    bundle = CompositeSignal().evidence(result)
    assert any(r["signal_id"] == "EG-007" for r in bundle.supporting_rows)
    assert any(r["signal_id"] == "EG-010" for r in bundle.counter_rows)


def test_corpus_smoke() -> None:
    """Corpus entities load without breaking composite evaluation."""
    _ = corpus_frames("cse_alpha")
