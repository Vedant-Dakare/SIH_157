"""Unit tests for NS-009 telemetry gap spike."""

from __future__ import annotations

from satsa.signals.negative_space import NS009TelemetryGapSpike

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def test_trigger_fires_on_planted_scenario() -> None:
    """S3 (cse_charlie) spikes critical telemetry gaps: flagged with evidence."""
    frames = corpus_frames("cse_charlie")
    signal = NS009TelemetryGapSpike()
    result = signal.compute(make_ctx("cse_charlie", frames))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire NS-009."""
    frames = corpus_frames("cse_alpha")
    result = NS009TelemetryGapSpike().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = NS009TelemetryGapSpike()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
