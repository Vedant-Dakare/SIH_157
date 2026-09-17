"""Unit tests for NS-011 absence of out-of-hours activity."""

from __future__ import annotations

from satsa.signals.negative_space import NS011NoAfterHours

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def test_trigger_fires_on_planted_scenario() -> None:
    """S7 (cse_golf) closes everything in daylight: flagged as observation."""
    frames = corpus_frames("cse_golf")
    signal = NS011NoAfterHours()
    result = signal.compute(make_ctx("cse_golf", frames))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert result.confidence == "LOW"
    assert_evidence(signal, result)


def test_low_confidence_and_peer_context() -> None:
    """NS-011 always carries LOW confidence with peer comparison."""
    frames = corpus_frames("cse_golf")
    signal = NS011NoAfterHours()
    result = signal.compute(make_ctx("cse_golf", frames))
    bundle = signal.evidence(result)
    assert result.confidence == "LOW"
    assert "peer_median_night_fraction" in bundle.cohort_comparison


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire NS-011."""
    frames = corpus_frames("cse_alpha")
    result = NS011NoAfterHours().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = NS011NoAfterHours()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
