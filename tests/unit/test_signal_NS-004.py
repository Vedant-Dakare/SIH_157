"""Unit tests for NS-004 MITRE coverage absence."""

from __future__ import annotations

import pandas as pd
from satsa.signals.negative_space import NS004MitreAbsence

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Six phishing-only alerts (zero MITRE-mapped tactics)."""
    alerts = pd.DataFrame(
        [
            {
                "alert_id": f"a{i}",
                "asset_id": "asset1",
                "category": "PHISHING",
                "detected_ts": pd.Timestamp("2024-05-10 12:00", tz="UTC"),
            }
            for i in range(6)
        ]
    )
    return {"alerts": alerts}


def test_trigger_fires_on_planted_scenario() -> None:
    """MITRE-absent fixture: flagged with row evidence."""
    signal = NS004MitreAbsence()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire NS-004."""
    frames = corpus_frames("cse_alpha")
    result = NS004MitreAbsence().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = NS004MitreAbsence()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
