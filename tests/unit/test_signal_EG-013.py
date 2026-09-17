"""Unit tests for EG-013 suspiciously perfect SLA."""

from __future__ import annotations

import pandas as pd
from satsa.signals.execution_gaps import EG013PerfectSla

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Twelve cases with identical 24h dwells, all inside the SLA."""
    base = pd.Timestamp("2024-05-10 08:00", tz="UTC")
    cases = pd.DataFrame(
        [
            {
                "case_id": f"c{i}",
                "severity_norm": "MEDIUM",
                "status": "CLOSED",
                "open_ts": base,
                "close_ts": base + pd.Timedelta(hours=24),
                "reopen_count": 0,
                "alert_ids": [],
            }
            for i in range(12)
        ]
    )
    return {"cases": cases}


def test_trigger_fires_on_planted_scenario() -> None:
    """Perfect-SLA fixture: flagged with row evidence."""
    signal = EG013PerfectSla()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire EG-013."""
    frames = corpus_frames("cse_alpha")
    result = EG013PerfectSla().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = EG013PerfectSla()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
