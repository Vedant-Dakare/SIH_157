"""Unit tests for NS-012 feed truncation."""

from __future__ import annotations

import pandas as pd
from satsa.signals.negative_space import NS012FeedTruncation

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Six current alerts against a collapsed trailing baseline."""
    alerts = pd.DataFrame(
        [
            {
                "alert_id": f"a{i}",
                "asset_id": "asset1",
                "detected_ts": pd.Timestamp("2024-05-28 12:00", tz="UTC"),
            }
            for i in range(6)
        ]
    )
    return {"alerts": alerts}


def test_trigger_fires_on_planted_scenario() -> None:
    """Truncation fixture: flagged with row evidence."""
    signal = NS012FeedTruncation()
    windows = [100.0, 100.0, 100.0, 100.0, 20.0]
    ctx = make_ctx("cse_probe", _trigger_frames(), cohort_stats={"window_counts": windows})
    result = signal.compute(ctx)
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire NS-012."""
    frames = corpus_frames("cse_alpha")
    result = NS012FeedTruncation().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = NS012FeedTruncation()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
