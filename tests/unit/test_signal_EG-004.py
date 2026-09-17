"""Unit tests for EG-004 severity downgrade bias."""

from __future__ import annotations

from satsa.signals.execution_gaps import EG004SeverityDowngrade

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def test_trigger_fires_on_planted_scenario() -> None:
    """S6 (cse_foxtrot) downgrades alert severity at case level: flagged."""
    frames = corpus_frames("cse_foxtrot")
    signal = EG004SeverityDowngrade()
    result = signal.compute(make_ctx("cse_foxtrot", frames))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire EG-004."""
    frames = corpus_frames("cse_alpha")
    result = EG004SeverityDowngrade().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = EG004SeverityDowngrade()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
