"""Phase 4 portfolio tests (new file, prior phases untouched)."""

from __future__ import annotations

from typing import Any


def _record(entity_id: str, band: str, overall: float) -> dict[str, Any]:
    """Minimal score record."""
    return {"entity_id": entity_id, "band": band, "overall_score": overall}


def test_band_counts_sum_to_total() -> None:
    """entity_count_by_band sums to the entity count."""
    from satsa.scoring.portfolio import portfolio_summary

    records = {
        "a": _record("a", "HIGH", 80.0),
        "b": _record("b", "LOW", 5.0),
        "c": _record("c", "MODERATE", 30.0),
    }
    summary = portfolio_summary(records)
    assert sum(summary["entity_count_by_band"].values()) == 3
    assert summary["top_5_entities_by_risk"][0] == "a"
    assert set(summary["sector_aggregates"]) >= {"unknown"}


def test_declining_scores_classify_improving() -> None:
    """Falling window scores yield an IMPROVING trend."""
    from satsa.scoring.portfolio import trend_analysis

    history = [
        {"window": "w1", "overall_score": 60.0, "findings": ["EG-001", "EG-006"]},
        {"window": "w2", "overall_score": 40.0, "findings": ["EG-001"]},
        {"window": "w3", "overall_score": 20.0, "findings": ["EG-001"]},
    ]
    out = trend_analysis("cse_x", history)
    assert out["trend"] == "IMPROVING"
    assert out["signals"]["EG-006"] == "RESOLVED"
    assert out["signals"]["EG-001"] == "PERSISTENT"
    short = trend_analysis("cse_x", history[:1])
    assert short["trend"] == "INSUFFICIENT_HISTORY"


def test_drill_down_chain_intact_for_sample() -> None:
    """Portfolio → entity → domain → signal → evidence resolves without breaks."""
    import random

    from satsa.scoring.portfolio import drill_down, portfolio_summary
    from satsa.scoring.risk_engine import score_all
    from satsa.signals.registry import get_signal
    from satsa.signals.runner import build_all_features, run_entity

    scored = score_all(run_id="t")
    summary = portfolio_summary(scored["records"])
    assert summary["top_5_entities_by_risk"]
    features = build_all_features()
    rng = random.Random(7)
    sample = rng.sample(sorted(scored["records"]), 3)
    for entity_id in sample:
        record = scored["records"][entity_id]
        results = run_entity(entity_id, features)
        bundles = {}
        for signal_id in record["flagged_signals"]:
            signal = get_signal(signal_id)
            bundles[signal_id] = signal.evidence(results[signal_id]) if signal else None
        chain = drill_down(entity_id, record, results, bundles)
        assert chain["overall_score"] == record["overall_score"]
        for domain, members in record["domain_members"].items():
            for signal_id in members:
                leaf = chain["domains"][domain]["signals"][signal_id]
                assert leaf["is_flagged"] is True
                if bundles[signal_id] is not None:
                    assert leaf["evidence_rows"] >= 1
                    assert leaf["evidence_id"]
