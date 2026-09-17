"""Phase 4 scoring test helpers (new file, prior phases untouched)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def fake_result(
    signal_id: str,
    flagged: bool = True,
    score: float = 1.0,
    severity: str = "HIGH",
    insufficient: bool = False,
    sample_size: int = 10,
) -> SimpleNamespace:
    """Build a minimal SignalResult stand-in."""
    return SimpleNamespace(
        finding_id=f"f-{signal_id}",
        entity_id="cse_probe",
        signal_id=signal_id,
        value=score,
        threshold=0.5,
        score=score,
        severity=severity,
        confidence="MEDIUM",
        sample_size=sample_size,
        window_start="2024-05-02",
        window_end="2024-06-01",
        is_flagged=flagged,
        contributing_rows_ref=[],
        insufficient_data=insufficient,
        cohort_too_small=False,
        metadata={},
    )


def fake_bundle(alert_ids: list[str], case_ids: list[str]) -> SimpleNamespace:
    """Build a minimal EvidenceBundle stand-in."""
    rows = [{"alert_id": a, "case_id": c} for a, c in zip(alert_ids, case_ids)]
    return SimpleNamespace(
        finding_id="f",
        supporting_rows=rows,
        counter_rows=[{"alert_id": "other"}],
        counter_none_reason="",
        cohort_comparison={},
        evidence_id="e" * 8,
    )


def corpus_inputs(entity_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, float]]:
    """Load real frames, results and features for an entity."""
    from satsa.signals.runner import build_all_features, load_entity, run_entity

    features = build_all_features()
    frames = load_entity(entity_id)
    results = run_entity(entity_id, features)
    return frames, results, features[entity_id]
