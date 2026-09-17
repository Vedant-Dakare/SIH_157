"""Unit tests for EG-003 escalation bypass."""

from __future__ import annotations

from satsa.signals.execution_gaps import EG003EscalationBypass

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def test_trigger_fires_on_planted_scenario() -> None:
    """S8 (cse_hotel) bypasses escalation on CRITICAL T1: flagged with evidence."""
    frames = corpus_frames("cse_hotel")
    signal = EG003EscalationBypass()
    result = signal.compute(make_ctx("cse_hotel", frames))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire EG-003."""
    frames = corpus_frames("cse_alpha")
    result = EG003EscalationBypass().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = EG003EscalationBypass()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
