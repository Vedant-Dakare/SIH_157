"""Unit tests for NS-005 expected core source absent."""

from __future__ import annotations

from satsa.signals.negative_space import NS005ExpectedSourceAbsent

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def test_trigger_fires_on_planted_scenario() -> None:
    """S3 (cse_charlie) misses expected sources: flagged with row evidence."""
    frames = corpus_frames("cse_charlie")
    signal = NS005ExpectedSourceAbsent()
    result = signal.compute(make_ctx("cse_charlie", frames))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire NS-005."""
    frames = corpus_frames("cse_alpha")
    result = NS005ExpectedSourceAbsent().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = NS005ExpectedSourceAbsent()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
