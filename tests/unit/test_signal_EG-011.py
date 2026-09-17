"""Unit tests for EG-011 duplicate chain depth."""

from __future__ import annotations

import pandas as pd
from satsa.signals.execution_gaps import EG011DuplicateChain

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Six cases with a duplicate chain and DUPLICATE dispositions."""
    cases = pd.DataFrame(
        [
            {
                "case_id": f"c{i}",
                "severity_norm": "MEDIUM",
                "status": "CLOSED",
                "disposition_code": "DUPLICATE" if i < 2 else "BENIGN",
                "is_duplicate_of": ("c0" if i == 1 else ("c1" if i == 2 else "")),
                "open_ts": pd.Timestamp("2024-05-10 08:00", tz="UTC"),
                "close_ts": pd.Timestamp("2024-05-10 09:00", tz="UTC"),
                "reopen_count": 0,
                "alert_ids": [],
            }
            for i in range(6)
        ]
    )
    return {"cases": cases}


def test_trigger_fires_on_planted_scenario() -> None:
    """Duplicate-chain fixture: flagged with row evidence."""
    signal = EG011DuplicateChain()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire EG-011."""
    frames = corpus_frames("cse_alpha")
    result = EG011DuplicateChain().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = EG011DuplicateChain()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
