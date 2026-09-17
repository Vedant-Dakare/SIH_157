"""Phase 7 expert-agreement tests (new file, prior phases untouched)."""

from __future__ import annotations

from pathlib import Path


def test_disagreements_with_evidence() -> None:
    """Disagreement lists are disjoint and every item carries evidence."""
    from satsa.validation.expert_agreement import build_disagreements

    from tests.unit.validation_helpers import get_validation_inputs

    flagged, _, labels, results = get_validation_inputs()
    sat_only, expert_only = build_disagreements(flagged, labels, results)
    sat_ids = {(d.entity_id, d.signal_id) for d in sat_only}
    expert_ids = {(d.entity_id, d.signal_id) for d in expert_only}
    assert not (sat_ids & expert_ids)
    for item in (*sat_only, *expert_only):
        assert item.evidence
        assert "supporting_rows" in item.evidence
        assert "evidence_id" in item.evidence


def test_adjudication_round_trip(tmp_path: Path) -> None:
    """Feedback records persist and read back (thresholds stay manual)."""
    from satsa.validation.expert_agreement import (
        AdjudicationFeedback,
        read_adjudications,
        record_adjudication,
    )

    target = tmp_path / "adjudications.jsonl"
    record_adjudication(
        AdjudicationFeedback(disagreement_id="d1", adjudicated_by="hash", verdict="SAT_SA_CORRECT",
                             threshold_adjustment=0.05),
        path=target,
    )
    stored = read_adjudications(target)
    assert len(stored) == 1
    assert stored[0].verdict == "SAT_SA_CORRECT"
