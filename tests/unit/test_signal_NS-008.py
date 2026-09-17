"""Unit tests for NS-008 internet-facing blind spot."""

from __future__ import annotations

import pandas as pd
from satsa.signals.negative_space import NS008InternetBlindspot

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Ten assets (six internet-facing) with alerts only off-perimeter."""
    assets = pd.DataFrame(
        [
            {
                "asset_id": f"asset{i}",
                "criticality": "medium",
                "environment": "production",
                "os_family": "linux",
                "internet_facing": i < 6,
            }
            for i in range(10)
        ]
    )
    alerts = pd.DataFrame(
        [
            {
                "alert_id": f"a{i}",
                "asset_id": f"asset{i + 6}",
                "detected_ts": pd.Timestamp("2024-05-10 12:00", tz="UTC"),
            }
            for i in range(4)
        ]
    )
    return {"assets": assets, "alerts": alerts}


def test_trigger_fires_on_planted_scenario() -> None:
    """Blind-perimeter fixture: flagged with row evidence."""
    signal = NS008InternetBlindspot()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire NS-008."""
    frames = corpus_frames("cse_alpha")
    result = NS008InternetBlindspot().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = NS008InternetBlindspot()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
