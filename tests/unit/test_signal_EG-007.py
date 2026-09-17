"""Unit tests for EG-007 metric gaming pattern."""

from __future__ import annotations

import pandas as pd
from satsa.signals.execution_gaps import EG007MetricGaming

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Six rushed, reopened, root-cause-free closures with quartile peers."""
    base = pd.Timestamp("2024-05-10 12:00", tz="UTC")
    cases = pd.DataFrame(
        [
            {
                "case_id": f"c{i}",
                "severity_norm": "HIGH",
                "status": "CLOSED",
                "disposition_code": "BENIGN",
                "tier": "T1",
                "open_ts": base,
                "close_ts": base + pd.Timedelta(hours=1),
                "reopen_count": 3 if i < 3 else 0,
                "alert_ids": [],
                "detected_ts": base,
            }
            for i in range(6)
        ]
    )
    return {"cases": cases, "alerts": pd.DataFrame(), "escalations": pd.DataFrame()}


def _peers() -> dict[str, list[float]]:
    """Peer distributions placing the trigger in the gaming quartiles."""
    return {
        "closure_rate": [0.4, 0.5, 0.5, 0.6, 0.6, 0.7, 0.8],
        "reopen_rate": [0.0, 0.0, 0.0, 0.05, 0.05, 0.1, 0.1],
        "root_cause_rate": [0.5, 0.5, 0.6, 0.6, 0.7, 0.7, 0.8],
    }


def test_trigger_fires_on_planted_scenario() -> None:
    """Gaming-pattern fixture: top-quartile closure/recurrence, bottom root-cause."""
    signal = EG007MetricGaming()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames(), cohort_features=_peers()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire EG-007."""
    frames = corpus_frames("cse_alpha")
    result = EG007MetricGaming().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = EG007MetricGaming()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
