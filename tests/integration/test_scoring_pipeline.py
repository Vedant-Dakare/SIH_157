"""Phase 4 scoring pipeline integration (new file, prior phases untouched)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


def _seeded_ledger() -> dict[str, object]:
    """Four prior runs surfacing every entity except S2/S7/S8 (novelty testbed)."""
    stale = ["cse_alpha", "cse_charlie", "cse_delta", "cse_echo", "cse_foxtrot", "cse_india"]
    now = datetime.now(UTC).isoformat()
    return {
        "runs": [
            {"run_id": f"prior-{i}", "ts": now, "findings": dict.fromkeys(stale, ["EG-001"])}
            for i in range(4)
        ],
        "last_reviewed": dict.fromkeys(stale, now),
    }


def test_scoring_pipeline_top3_and_queues(tmp_path: Path) -> None:
    """S2/S7/S8 top the review queue; S10 waits in insufficient-evidence."""
    import json

    from satsa.scoring.portfolio import trend_analysis
    from satsa.scoring.prioritisation import prioritise

    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps(_seeded_ledger()), encoding="utf-8")

    out = prioritise(run_id="demo", seed=42, ledger_path=ledger_path, top=10)
    top3 = [e["entity_id"] for e in out["queue"][:3]]
    assert top3 == ["cse_golf", "cse_hotel", "cse_bravo"]
    assert "cse_juliet" not in [e["entity_id"] for e in out["full_queue"]]
    assert "cse_juliet" in out["insufficient_queue"]

    first = out["queue"][0]
    assert first["rank"] == 1
    assert first["focus_area"]
    assert first["signal_ids"]
    assert first["expected_review_minutes"] >= 1
    assert first["sample_alert_ids"] or first["sample_case_ids"]

    history = [
        {"window": "w1", "overall_score": 30.0, "findings": ["EG-001"]},
        {"window": "w2", "overall_score": 28.0, "findings": ["EG-001"]},
        {
            "window": "w3",
            "overall_score": float(first["risk_score"]),
            "findings": list(first["signal_ids"]),
        },
    ]
    trend = trend_analysis(first["entity_id"], history)
    assert trend["trend"] in ("STABLE", "IMPROVING", "DETERIORATING")
    assert trend["signals"]
