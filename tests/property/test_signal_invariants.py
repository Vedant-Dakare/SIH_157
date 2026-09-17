"""Property tests: signal invariants (no NaN, min_n gating, determinism, bounded scores)."""

from __future__ import annotations

import math

import pandas as pd
from hypothesis import given, settings
from hypothesis import strategies as st
from satsa.signals.registry import get_enabled_signals

from tests.unit.signal_helpers import make_ctx


def _seeded_frames(seed: int, n: int = 8) -> dict[str, pd.DataFrame]:
    """Build deterministic pseudo-random valid frames."""
    import numpy as np

    rng = np.random.default_rng(seed)
    base = pd.Timestamp("2024-05-10 12:00", tz="UTC")
    severities = rng.choice(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"], size=n).tolist()
    alerts = pd.DataFrame(
        [
            {
                "alert_id": f"a{i}",
                "asset_id": f"asset{i % 3}",
                "severity_norm": severities[i],
                "category": "MALWARE",
                "detected_ts": base,
                "ack_ts": base + pd.Timedelta(minutes=10),
                "close_ts": base + pd.Timedelta(hours=2),
                "ingest_ts": base,
            }
            for i in range(n)
        ]
    )
    cases = pd.DataFrame(
        [
            {
                "case_id": f"c{i}",
                "asset_id": f"asset{i % 3}",
                "severity_norm": severities[i],
                "status": "CLOSED",
                "disposition_code": "TRUE_POSITIVE",
                "tier": "T2",
                "open_ts": base,
                "close_ts": base + pd.Timedelta(hours=2),
                "reopen_count": 0,
                "alert_ids": [f"a{i}"],
                "detected_ts": base,
                "ack_ts": base,
            }
            for i in range(n)
        ]
    )
    investigations = pd.DataFrame(
        [
            {
                "investigation_id": f"i{i}",
                "case_id": f"c{i}",
                "analyst_id": "analyst",
                "notes": f"Detailed distinct investigation narrative number {i} with observations.",
            }
            for i in range(n)
        ]
    )
    assets = pd.DataFrame(
        [
            {
                "asset_id": f"asset{i}",
                "criticality": "medium",
                "environment": "production",
                "os_family": "linux",
                "internet_facing": False,
            }
            for i in range(3)
        ]
    )
    telemetry = pd.DataFrame(
        [
            {"asset_id": f"asset{i}", "source": s, "observed_ts": base}
            for i in range(3)
            for s in ("edr", "auth")
        ]
    )
    escalations = pd.DataFrame(
        [
            {"escalation_id": f"e{i}", "case_id": f"c{i}", "from_tier": "T1", "to_tier": "T2"}
            for i in range(min(2, n))
        ]
    )
    return {
        "alerts": alerts,
        "cases": cases,
        "investigations": investigations,
        "escalations": escalations,
        "assets": assets,
        "telemetry": telemetry,
    }


@given(seed=st.integers(min_value=0, max_value=1000))
@settings(max_examples=20, deadline=None)
def test_no_nan_leakage(seed: int) -> None:
    """No signal may return NaN in value, score, or threshold."""
    frames = _seeded_frames(seed)
    for signal in get_enabled_signals():
        result = signal.compute(make_ctx("cse_probe", frames, seed=seed))
        assert not math.isnan(result.value), signal.id
        assert not math.isnan(result.score), signal.id
        assert not math.isnan(result.threshold), signal.id


@given(seed=st.integers(min_value=0, max_value=1000))
@settings(max_examples=10, deadline=None)
def test_determinism(seed: int) -> None:
    """Same input plus same seed yields identical SignalResults."""
    frames = _seeded_frames(seed)
    for signal in get_enabled_signals():
        first = signal.compute(make_ctx("cse_probe", frames, seed=seed))
        second = signal.compute(make_ctx("cse_probe", frames, seed=seed))
        assert first == second, signal.id


def test_scores_bounded_and_gated() -> None:
    """Scores stay in [0, 1] and sub-min_n inputs force insufficient_data."""
    from tests.unit.signal_helpers import one_row_frames

    frames = _seeded_frames(11)
    for signal in get_enabled_signals():
        result = signal.compute(make_ctx("cse_probe", frames, seed=11))
        assert 0.0 <= result.score <= 1.0, signal.id
        tiny = signal.compute(make_ctx("cse_probe", one_row_frames(), seed=11))
        if tiny.sample_size < signal.min_n(make_ctx("cse_probe", one_row_frames(), seed=11)):
            assert tiny.insufficient_data is True, signal.id
            assert tiny.is_flagged is False, signal.id
