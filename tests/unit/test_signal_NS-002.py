"""Unit tests for NS-002 telemetry silence streak."""

from __future__ import annotations

import pandas as pd
from satsa.signals.negative_space import NS002SilenceStreak

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Six assets, two with zero telemetry across the window."""
    assets = pd.DataFrame(
        [
            {
                "asset_id": f"asset{i}",
                "criticality": "high",
                "environment": "production",
                "os_family": "linux",
                "internet_facing": True,
            }
            for i in range(6)
        ]
    )
    telemetry = pd.DataFrame(
        [
            {
                "asset_id": f"asset{i}",
                "source": source,
                "observed_ts": pd.Timestamp("2024-05-20", tz="UTC"),
            }
            for i in range(4)
            for source in ("edr", "firewall", "ids", "auth")
        ]
    )
    return {"assets": assets, "telemetry": telemetry}


def test_trigger_fires_on_planted_scenario() -> None:
    """Silent-asset fixture: flagged with row evidence."""
    signal = NS002SilenceStreak()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire NS-002."""
    frames = corpus_frames("cse_alpha")
    result = NS002SilenceStreak().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = NS002SilenceStreak()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
