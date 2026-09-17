"""Unit tests for feature engineering modules."""

from __future__ import annotations

import pandas as pd
from satsa.features import asset as asset_mod
from satsa.features import coverage as coverage_mod
from satsa.features import text as text_mod
from satsa.features import workflow as workflow_mod
from satsa.features.entity_features import (
    FEATURE_SCHEMA,
    benjamini_hochberg,
    build_entity_features,
    features_to_polars,
)
from satsa.features.temporal import detect_batch_close
from satsa.signals.runner import load_entity


def test_batch_close_burst_detected() -> None:
    """The S7 corpus yields a burst of >= 50 with a 60s-scale duration."""
    cases = load_entity("cse_golf")["cases"]
    bursts = detect_batch_close(cases)
    assert not bursts.empty
    assert int(bursts["burst_size"].max()) >= 50
    assert set(bursts.columns) == {
        "burst_id",
        "burst_size",
        "burst_duration",
        "analyst_id",
        "window_start",
    }


def test_backfill_flags_retroactive_rows() -> None:
    """Records ingested far after the event are flagged as backfill."""
    alerts = pd.DataFrame(
        [
            {
                "alert_id": "a1",
                "detected_ts": pd.Timestamp("2024-01-01", tz="UTC"),
                "ingest_ts": pd.Timestamp("2024-06-01", tz="UTC"),
            },
            {
                "alert_id": "a2",
                "detected_ts": pd.Timestamp("2024-05-30", tz="UTC"),
                "ingest_ts": pd.Timestamp("2024-06-01", tz="UTC"),
            },
        ]
    )
    flagged = workflow_mod.backfill_detection(alerts, "detected_ts")
    assert flagged["alert_id"].tolist() == ["a1"]


def test_text_lite_backend_scores() -> None:
    """LITE backend scores template similarity with length normalisation."""
    investigations = load_entity("cse_delta")["investigations"]
    feats = text_mod.text_features(investigations, backend="lite")
    assert feats["template_similarity_score"] > 0.85
    assert feats["backend"] == "lite"
    assert 0.0 <= feats["placeholder_ratio"] <= 1.0
    assert 0.0 <= feats["vocabulary_richness"] <= 1.0


def test_negative_space_map_schema() -> None:
    """The negative-space map emits the required six-column table."""
    frames = load_entity("cse_charlie")
    space = coverage_mod.negative_space_map("cse_charlie", frames["assets"], frames["telemetry"])
    assert list(space.columns) == [
        "entity_id",
        "asset_id",
        "expected_source",
        "observed",
        "gap_flag",
        "silence_days",
    ]
    assert bool(space["gap_flag"].any())


def test_shadow_assets_warn() -> None:
    """Unknown alert assets become UNKNOWN shadows with a WARNING."""
    import pytest

    alerts = pd.DataFrame([{"alert_id": "a1", "asset_id": "ghost"}])
    assets = pd.DataFrame([{"asset_id": "known", "criticality": "low"}])
    with pytest.warns(UserWarning):
        resolved = asset_mod.resolve_shadow_assets(alerts, assets)
    assert "ghost" in resolved["asset_id"].tolist()
    assert resolved.set_index("asset_id").loc["ghost", "criticality"] == "UNKNOWN"


def test_entity_vector_schema_and_bh_fdr() -> None:
    """Feature vectors span 120-200 polars columns with BH-adjusted p-values."""
    frames = load_entity("cse_alpha")
    feats = build_entity_features(
        "cse_alpha",
        frames["alerts"],
        frames["cases"],
        frames["investigations"],
        frames["escalations"],
        frames["assets"],
        frames["telemetry"],
    )
    assert 120 <= len(FEATURE_SCHEMA) <= 200
    assert set(feats) == set(FEATURE_SCHEMA)
    matrix = features_to_polars({"cse_alpha": feats})
    assert matrix.shape == (1, len(FEATURE_SCHEMA) + 1)
    padj = [feats[c] for c in FEATURE_SCHEMA if c.startswith("padj_")]
    raw = [feats[c] for c in FEATURE_SCHEMA if c.startswith("p_") and not c.startswith("padj_")]
    assert padj and raw and len(padj) == len(raw)
    assert all(0.0 <= v <= 1.0 for v in padj)
    assert benjamini_hochberg([0.01, 0.04, 0.5]) == [0.03, 0.06, 0.5]
