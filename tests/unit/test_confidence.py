"""Phase 4 confidence tests (new file, prior phases untouched)."""

from __future__ import annotations

from tests.unit.scoring_helpers import corpus_inputs


def test_low_completeness_caps_and_separates() -> None:
    """data_completeness < 0.6 caps LOW and excludes from main ranking."""
    from satsa.scoring.confidence import assess_confidence
    from satsa.scoring.risk_engine import score_all

    frames, results, features = corpus_inputs("cse_juliet")
    outcome = assess_confidence("cse_juliet", frames, results, features)
    assert outcome.level == "LOW"
    assert outcome.capped_by_completeness is True
    assert outcome.data_completeness < 0.6

    scored = score_all(run_id="t")
    main_ids = [r["entity_id"] for r in scored["ranking"]]
    queued_ids = [r["entity_id"] for r in scored["insufficient_queue"]]
    assert "cse_juliet" not in main_ids
    assert "cse_juliet" in queued_ids


def test_high_completeness_adequate_samples_is_high() -> None:
    """Healthy feed with adequate samples yields HIGH confidence."""
    from satsa.scoring.confidence import assess_confidence

    frames, results, features = corpus_inputs("cse_alpha")
    outcome = assess_confidence("cse_alpha", frames, results, features)
    assert outcome.level == "HIGH"
    assert outcome.capped_by_completeness is False
    assert outcome.data_completeness >= 0.9


def test_reason_is_human_readable() -> None:
    """Every confidence outcome carries a non-empty reason string."""
    from satsa.scoring.confidence import assess_confidence

    for entity_id in ("cse_alpha", "cse_bravo", "cse_juliet"):
        frames, results, features = corpus_inputs(entity_id)
        outcome = assess_confidence(entity_id, frames, results, features)
        assert isinstance(outcome.reason, str)
        assert len(outcome.reason.strip()) > 20
        assert outcome.level in ("HIGH", "MEDIUM", "LOW")
