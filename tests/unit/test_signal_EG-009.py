"""Unit tests for EG-009 backfill documentation."""

from __future__ import annotations

import pandas as pd
from satsa.signals.execution_gaps import EG009Backfill

from tests.unit.signal_helpers import assert_evidence, corpus_frames, make_ctx, one_row_frames


def _trigger_frames() -> dict[str, pd.DataFrame]:
    """Six alerts, two ingested 40 days after detection."""
    rows = []
    for i in range(6):
        detected = pd.Timestamp("2024-05-01 12:00", tz="UTC")
        ingest = pd.Timestamp("2024-06-10 12:00", tz="UTC") if i < 2 else detected
        rows.append(
            {
                "alert_id": f"a{i}",
                "asset_id": "asset1",
                "severity_norm": "HIGH",
                "detected_ts": detected,
                "ingest_ts": ingest,
            }
        )
    return {"alerts": pd.DataFrame(rows)}


def test_trigger_fires_on_planted_scenario() -> None:
    """Backfill fixture: flagged with row evidence."""
    signal = EG009Backfill()
    result = signal.compute(make_ctx("cse_probe", _trigger_frames()))
    assert result.is_flagged is True
    assert result.insufficient_data is False
    assert_evidence(signal, result)


def test_healthy_silent() -> None:
    """S1 (healthy) does not fire EG-009."""
    frames = corpus_frames("cse_alpha")
    result = EG009Backfill().compute(make_ctx("cse_alpha", frames))
    assert result.is_flagged is False


def test_insufficient_data() -> None:
    """A single record yields insufficient_data without flagging."""
    signal = EG009Backfill()
    result = signal.compute(make_ctx("cse_probe", one_row_frames()))
    assert result.insufficient_data is True
    assert result.is_flagged is False
