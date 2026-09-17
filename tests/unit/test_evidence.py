"""Phase 5 evidence tests (new file, prior phases untouched)."""

from __future__ import annotations

from pathlib import Path

import pytest


def _bravo_finding() -> tuple[str, str, object]:
    """Real flagged EG-001 finding with bundle from the S2 corpus."""
    from satsa.signals.registry import get_signal
    from satsa.signals.runner import build_all_features, run_entity

    features = build_all_features()
    results = run_entity("cse_bravo", features)
    result = results["EG-001"]
    assert result.is_flagged
    signal = get_signal("EG-001")
    assert signal is not None
    return result.finding_id, "2024-05-03..2024-05-31", signal.evidence(result)


def test_bundle_has_supporting_rows(tmp_path: Path) -> None:
    """Retrieved evidence carries at least one supporting row."""
    from satsa.explain.evidence import _connect, materialize, retrieve_evidence

    finding_id, window, bundle = _bravo_finding()
    conn = _connect(tmp_path / "ev.duckdb")
    try:
        materialize(finding_id, "EG-001", "cse_bravo", window, bundle, conn)
        stored = retrieve_evidence(finding_id, conn)
    finally:
        conn.close()
    assert len(stored.supporting_rows) >= 1
    assert stored.evidence_id


def test_counter_present_or_reason(tmp_path: Path) -> None:
    """Counter-evidence always present or explicitly excused."""
    from satsa.explain.evidence import _connect, materialize, retrieve_evidence

    finding_id, window, bundle = _bravo_finding()
    conn = _connect(tmp_path / "ev.duckdb")
    try:
        materialize(finding_id, "EG-001", "cse_bravo", window, bundle, conn)
        stored = retrieve_evidence(finding_id, conn)
    finally:
        conn.close()
    assert stored.counter_rows or isinstance(stored.counter_rows_absent_reason, str)
    if not stored.counter_rows:
        assert stored.counter_rows_absent_reason.strip()


def test_evidence_id_stable(tmp_path: Path) -> None:
    """Same inputs always reproduce the same evidence hash."""
    from satsa.explain.evidence import (
        _connect,
        materialize,
        stable_evidence_id,
    )

    finding_id, window, bundle = _bravo_finding()
    conn = _connect(tmp_path / "ev.duckdb")
    try:
        first = materialize(finding_id, "EG-001", "cse_bravo", window, bundle, conn)
        second = materialize(finding_id, "EG-001", "cse_bravo", window, bundle, conn)
    finally:
        conn.close()
    assert first.evidence_id == second.evidence_id
    recomputed = stable_evidence_id("EG-001", "cse_bravo", window, first.supporting_rows)
    assert recomputed == first.evidence_id


def test_unknown_finding_is_explicit_error(tmp_path: Path) -> None:
    """Unknown finding ids raise KeyError, never an obscure crash."""
    from satsa.explain.evidence import _connect, retrieve_evidence

    conn = _connect(tmp_path / "ev.duckdb")
    try:
        with pytest.raises(KeyError, match="finding not found"):
            retrieve_evidence("no-such-finding", conn)
    finally:
        conn.close()
