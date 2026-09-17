"""Append-only tamper-evident ledger: JSONL (source of truth) + DuckDB table.

entry_hash = SHA-256(prev_hash || canonical_json(payload) || seq || ts),
with run_id and event_type bound inside the hashed envelope. Genesis
prev_hash is "0" * 64. Writes go to JSONL first, then DuckDB; a DuckDB
failure leaves JSONL as truth (warning logged, entry still returned).
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
from pydantic import BaseModel, Field

from satsa.audit.hashing import canonical_json, sha256_str
from satsa.audit.merkle import compute_merkle_root
from satsa.paths import from_root

logger = logging.getLogger(__name__)

GENESIS_PREV_HASH = "0" * 64
LEDGER_JSONL = from_root("data", "warehouse", "audit_ledger.jsonl")
LEDGER_DB = from_root("data", "warehouse", "audit.duckdb")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger (
    seq INTEGER PRIMARY KEY,
    run_id VARCHAR,
    ts VARCHAR,
    event_type VARCHAR,
    payload_json VARCHAR,
    prev_hash VARCHAR,
    entry_hash VARCHAR,
    signature VARCHAR
)
"""


@contextmanager
def _ledger_lock(jsonl: Path):
    """Serialize sequence allocation across concurrent pipeline processes."""
    lock_path = jsonl.with_suffix(jsonl.suffix + ".lock")
    handle = lock_path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            while True:
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


class LedgerEntry(BaseModel):
    """One tamper-evident ledger record."""

    seq: int = Field(ge=0)
    run_id: str = Field(min_length=1)
    ts: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str = Field(min_length=1)
    entry_hash: str = Field(min_length=1)
    signature: str | None = None


class VerificationResult(BaseModel):
    """Outcome of walking the hash chain."""

    valid: bool = False
    first_broken_seq: int | None = None
    merkle_root: str = ""
    entry_count: int = 0


def _utc_now() -> str:
    """Current UTC time as ISO-8601."""
    return datetime.now(UTC).isoformat()


def _hash_entry(
    prev_hash: str, seq: int, ts: str, run_id: str, event_type: str, payload: dict[str, Any]
) -> str:
    """Hash the full envelope so every field is tamper-evident."""
    parts = [prev_hash, canonical_json(payload), str(seq), ts, run_id, event_type]
    return sha256_str("||".join(parts))


def _ensure_db(conn: duckdb.DuckDBPyConnection) -> None:
    """Create the ledger table when absent."""
    conn.execute(_SCHEMA)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read JSONL entries (empty list when absent)."""
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"malformed audit ledger entry at line {line_number}") from exc
    return entries


def append_event(
    run_id: str,
    event_type: str,
    payload: dict[str, Any] | None = None,
    jsonl_path: str | Path = LEDGER_JSONL,
    db_path: str | Path = LEDGER_DB,
    conn: duckdb.DuckDBPyConnection | None = None,
    signer: Callable[[str], str] | None = None,
    ts: str | None = None,
) -> LedgerEntry:
    """Append one event atomically (JSONL first, then DuckDB)."""
    jsonl = Path(jsonl_path)
    jsonl.parent.mkdir(parents=True, exist_ok=True)
    with _ledger_lock(jsonl):
        existing = _read_jsonl(jsonl)
        if existing:
            seq = int(max(int(e.get("seq", -1)) for e in existing)) + 1
            prev_hash = str(existing[-1].get("entry_hash", GENESIS_PREV_HASH))
        else:
            seq, prev_hash = 0, GENESIS_PREV_HASH
        stamp = ts or _utc_now()
        body = dict(payload or {})
        entry_hash = _hash_entry(prev_hash, seq, stamp, run_id, event_type, body)
        signature = signer(entry_hash) if signer is not None else None
        entry = LedgerEntry(
            seq=seq,
            run_id=run_id,
            ts=stamp,
            event_type=event_type,
            payload=body,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            signature=signature,
        )
        with jsonl.open("a", encoding="utf-8") as handle:
            handle.write(entry.model_dump_json() + "\n")
    close = False
    if conn is None:
        try:
            target = Path(db_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            conn = duckdb.connect(str(target))
            close = True
        except Exception as exc:
            logger.warning("DuckDB ledger unavailable; JSONL is source of truth: %s", exc)
            return entry
    try:
        _ensure_db(conn)
        conn.execute(
            "INSERT INTO ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                entry.seq,
                entry.run_id,
                entry.ts,
                entry.event_type,
                canonical_json(entry.payload),
                entry.prev_hash,
                entry.entry_hash,
                entry.signature or "",
            ],
        )
    except Exception as exc:
        logger.warning("DuckDB ledger write failed; JSONL is source of truth: %s", exc)
    finally:
        if close:
            conn.close()
    return entry


def _rows_from_conn(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Read all ledger rows in seq order."""
    _ensure_db(conn)
    rows = conn.execute(
        "SELECT seq, run_id, ts, event_type, payload_json, prev_hash, entry_hash, signature"
        " FROM ledger ORDER BY seq"
    ).fetchall()
    return [
        {
            "seq": int(r[0]),
            "run_id": str(r[1]),
            "ts": str(r[2]),
            "event_type": str(r[3]),
            "payload": json.loads(r[4] or "{}"),
            "prev_hash": str(r[5]),
            "entry_hash": str(r[6]),
            "signature": str(r[7]) or None,
        }
        for r in rows
    ]


def _verify_rows(rows: list[dict[str, Any]]) -> VerificationResult:
    """Verify a materialized sequence of ledger rows."""
    if not rows:
        return VerificationResult(valid=True, first_broken_seq=None, merkle_root="", entry_count=0)
    expected_seq = 0
    prev = GENESIS_PREV_HASH
    for row in rows:
        recomputed = _hash_entry(
            row["prev_hash"],
            row["seq"],
            row["ts"],
            row["run_id"],
            row["event_type"],
            row["payload"],
        )
        if (
            row["seq"] != expected_seq
            or row["prev_hash"] != prev
            or recomputed != row["entry_hash"]
        ):
            return VerificationResult(
                valid=False,
                first_broken_seq=row["seq"],
                merkle_root=compute_merkle_root([r["entry_hash"] for r in rows]),
                entry_count=len(rows),
            )
        prev = row["entry_hash"]
        expected_seq += 1
    return VerificationResult(
        valid=True,
        first_broken_seq=None,
        merkle_root=compute_merkle_root([r["entry_hash"] for r in rows]),
        entry_count=len(rows),
    )


def sync_duckdb_from_jsonl(
    conn: duckdb.DuckDBPyConnection, jsonl_path: str | Path = LEDGER_JSONL
) -> int:
    """Repair the DuckDB mirror from valid JSONL without changing the source ledger."""
    rows = _read_jsonl(Path(jsonl_path))
    result = _verify_rows(rows)
    if not result.valid:
        raise ValueError("refusing to sync an invalid JSONL audit ledger")
    _ensure_db(conn)
    conn.execute("DELETE FROM ledger")
    for row in rows:
        conn.execute(
            "INSERT INTO ledger VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                row["seq"], row["run_id"], row["ts"], row["event_type"],
                canonical_json(row.get("payload", {})), row["prev_hash"],
                row["entry_hash"], row.get("signature") or "",
            ],
        )
    return len(rows)


def verify_chain(
    conn: duckdb.DuckDBPyConnection,
    jsonl_path: str | Path | None = None,
) -> VerificationResult:
    """Verify a DB ledger, or reconcile it with JSONL when a source path is supplied."""
    db_rows = _rows_from_conn(conn)
    if jsonl_path is not None:
        source = Path(jsonl_path)
    else:
        source = None
    if source is not None and source.exists():
        try:
            source_rows = _read_jsonl(source)
            source_result = _verify_rows(source_rows)
            if not source_result.valid:
                return source_result
            if db_rows != source_rows:
                broken = next(
                    (index for index, (db, truth) in enumerate(zip(db_rows, source_rows)) if db != truth),
                    min(len(db_rows), len(source_rows)),
                )
                return VerificationResult(
                    valid=False,
                    first_broken_seq=int(source_rows[broken]["seq"]) if broken < len(source_rows) else broken,
                    merkle_root=compute_merkle_root([str(r["entry_hash"]) for r in source_rows]),
                    entry_count=len(source_rows),
                )
            return source_result
        except (OSError, ValueError, TypeError, KeyError):
            return VerificationResult(valid=False, first_broken_seq=0, entry_count=len(source_rows) if "source_rows" in locals() else 0)
    return _verify_rows(db_rows)
