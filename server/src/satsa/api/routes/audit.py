"""Audit routes: chain verification and entry listing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from satsa.api import deps


def _connect() -> duckdb.DuckDBPyConnection:
    from satsa.audit import ledger as audit_ledger

    target = Path(deps.WAREHOUSE_ROOT) / "audit.duckdb"
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(target))
    audit_ledger._ensure_db(conn)
    return conn


def verify() -> tuple[int, dict[str, Any]]:
    """GET /audit/verify."""
    from satsa.audit import ledger as audit_ledger

    conn = _connect()
    try:
        source = deps.WAREHOUSE_ROOT / "audit_ledger.jsonl"
        if source.exists():
            try:
                source_result = audit_ledger._verify_rows(audit_ledger._read_jsonl(source))
            except (OSError, ValueError, TypeError):
                source_result = audit_ledger.VerificationResult(
                    valid=False,
                    first_broken_seq=0,
                    merkle_root="",
                    entry_count=0,
                )
            if source_result.valid:
                audit_ledger.sync_duckdb_from_jsonl(conn, source)
                result = source_result
            else:
                result = source_result
        else:
            result = audit_ledger.verify_chain(conn)
    finally:
        conn.close()
    return 200, {
        "valid": result.valid,
        "entry_count": result.entry_count,
        "merkle_root": result.merkle_root,
    }


def entries(query: dict[str, str]) -> tuple[int, dict[str, Any]]:
    """GET /audit/entries with optional run filter."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT seq, run_id, ts, event_type, payload_json, prev_hash, entry_hash, signature"
            " FROM ledger ORDER BY seq"
        ).fetchall()
    finally:
        conn.close()
    run_id = query.get("run_id", "")
    out = [
        {
            "seq": r[0],
            "run_id": r[1],
            "ts": r[2],
            "event_type": r[3],
            "payload": json.loads(r[4] or "{}"),
            "prev_hash": r[5],
            "entry_hash": r[6],
            "signature": r[7],
        }
        for r in rows
        if not run_id or r[1] == run_id
    ]
    return 200, {"entries": out}
