"""Unit tests for EG-014 escalation to nowhere."""

from __future__ import annotations

from satsa.signals.execution_gaps import EG014EscalationNowhere

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def test_trigger_fires_on_planted_scenario() -> None:
    """S9-corpus pattern (cse_india) carries orphaned escalations: flagged."""
    frames = corpus_frames("cse_india")
    signal = EG014EscalationNowhere()
    result = signal.compute(make_ctx("cse_india", frames))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire EG-014."""
    frames = corpus_frames("cse_alpha")
    result = EG014EscalationNowhere().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = EG014EscalationNowhere()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
