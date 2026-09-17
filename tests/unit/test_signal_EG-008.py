"""Unit tests for EG-008 after-hours closure rush."""

from __future__ import annotations

import pandas as pd
from satsa.signals.execution_gaps import EG008AfterHoursClosure

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Six closures, five deep at night."""
    closes = [23, 1, 2, 3, 0, 12]
    cases = pd.DataFrame(
        [
            {
                "case_id": f"c{i}",
                "severity_norm": "HIGH",
                "status": "CLOSED",
                "open_ts": pd.Timestamp("2024-05-10 08:00", tz="UTC"),
                "close_ts": pd.Timestamp(f"2024-05-10 {h:02d}:30", tz="UTC"),
                "reopen_count": 0,
                "alert_ids": [],
            }
            for i, h in enumerate(closes)
        ]
    )
    return {"cases": cases}


def test_trigger_fires_on_planted_scenario() -> None:
    """Night-rush fixture: flagged with row evidence."""
    signal = EG008AfterHoursClosure()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire EG-008."""
    frames = corpus_frames("cse_alpha")
    result = EG008AfterHoursClosure().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = EG008AfterHoursClosure()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
