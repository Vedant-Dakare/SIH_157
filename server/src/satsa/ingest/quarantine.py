"""Quarantine ledger: JSONL append plus data-quality scorecard."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from satsa.errors import SatsaQuarantineError


class QuarantineRecord(BaseModel):
    """Single quarantined row matching the Master Section M schema."""

    cse_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    record_index: int = Field(ge=0)
    reason_code: str = Field(min_length=1)
    details: str = Field(default="")
    raw_record: dict[str, str] = Field(default_factory=dict)
    quarantined_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DataQualityScorecard(BaseModel):
    """Aggregate data-quality outcome for one CSE ingest."""

    cse_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    total_rows: int = Field(ge=0)
    valid_rows: int = Field(ge=0)
    quarantined_rows: int = Field(ge=0)
    quarantine_rate: float = Field(ge=0.0, le=1.0)
    reason_code_counts: dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def _record_fingerprint(record: QuarantineRecord) -> str:
    """Compute a stable fingerprint used for idempotent appends."""
    payload = json.dumps(
        {
            "cse_id": record.cse_id,
            "run_id": record.run_id,
            "record_index": record.record_index,
            "reason_code": record.reason_code,
            "raw_record": record.raw_record,
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def append_quarantine(
    records: list[QuarantineRecord],
    cse_id: str,
    run_id: str,
    data_root: str | Path = "data",
) -> DataQualityScorecard:
    """Append quarantine records to JSONL without overwriting existing rows.

    Args:
        records: Quarantine records from this ingest batch.
        cse_id: CSE identifier scoping the quarantine file.
        run_id: Run identifier for idempotency.
        data_root: Data root containing the quarantine/ directory.

    Returns:
        DataQualityScorecard summarising valid versus quarantined rows.

    Raises:
        SatsaQuarantineError: Only when the quarantine write itself fails.
    """
    quarantine_dir = Path(data_root) / "quarantine"
    try:
        quarantine_dir.mkdir(parents=True, exist_ok=True)
        target = quarantine_dir / f"{cse_id}.jsonl"
        existing: set[str] = set()
        if target.exists():
            with target.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                        fingerprint = payload.get("_fingerprint", "")
                        if fingerprint:
                            existing.add(fingerprint)
                    except Exception:
                        continue
        with target.open("a", encoding="utf-8") as handle:
            for record in records:
                fingerprint = _record_fingerprint(record)
                if fingerprint in existing:
                    continue
                payload = record.model_dump(mode="json")
                payload["_fingerprint"] = fingerprint
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
                existing.add(fingerprint)
        reason_counts: dict[str, int] = {}
        for record in records:
            reason_counts[record.reason_code] = reason_counts.get(record.reason_code, 0) + 1
        quarantined_rows = len(records)
        total_rows = quarantined_rows
        valid_rows = 0
        rate = 0.0
        if quarantined_rows > 0:
            rate = 1.0
        return DataQualityScorecard(
            cse_id=cse_id,
            run_id=run_id,
            total_rows=total_rows,
            valid_rows=valid_rows,
            quarantined_rows=quarantined_rows,
            quarantine_rate=rate,
            reason_code_counts=reason_counts,
            generated_at=datetime.now(UTC),
        )
    except SatsaQuarantineError:
        raise
    except Exception as exc:
        raise SatsaQuarantineError(f"quarantine write failed for {cse_id}: {exc}") from exc


def build_scorecard(
    cse_id: str,
    run_id: str,
    total_rows: int,
    valid_rows: int,
    quarantined: list[QuarantineRecord],
) -> DataQualityScorecard:
    """Build a scorecard when total and valid counts are known externally.

    Args:
        cse_id: CSE identifier.
        run_id: Run identifier.
        total_rows: Total rows seen.
        valid_rows: Rows passing validation.
        quarantined: Quarantine records for reason-code counts.

    Returns:
        Populated DataQualityScorecard.
    """
    quarantined_rows = len(quarantined)
    counts: dict[str, int] = {}
    for record in quarantined:
        counts[record.reason_code] = counts.get(record.reason_code, 0) + 1
    rate = 0.0
    if total_rows > 0:
        rate = float(quarantined_rows) / float(total_rows)
    return DataQualityScorecard(
        cse_id=cse_id,
        run_id=run_id,
        total_rows=int(total_rows),
        valid_rows=int(valid_rows),
        quarantined_rows=int(quarantined_rows),
        quarantine_rate=float(rate),
        reason_code_counts=counts,
        generated_at=datetime.now(UTC),
    )
