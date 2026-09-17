"""Shared fixtures for Phase 2 signal unit tests (new file, Phase 0+1 untouched)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pandas as pd
from satsa.signals._config import load_thresholds
from satsa.signals.base import SignalContext
from satsa.signals.runner import load_entity

UTC = UTC
WINDOW = ("2024-05-02", "2024-06-01")


def corpus_frames(entity_id: str) -> dict[str, pd.DataFrame]:
    """Load the six canonical tables for a synthetic entity."""
    return load_entity(entity_id)


def make_ctx(
    entity_id: str,
    frames: dict[str, pd.DataFrame],
    seed: int = 7,
    cohort_features: dict[str, list[float]] | None = None,
    cohort_stats: dict[str, Any] | None = None,
) -> SignalContext:
    """Build a deterministic SignalContext from frames."""
    return SignalContext(
        entity_id=entity_id,
        run_id="unit-test",
        window_start=WINDOW[0],
        window_end=WINDOW[1],
        features={},
        alerts=frames.get("alerts", pd.DataFrame()),
        cases=frames.get("cases", pd.DataFrame()),
        investigations=frames.get("investigations", pd.DataFrame()),
        escalations=frames.get("escalations", pd.DataFrame()),
        assets=frames.get("assets", pd.DataFrame()),
        telemetry=frames.get("telemetry", pd.DataFrame()),
        cohort_stats=dict(cohort_stats or {}),
        cohort_features=dict(cohort_features or {}),
        config=load_thresholds(),
        seed=seed,
    )


def one_row_frames() -> dict[str, pd.DataFrame]:
    """Minimal single-record frames triggering insufficient_data everywhere."""
    ts = datetime(2024, 5, 10, 12, 0, tzinfo=UTC)
    return {
        "alerts": pd.DataFrame(
            [
                {
                    "alert_id": "a1",
                    "asset_id": "asset1",
                    "severity_norm": "HIGH",
                    "category": "MALWARE",
                    "detected_ts": ts,
                    "ack_ts": ts,
                    "close_ts": ts,
                }
            ]
        ),
        "cases": pd.DataFrame(
            [
                {
                    "case_id": "c1",
                    "asset_id": "asset1",
                    "severity_norm": "HIGH",
                    "status": "OPEN",
                    "disposition_code": "TRUE_POSITIVE",
                    "tier": "T2",
                    "open_ts": ts,
                    "close_ts": pd.NaT,
                    "reopen_count": 0,
                    "alert_ids": ["a1"],
                    "detected_ts": ts,
                    "ack_ts": ts,
                }
            ]
        ),
        "investigations": pd.DataFrame(
            [
                {
                    "investigation_id": "i1",
                    "case_id": "c1",
                    "analyst_id": "x",
                    "notes": "looked, fine",
                }
            ]
        ),
        "escalations": pd.DataFrame(columns=["escalation_id", "case_id", "from_tier", "to_tier"]),
        "assets": pd.DataFrame(
            [
                {
                    "asset_id": "asset1",
                    "criticality": "medium",
                    "environment": "production",
                    "os_family": "linux",
                    "internet_facing": False,
                }
            ]
        ),
        "telemetry": pd.DataFrame(
            [{"asset_id": "asset1", "source": "edr", "observed_ts": ts}]
        ),
    }


def assert_evidence(signal: Any, result: Any) -> None:
    """Assert a result carries supporting rows and counter rows or a reason."""
    bundle = signal.evidence(result)
    assert len(bundle.supporting_rows) >= 1
    assert len(bundle.counter_rows) >= 1 or bundle.counter_none_reason
    assert bundle.evidence_id
