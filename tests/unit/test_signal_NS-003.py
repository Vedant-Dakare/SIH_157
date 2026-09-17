"""Unit tests for NS-003 category absence vs peers."""

from __future__ import annotations

import pandas as pd
from satsa.signals.negative_space import NS003CategoryAbsence

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Six single-category alerts (six of seven taxonomy categories missing)."""
    alerts = pd.DataFrame(
        [
            {
                "alert_id": f"a{i}",
                "asset_id": "asset1",
                "category": "MALWARE",
                "detected_ts": pd.Timestamp("2024-05-10 12:00", tz="UTC"),
            }
            for i in range(6)
        ]
    )
    return {"alerts": alerts}


def _peers() -> dict[str, list[float]]:
    """Peers miss roughly two categories each."""
    return {"category_missing_count": [2.0, 2.0, 3.0, 2.0, 3.0]}


def test_trigger_fires_on_planted_scenario() -> None:
    """Narrow-category fixture: flagged against peer context."""
    signal = NS003CategoryAbsence()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames(), cohort_features=_peers()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire NS-003."""
    frames = corpus_frames("cse_alpha")
    result = NS003CategoryAbsence().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = NS003CategoryAbsence()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
