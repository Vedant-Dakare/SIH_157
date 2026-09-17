"""Unit tests for the anomaly ensemble (PyOD x5 + Mahalanobis)."""

from __future__ import annotations

import pandas as pd
from satsa.features.entity_features import FEATURE_SCHEMA
from satsa.signals.anomaly import ensemble_scores, feature_contributions, top_contributors
from satsa.signals.runner import build_all_features, run_anomaly


def _matrix() -> pd.DataFrame:
    """Six entities over the real feature schema with one planted outlier."""
    import warnings

    warnings.filterwarnings("ignore")
    features = build_all_features()
    entities = sorted(features)[:6]
    frame = pd.DataFrame(
        [[float(features[e].get(c, 0.0)) for c in FEATURE_SCHEMA] for e in entities],
        columns=FEATURE_SCHEMA,
    )
    frame.iloc[0] = frame.iloc[0] * 3.0 + 1.0
    return frame


def test_all_models_score_without_error() -> None:
    """All five PyOD models plus Mahalanobis initialise and score."""
    scores = ensemble_scores(_matrix())
    assert set(scores["model_scores"]) == {"iforest", "ecod", "copod", "hbos", "lof", "mahalanobis"}
    assert len(scores["anomaly_score"]) == 6
    assert all(0.0 <= s <= 1.0 for s in scores["anomaly_score"])
    assert sorted(scores["anomaly_rank"]) == [1, 2, 3, 4, 5, 6]


def test_contributions_within_tolerance() -> None:
    """Ablation contributions are finite, deterministic, and schema-grounded."""
    frame = _matrix()
    first = feature_contributions(frame)
    second = feature_contributions(frame)
    assert len(first) == 6
    for contrib in first:
        assert contrib
        assert all(isinstance(v, float) and v == v for v in contrib.values())
        assert len(top_contributors(contrib)) == 5
        assert set(top_contributors(contrib)) <= set(frame.columns)
    assert first == second


def test_anomaly_never_sole_basis() -> None:
    """Anomaly output always pairs with a named rule-based signal."""
    import warnings

    from satsa.signals.base import SignalResult
    from satsa.signals.runner import build_all_features

    warnings.filterwarnings("ignore")
    features = build_all_features()
    entities = sorted(features)[:3]
    subset = {e: features[e] for e in entities}
    fired = SignalResult(
        finding_id="f1",
        entity_id=entities[0],
        signal_id="EG-001",
        value=0.9,
        threshold=0.2,
        score=1.0,
        severity="HIGH",
        confidence="MEDIUM",
        sample_size=10,
        window_start="2024-05-02",
        window_end="2024-06-01",
        is_flagged=True,
    )
    quiet = SignalResult(
        finding_id="f2",
        entity_id=entities[0],
        signal_id="NS-004",
        value=0.1,
        threshold=0.34,
        score=0.29,
        severity="MEDIUM",
        confidence="MEDIUM",
        sample_size=10,
        window_start="2024-05-02",
        window_end="2024-06-01",
        is_flagged=False,
    )
    fired_only = {"EG-001": fired, "NS-004": quiet}
    quiet_only = {"NS-004": quiet}
    anomaly = run_anomaly(
        features=subset,
        rule_results={e: (fired_only if e == entities[0] else quiet_only) for e in entities},
    )
    assert anomaly[entities[0]]["paired_signal_id"] == "EG-001"
    assert len(anomaly[entities[0]]["top5_contributing_features"]) == 5


def test_single_entity_falls_back() -> None:
    """Single-entity input raises so callers fall back to peer benchmarks."""
    import pytest

    frame = pd.DataFrame([[1.0, 2.0]], columns=["a", "b"])
    with pytest.raises(ValueError):
        ensemble_scores(frame)
