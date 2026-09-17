"""Unit tests for EG-012 orphan case rate."""

from __future__ import annotations

import pandas as pd
from satsa.signals.execution_gaps import EG012OrphanRate

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Six cases, three with no linked alerts."""
    cases = pd.DataFrame(
        [
            {
                "case_id": f"c{i}",
                "severity_norm": "MEDIUM",
                "status": "OPEN",
                "open_ts": pd.Timestamp("2024-05-10 08:00", tz="UTC"),
                "close_ts": pd.NaT,
                "reopen_count": 0,
                "alert_ids": [] if i < 3 else ["a1"],
            }
            for i in range(6)
        ]
    )
    return {"cases": cases}


def test_trigger_fires_on_planted_scenario() -> None:
    """Orphan fixture: flagged with row evidence."""
    signal = EG012OrphanRate()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire EG-012."""
    frames = corpus_frames("cse_alpha")
    result = EG012OrphanRate().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = EG012OrphanRate()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
