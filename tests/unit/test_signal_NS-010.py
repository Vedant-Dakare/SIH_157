"""Unit tests for NS-010 silent critical estate."""

from __future__ import annotations

import pandas as pd
from satsa.signals.negative_space import NS010SilentCriticalEstate

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Five critical assets, four never alerting."""
    assets = pd.DataFrame(
        [
            {
                "asset_id": f"asset{i}",
                "criticality": "high",
                "environment": "production",
                "os_family": "linux",
                "internet_facing": False,
            }
            for i in range(5)
        ]
    )
    alerts = pd.DataFrame(
        [
            {
                "alert_id": "a0",
                "asset_id": "asset0",
                "detected_ts": pd.Timestamp("2024-05-10 12:00", tz="UTC"),
            }
        ]
    )
    return {"assets": assets, "alerts": alerts}


def test_trigger_fires_on_planted_scenario() -> None:
    """Silent-estate fixture: flagged with row evidence."""
    signal = NS010SilentCriticalEstate()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire NS-010."""
    frames = corpus_frames("cse_alpha")
    result = NS010SilentCriticalEstate().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = NS010SilentCriticalEstate()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
