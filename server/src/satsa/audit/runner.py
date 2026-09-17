"""Audit operations: verify the chain, export portable bundles (module runner).

Usage:
  python -m satsa.audit.runner verify
  python -m satsa.audit.runner export --run-id demo
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import duckdb


def _open_ledger(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    """Open (creating) the audit DuckDB."""
    from satsa.audit import ledger as audit_ledger

    target = Path(db_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(target))
    audit_ledger._ensure_db(conn)
    return conn


def do_verify(db_path: str | Path = "data/warehouse/audit.duckdb") -> dict[str, Any]:
    """Verify the global chain and report per-run pass/fail."""
    from satsa.audit import ledger as audit_ledger

    conn = _open_ledger(db_path)
    try:
        result = audit_ledger.verify_chain(conn, audit_ledger.LEDGER_JSONL)
        rows = conn.execute("SELECT DISTINCT run_id FROM ledger").fetchall()
        runs = sorted(str(r[0]) for r in rows)
        per_run = dict.fromkeys(runs, result.valid)
        print(f"ledger valid={result.valid} entries={result.entry_count} root={result.merkle_root}")
        for run_id in runs:
            print(f"  run {run_id}: {'PASS' if per_run[run_id] else 'FAIL'}")
        if not result.valid:
            print(f"  first broken seq: {result.first_broken_seq}")
        return {"verification": result.model_dump(), "per_run": per_run}
    finally:
        conn.close()


def do_export(
    run_id: str,
    db_path: str | Path = "data/warehouse/audit.duckdb",
    out_dir: str | Path = "deliverables",
) -> Path:
    """Write manifest + run ledger entries into a portable zip bundle."""
    from satsa.audit.merkle import compute_run_manifest
    from satsa.settings import load_settings

    conn = _open_ledger(db_path)
    try:
        settings = load_settings()
        manifest = compute_run_manifest(run_id, conn, settings)
        rows = conn.execute(
            "SELECT seq, run_id, ts, event_type, payload_json, prev_hash, entry_hash, signature"
            " FROM ledger WHERE run_id = ? ORDER BY seq",
            [run_id],
        ).fetchall()
        entries = [
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
        ]
    finally:
        conn.close()
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    bundle = target / f"{run_id}_audit_bundle.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(f"{run_id}.manifest.json", manifest.model_dump_json(indent=2))
        archive.writestr(f"{run_id}.ledger.json", json.dumps(entries, indent=2, sort_keys=True))
    print(f"wrote {bundle} ({len(entries)} entries)")
    return bundle


def main(argv: list[str] | None = None) -> int:
    """CLI entry: verify | export --run-id ID."""
    parser = argparse.ArgumentParser(description="SATSA audit runner (Phase 5)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    exp = sub.add_parser("export")
    exp.add_argument("--run-id", required=True)
    args = parser.parse_args(argv)
    if args.command == "verify":
        out = do_verify()
        return 0 if out["verification"]["valid"] else 1
    do_export(args.run_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
