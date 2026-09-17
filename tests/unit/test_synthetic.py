"""Unit tests for synthetic corpora and ground truth."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


def _thresholds() -> dict:
    """Load thresholds for test expectations."""
    with open("configs/thresholds.yaml", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def test_all_ten_scenarios_generate() -> None:
    """All 10 scenarios generate six parquet files each."""
    root = Path("data/synthetic")
    expected = [
        "cse_alpha",
        "cse_bravo",
        "cse_charlie",
        "cse_delta",
        "cse_echo",
        "cse_foxtrot",
        "cse_golf",
        "cse_hotel",
        "cse_india",
        "cse_juliet",
    ]
    for entity in expected:
        for table in ["alerts", "cases", "investigations", "escalations", "assets", "telemetry"]:
            assert (root / entity / f"{table}.parquet").exists(), f"missing {entity}/{table}"


def test_s2_premature_close() -> None:
    """S2 CRITICAL cases close within 5 minutes of opening."""
    thresholds = _thresholds()
    limit_minutes = float(thresholds["premature_close_minutes"])
    frame = pd.read_parquet("data/synthetic/cse_bravo/cases.parquet")
    crit = frame[(frame["severity_norm"] == "CRITICAL") & (frame["close_ts"].notna())]
    assert len(crit) > 0
    deltas = (
        pd.to_datetime(crit["close_ts"], utc=True) - pd.to_datetime(crit["open_ts"], utc=True)
    ).dt.total_seconds() / 60.0
    assert bool((deltas < limit_minutes).all())


def test_s3_coverage_gap() -> None:
    """S3 CRITICAL assets carry gap_flag TRUE."""
    frame = pd.read_parquet("data/synthetic/cse_charlie/assets.parquet")
    crit = frame[frame["criticality"].str.lower() == "high"]
    assert len(crit) > 0
    assert bool(crit["gap_flag"].all())


def test_s4_template_similarity() -> None:
    """S4 investigation notes have pairwise TF-IDF similarity above 0.85."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    frame = pd.read_parquet("data/synthetic/cse_delta/investigations.parquet")
    notes = frame["notes"].dropna().tolist()[:10]
    assert len(notes) >= 5
    matrix = TfidfVectorizer().fit_transform(notes)
    sims = cosine_similarity(matrix)
    n = sims.shape[0]
    off_diag = [sims[i, j] for i in range(n) for j in range(n) if i != j]
    assert min(off_diag) > 0.85


def test_s7_bulk_close_window() -> None:
    """S7 has 150 cases sharing one analyst inside a 20-second window."""
    frame = pd.read_parquet("data/synthetic/cse_golf/cases.parquet")
    assert len(frame) >= 150
    top_analyst = frame["analyst_id"].value_counts().iloc[0]
    assert top_analyst >= 150
    analyst_id = frame["analyst_id"].value_counts().index[0]
    subset = frame[frame["analyst_id"] == analyst_id].head(150)
    opens = pd.to_datetime(subset["open_ts"], utc=True)
    closes = pd.to_datetime(subset["close_ts"], utc=True)
    span = (max(closes.max(), opens.max()) - min(opens.min(), closes.min())).total_seconds()
    assert span <= 20.0 + 1e-6


def test_s8_escalation_bypass() -> None:
    """S8 CRITICAL cases have zero linked escalation records."""
    cases = pd.read_parquet("data/synthetic/cse_hotel/cases.parquet")
    esc = pd.read_parquet("data/synthetic/cse_hotel/escalations.parquet")
    crit = cases[cases["severity_norm"] == "CRITICAL"]
    assert len(crit) > 0
    assert bool((crit["tier"] == "T1").all())
    esc_rows = 0 if "_empty" in esc.columns and len(esc.columns) == 1 else len(esc)
    assert esc_rows == 0


def test_s10_partial_feed_nulls() -> None:
    """S10 has roughly 30 percent nulled required fields."""
    frame = pd.read_parquet("data/synthetic/cse_juliet/alerts.parquet")
    null_frac = float(frame["severity_norm"].isna().mean()) if len(frame) else 0.0
    assert 0.20 <= null_frac <= 0.40


def test_ground_truth_covers_all_pairs() -> None:
    """ground_truth.parquet labels every entity-signal pair."""
    from satsa.synthetic.scenarios import ALL_SIGNAL_IDS, SCENARIOS

    frame = pd.read_parquet("data/synthetic/ground_truth.parquet")
    for entity in SCENARIOS:
        for signal in ALL_SIGNAL_IDS:
            subset = frame[(frame["entity_id"] == entity) & (frame["signal_id"] == signal)]
            assert len(subset) >= 1, f"missing {entity}/{signal}"


def test_s10_confidence() -> None:
    """S10 ground truth rows carry confidence 0.7."""
    frame = pd.read_parquet("data/synthetic/ground_truth.parquet")
    s10 = frame[frame["entity_id"] == "cse_juliet"]
    assert len(s10) > 0
    assert bool((s10["confidence"] == 0.7).all())


def test_s1_healthy_all_false() -> None:
    """S1 healthy baseline has expected_flag FALSE for all signals."""
    frame = pd.read_parquet("data/synthetic/ground_truth.parquet")
    s1 = frame[frame["entity_id"] == "cse_alpha"]
    assert len(s1) > 0
    assert bool((~s1["expected_flag"]).all())
