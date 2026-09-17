"""Evidence retrieval: materialize finding bundles into DuckDB, read them back.

Counter-evidence is mandatory: always present, or explicitly absent with a
reason (supervisory fairness). evidence_id is stable SHA-256 over
signal_id + entity_id + window + sorted row ids.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
from pydantic import BaseModel, Field

from satsa.signals.base import _evidence_id

EVIDENCE_DB = Path("data/warehouse/evidence.duckdb")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence (
    finding_id VARCHAR PRIMARY KEY,
    signal_id VARCHAR,
    entity_id VARCHAR,
    window_label VARCHAR,
    evidence_id VARCHAR,
    supporting_json VARCHAR,
    counter_json VARCHAR,
    counter_absent_reason VARCHAR,
    cohort_json VARCHAR,
    retrieved_at VARCHAR
)
"""


def _connect(path: str | Path = EVIDENCE_DB) -> duckdb.DuckDBPyConnection:
    """Open the evidence database, creating schema on demand."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(target))
    conn.execute(_SCHEMA)
    return conn


def _row_ids(rows: list[dict[str, Any]]) -> list[str]:
    """Collect stable row ids from evidence rows."""
    ids: list[str] = []
    for i, row in enumerate(rows):
        if isinstance(row, dict):
            ids.append(str(row.get("case_id", row.get("alert_id", row.get("asset_id", i)))))
        else:
            ids.append(str(i))
    return ids


class StoredEvidence(BaseModel):
    """Evidence bundle as retrieved from DuckDB."""

    finding_id: str = Field(min_length=1)
    evidence_id: str = ""
    supporting_rows: list[dict[str, Any]] = Field(default_factory=list)
    counter_rows: list[dict[str, Any]] = Field(default_factory=list)
    counter_rows_absent_reason: str = ""
    cohort_comparison: dict[str, Any] = Field(default_factory=dict)
    retrieved_at: str = ""


def materialize(
    finding_id: str,
    signal_id: str,
    entity_id: str,
    window: str,
    bundle: Any,
    conn: duckdb.DuckDBPyConnection | None = None,
    db_path: str | Path = EVIDENCE_DB,
) -> StoredEvidence:
    """Store one finding's evidence rows; returns the stored record."""
    close = False
    if conn is None:
        conn = _connect(db_path)
        close = True
    try:
        supporting = [dict(r) for r in (getattr(bundle, "supporting_rows", []) or [])]
        counter = [dict(r) for r in (getattr(bundle, "counter_rows", []) or [])]
        reason = str(getattr(bundle, "counter_none_reason", "") or "")
        if not counter and not reason:
            reason = "no counter-evidence found for this signal type"
        cohort = dict(getattr(bundle, "cohort_comparison", {}) or {})
        evidence_id = str(getattr(bundle, "evidence_id", "") or "")
        if not evidence_id:
            evidence_id = _evidence_id(signal_id, entity_id, window, _row_ids(supporting))
        record = StoredEvidence(
            finding_id=finding_id,
            evidence_id=evidence_id,
            supporting_rows=supporting,
            counter_rows=counter,
            counter_rows_absent_reason="" if counter else reason,
            cohort_comparison=cohort,
            retrieved_at=datetime.now(UTC).isoformat(),
        )
        conn.execute("DELETE FROM evidence WHERE finding_id = ?", [finding_id])
        conn.execute(
            "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                finding_id,
                signal_id,
                entity_id,
                window,
                record.evidence_id,
                json.dumps(supporting, default=str),
                json.dumps(counter, default=str),
                record.counter_rows_absent_reason,
                json.dumps(cohort, default=str),
                record.retrieved_at,
            ],
        )
        return record
    finally:
        if close:
            conn.close()


def retrieve_evidence(
    finding_id: str,
    conn: duckdb.DuckDBPyConnection,
) -> StoredEvidence:
    """Fetch one finding's evidence; KeyError when the finding is unknown."""
    rows = conn.execute(
        "SELECT finding_id, evidence_id, supporting_json, counter_json,"
        " counter_absent_reason, cohort_json, retrieved_at"
        " FROM evidence WHERE finding_id = ?",
        [finding_id],
    ).fetchall()
    if not rows:
        raise KeyError(f"finding not found: {finding_id}")
    fid, eid, sup, cnt, reason, cohort, retrieved = rows[0]
    return StoredEvidence(
        finding_id=str(fid),
        evidence_id=str(eid),
        supporting_rows=json.loads(sup or "[]"),
        counter_rows=json.loads(cnt or "[]"),
        counter_rows_absent_reason=str(reason or ""),
        cohort_comparison=json.loads(cohort or "{}"),
        retrieved_at=str(retrieved or ""),
    )


def stable_evidence_id(
    signal_id: str, entity_id: str, window: str, rows: list[dict[str, Any]]
) -> str:
    """Recompute the stable evidence hash for verification."""
    return _evidence_id(signal_id, entity_id, window, _row_ids(rows))


def find_finding(
    finding_id: str,
    synthetic_root: str | Path = "data/synthetic",
    run_id: str = "phase2-run",
    seed: int = 42,
) -> tuple[str, Any, Any, Any]:
    """Resolve any finding id to (entity_id, result, bundle, signal).

    Scans corpus entities and matches computed finding ids. Raises KeyError
    with an explicit message when no finding matches.
    """
    from satsa.signals.registry import get_signal
    from satsa.signals.runner import build_all_features, list_entities, run_entity

    features = build_all_features(synthetic_root)
    for entity_id in list_entities(synthetic_root):
        results = run_entity(entity_id, features, synthetic_root, run_id)
        for signal_id, result in results.items():
            if getattr(result, "finding_id", "") != finding_id:
                continue
            signal = get_signal(signal_id)
            bundle = None
            if signal is not None:
                try:
                    bundle = signal.evidence(result)
                except Exception:
                    bundle = None
            _ = seed
            return entity_id, result, bundle, signal
    raise KeyError(f"finding not found: {finding_id}")
