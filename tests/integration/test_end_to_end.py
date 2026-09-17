"""Phase 6 end-to-end pipeline test (new file, prior phases untouched)."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path


def _seeded_scoring_ledger() -> dict[str, object]:
    """Prior runs that make S2/S7/S8 novel (same shape as Phase 4)."""
    stale = ["cse_alpha", "cse_charlie", "cse_delta", "cse_echo", "cse_foxtrot", "cse_india"]
    now = datetime.now(UTC).isoformat()
    return {
        "runs": [
            {"run_id": f"prior-{i}", "ts": now, "findings": dict.fromkeys(stale, ["EG-001"])}
            for i in range(4)
        ],
        "last_reviewed": dict.fromkeys(stale, now),
    }


def test_end_to_end_pipeline(tmp_path: Path) -> None:
    """Seed → full pipeline → reports, verified ledger, correct queues, < 15 min."""
    import duckdb
    from satsa.audit import ledger as audit_ledger
    from satsa.pipeline.orchestrator import run_pipeline

    started = time.monotonic()
    ledger_path = Path("data/scoring/ledger.json")
    backup = None
    if ledger_path.exists():
        backup = tmp_path / "ledger_backup.json"
        backup.write_text(ledger_path.read_text(encoding="utf-8"), encoding="utf-8")
    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text(json.dumps(_seeded_scoring_ledger()), encoding="utf-8")
        out = run_pipeline(run_id="e2e", force=True)
    finally:
        if backup is not None:
            ledger_path.write_text(backup.read_text(encoding="utf-8"), encoding="utf-8")
        elif ledger_path.exists():
            ledger_path.unlink()
    elapsed = time.monotonic() - started
    assert out["aborted"] is False
    assert elapsed < 900, f"full run took {elapsed:.0f}s"

    reports = Path("data/curated/reports/e2e")
    for name in ("portfolio_report.html", "review_queue.html", "negative_space_map.html",
                 "data_quality_report.html", "entity_cse_bravo.html", "findings.csv"):
        assert (reports / name).exists(), name

    conn = duckdb.connect("data/warehouse/audit.duckdb")
    try:
        verification = audit_ledger.verify_chain(conn)
    finally:
        conn.close()
    assert verification.valid

    queue_path = Path("data/warehouse/runs/e2e/queue.json")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    top = queue[0]["entity_id"] if queue else None
    assert top in ("cse_bravo", "cse_golf", "cse_hotel"), top
    assert top != "cse_alpha"
    insufficient = json.loads(
        (Path("data/warehouse/runs/e2e/records.json")).read_text(encoding="utf-8"))
    low = [e for e, r in insufficient.items() if r["data_completeness"] < 0.6]
    assert "cse_juliet" in low
    assert "cse_juliet" not in [e["entity_id"] for e in queue]
