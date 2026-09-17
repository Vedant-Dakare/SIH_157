"""Phase 4 prioritisation tests (new file, prior phases untouched)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd

from tests.unit.scoring_helpers import fake_bundle, fake_result


def _scored(entity_id: str, overall: float, confidence: str, signals: list[str]) -> dict[str, Any]:
    """Minimal score record for queue tests."""
    return {
        "entity_id": entity_id,
        "overall_score": overall,
        "band": "ELEVATED",
        "confidence": confidence,
        "domain_contributions": {"operational_discipline": overall, "governance": 0.0},
        "flagged_signals": list(signals),
    }


def _env() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Fabricated results/bundles/frames with valid alert ids."""
    results = {"EG-001": fake_result("EG-001")}
    bundles = {"EG-001": fake_bundle(["a1", "a2", "a3"], ["c1", "c2", "c3"])}
    frames = {"alerts": pd.DataFrame([{"alert_id": f"a{i}"} for i in range(1, 6)])}
    return results, bundles, frames


def test_determinism_same_seed_same_order() -> None:
    """Same input + seed yields identical priority order."""
    from satsa.scoring.prioritisation import build_queue

    scored = {
        "e1": _scored("e1", 40.0, "HIGH", ["EG-001"]),
        "e2": _scored("e2", 40.0, "HIGH", ["EG-001"]),
        "e3": _scored("e3", 20.0, "MEDIUM", ["EG-001"]),
    }
    results, bundles, frames = _env()
    by_entity = {e: dict(results) for e in scored}
    bundle_map = {e: dict(bundles) for e in scored}
    frame_map = {e: frames for e in scored}
    first = build_queue(scored, by_entity, bundle_map, frame_map, {}, seed=7)
    second = build_queue(scored, by_entity, bundle_map, frame_map, {}, seed=7)
    assert [e["entity_id"] for e in first] == [e["entity_id"] for e in second]
    assert [e["priority"] for e in first] == [e["priority"] for e in second]


def test_novelty_downweights_repeat_findings() -> None:
    """Entities in N consecutive prior runs get reduced novelty weight."""
    from satsa.scoring.prioritisation import novelty_weight

    ledger = {"runs": [{"findings": {"e1": ["EG-001"]}}, {"findings": {"e1": ["EG-001"]}}]}
    assert novelty_weight("e1", ledger, prior_runs=2) < 1.0
    assert novelty_weight("e1", ledger, prior_runs=2) == 0.4
    assert novelty_weight("fresh", ledger, prior_runs=2) == 1.0
    assert novelty_weight("e1", {}, prior_runs=2) == 1.0


def test_coverage_gap_upweights_stale_entities() -> None:
    """Unreviewed > M days elevates the coverage weight."""
    from satsa.scoring.prioritisation import coverage_gap_weight

    old = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    recent = datetime.now(UTC).isoformat()
    assert coverage_gap_weight("e1", {"last_reviewed": {"e1": old}}, gap_days=30) == 1.25
    assert coverage_gap_weight("e1", {"last_reviewed": {"e1": recent}}, gap_days=30) == 1.0
    assert coverage_gap_weight("never", {}, gap_days=30) == 1.25


def test_samples_are_valid_canonical_ids() -> None:
    """Sample ids come from evidence and validate against the alerts table."""
    from satsa.scoring.prioritisation import build_queue

    scored = {"e1": _scored("e1", 40.0, "HIGH", ["EG-001"])}
    results, bundles, frames = _env()
    queue = build_queue(scored, {"e1": results}, {"e1": bundles}, {"e1": frames}, {}, seed=7)
    entry = queue[0]
    assert set(entry["sample_alert_ids"]) <= {"a1", "a2", "a3", "a4", "a5"}
    assert entry["sample_case_ids"]
    assert entry["expected_review_minutes"] >= 1
    assert isinstance(entry["expected_review_minutes"], int)
    assert entry["rank"] == 1
    assert entry["focus_area"] == "operational_discipline"
