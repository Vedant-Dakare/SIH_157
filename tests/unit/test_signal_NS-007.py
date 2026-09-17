"""Unit tests for NS-007 detrended low activity."""

from __future__ import annotations

import pandas as pd
from satsa.signals.negative_space import NS007LowActivityDetrended

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Ninety days of steady volume collapsing in the final week."""
    rows = []
    idx = 0
    for day in range(90):
        volume = 1 if day >= 83 else 10
        for _ in range(volume):
            rows.append(
                {
                    "alert_id": f"a{idx}",
                    "asset_id": "asset1",
                    "detected_ts": pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=day),
                }
            )
            idx += 1
    return {"alerts": pd.DataFrame(rows)}


def test_trigger_fires_on_planted_scenario() -> None:
    """Collapse fixture: flagged after seasonal detrending."""
    signal = NS007LowActivityDetrended()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire NS-007."""
    frames = corpus_frames("cse_alpha")
    result = NS007LowActivityDetrended().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = NS007LowActivityDetrended()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
