"""Merkle trees over ledger hashes plus signed run manifests."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
from pydantic import BaseModel, Field

from satsa.audit.hashing import hmac_sign
from satsa.paths import from_root

MANIFEST_DIR = from_root("data", "warehouse", "runs")


class RunManifest(BaseModel):
    """Signed portable record of one pipeline run."""

    run_id: str = Field(min_length=1)
    created_at: str = ""
    window_start: str = ""
    window_end: str = ""
    entity_count: int = 0
    finding_count: int = 0
    first_seq: int = 0
    last_seq: int = 0
    entry_count: int = 0
    merkle_root: str = ""
    ledger_hashes: list[str] = Field(default_factory=list)
    thresholds_hash: str = ""
    signals_version: str = ""
    settings_snapshot: dict[str, Any] = Field(default_factory=dict)
    signature: str = ""


def compute_merkle_root(entry_hashes: list[str]) -> str:
    """Binary Merkle root over hex entry hashes (duplicate last leaf when odd).

    Deterministic: same inputs always yield the same root.
    """
    if not entry_hashes:
        return hashlib.sha256(b"").hexdigest()
    level = [h.lower() for h in entry_hashes]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level = [*level, level[-1]]
        nxt: list[str] = []
        for i in range(0, len(level), 2):
            pair = bytes.fromhex(level[i]) + bytes.fromhex(level[i + 1])
            nxt.append(hashlib.sha256(pair).hexdigest())
        level = nxt
    return level[0]


def _thresholds_hash(config_dir: str | Path = "configs") -> str:
    """SHA-256 over thresholds.yaml bytes (empty when absent)."""
    path = Path(config_dir)
    if not path.is_absolute():
        path = from_root(*path.parts)
    path = path / "thresholds.yaml"
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_run_manifest(
    run_id: str,
    conn: duckdb.DuckDBPyConnection,
    settings: Any,
    manifest_dir: str | Path = MANIFEST_DIR,
    config_dir: str | Path = "configs",
) -> RunManifest:
    """Collect run scope, chain hashes and HMAC-sign the manifest."""
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS ledger (seq INTEGER PRIMARY KEY, run_id VARCHAR,"
            " ts VARCHAR, event_type VARCHAR, payload_json VARCHAR, prev_hash VARCHAR,"
            " entry_hash VARCHAR, signature VARCHAR)"
        )
        rows = conn.execute(
            "SELECT seq, ts, payload_json, entry_hash FROM ledger"
            " WHERE run_id = ? ORDER BY seq",
            [run_id],
        ).fetchall()
    except Exception:
        rows = []
    hashes = [str(r[3]) for r in rows]
    findings = 0
    windows: list[str] = []
    for r in rows:
        try:
            payload = json.loads(r[2] or "{}")
        except ValueError:
            payload = {}
        if "finding_id" in payload:
            findings += 1
        if payload.get("window"):
            windows.append(str(payload["window"]))
    body = RunManifest(
        run_id=run_id,
        created_at=datetime.now(UTC).isoformat(),
        window_start=min(windows) if windows else "",
        window_end=max(windows) if windows else "",
        entity_count=len({json.loads(r[2] or "{}").get("entity_id", "") for r in rows}),
        finding_count=findings,
        first_seq=int(rows[0][0]) if rows else 0,
        last_seq=int(rows[-1][0]) if rows else 0,
        entry_count=len(rows),
        merkle_root=compute_merkle_root(hashes),
        ledger_hashes=hashes,
        thresholds_hash=_thresholds_hash(config_dir),
        signals_version="phase2-registry",
        settings_snapshot={"manifest_key_set": bool(getattr(settings, "manifest_key", ""))},
    )
    key = str(getattr(settings, "manifest_key", "") or "")
    payload = body.model_dump_json(exclude={"signature"})
    body.signature = hmac_sign(payload, key) if key else ""
    target = Path(manifest_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{run_id}.manifest.json").write_text(
        body.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    return body
