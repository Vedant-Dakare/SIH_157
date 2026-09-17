"""Phase 5 explain-chain integration (new file, prior phases untouched)."""

from __future__ import annotations

import random
from pathlib import Path


def test_explain_chain_no_broken_links(tmp_path: Path) -> None:
    """portfolio → entity → finding → signal → evidence → ledger, ×5 findings."""
    from types import SimpleNamespace

    import duckdb
    from satsa.audit import ledger as audit_ledger
    from satsa.audit.merkle import compute_run_manifest
    from satsa.explain import evidence as ev_mod
    from satsa.explain.evidence import _connect
    from satsa.scoring.risk_engine import score_all
    from satsa.signals.registry import get_signal
    from satsa.signals.runner import build_all_features, run_entity

    run_id = "explain-chain"
    jsonl = tmp_path / "ledger.jsonl"
    db_path = tmp_path / "audit.duckdb"
    ev_db = tmp_path / "evidence.duckdb"

    scored = score_all(run_id=run_id)
    assert scored["ranking"], "main ranking must be non-empty"
    features = build_all_features()
    rng = random.Random(7)

    pool: list[tuple[str, str]] = []
    for entity_id in sorted(scored["records"]):
        results = run_entity(entity_id, features)
        for signal_id, result in sorted(results.items()):
            if result.is_flagged and not signal_id.startswith("COMP-"):
                pool.append((entity_id, signal_id))
    assert len(pool) >= 5
    sample = rng.sample(pool, 5)

    ev_conn = _connect(ev_db)
    try:
        for entity_id, signal_id in sample:
            # portfolio → entity → finding
            record = scored["records"][entity_id]
            assert signal_id in record["flagged_signals"]
            results = run_entity(entity_id, features)
            result = results[signal_id]
            # finding → signal → evidence rows
            signal = get_signal(signal_id)
            assert signal is not None
            bundle = signal.evidence(result)
            assert len(bundle.supporting_rows) >= 1
            window = f"{result.window_start}..{result.window_end}"
            stored = ev_mod.materialize(
                result.finding_id, signal_id, entity_id, window, bundle, ev_conn
            )
            assert stored.supporting_rows or stored.counter_rows_absent_reason.strip()
            # evidence → ledger entry
            entry = audit_ledger.append_event(
                run_id,
                "FINDING",
                {
                    "finding_id": result.finding_id,
                    "signal_id": signal_id,
                    "entity_id": entity_id,
                    "evidence_id": stored.evidence_id,
                    "window": window,
                },
                jsonl_path=jsonl,
                db_path=db_path,
            )
            assert entry.seq >= 0
    finally:
        ev_conn.close()

    conn = duckdb.connect(str(db_path))
    try:
        verification = audit_ledger.verify_chain(conn)
        assert verification.valid, verification.first_broken_seq
        assert verification.entry_count == 5
        settings = SimpleNamespace(manifest_key="test-key")
        manifest = compute_run_manifest(run_id, conn, settings, manifest_dir=tmp_path / "runs")
    finally:
        conn.close()
    assert manifest.entry_count == 5
    assert manifest.merkle_root == verification.merkle_root
    assert manifest.signature
