"""Post-mapping validation producing valid records plus quarantine records."""

from __future__ import annotations

import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import ValidationError

logger = structlog.get_logger(__name__)

_REASON_MONOTONICITY = "TIMESTAMP_MONOTONICITY_VIOLATION"
_REASON_ENUM = "ENUM_VIOLATION"
_REASON_REFERENTIAL = "REFERENTIAL_INTEGRITY_VIOLATION"
_REASON_REQUIRED = "REQUIRED_FIELD_MISSING"
_REASON_SCHEMA = "SCHEMA_VIOLATION"

_CSV_PREFIXES = ("=", "+", "-", "@")


def _load_future_tolerance_seconds(config_dir: str | Path = "configs") -> int:
    """Load future-timestamp tolerance from thresholds.yaml."""
    path = Path(config_dir) / "thresholds.yaml"
    if not path.exists():
        return 60
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    try:
        return int(data.get("timestamp_future_tolerance_seconds", 60))
    except Exception:
        return 60


def _sanitise_value(value: Any) -> Any:
    """Sanitise non-UTF8 content and CSV injection prefixes without crashing."""
    if isinstance(value, bytes | bytearray):
        warnings.warn("non-UTF8 bytes sanitised to string", UserWarning, stacklevel=3)
        return bytes(value).decode("utf-8", errors="replace")
    if isinstance(value, str):
        cleaned = value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        if cleaned != value:
            warnings.warn("non-UTF8 content sanitised", UserWarning, stacklevel=3)
        if cleaned.startswith(_CSV_PREFIXES):
            stripped = cleaned.lstrip("=+-@\t\r ")
            warnings.warn(f"CSV injection pattern stripped: {value!r}", UserWarning, stacklevel=3)
            logger.warning("csv_injection_stripped", original=value)
            return stripped
        return cleaned
    return value


def _sanitise_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a sanitised copy of a record."""
    return {key: _sanitise_value(val) for key, val in record.items()}


def _check_monotonicity(record: dict[str, Any]) -> str | None:
    """Return a reason code when timestamp monotonicity is violated."""

    def _get(name: str) -> datetime | None:
        val = record.get(name)
        return val if isinstance(val, datetime) else None

    detected = _get("detected_ts")
    ack = _get("ack_ts")
    triage_start = _get("triage_start_ts")
    triage_end = _get("triage_end_ts")
    close = _get("close_ts")
    if detected is not None and ack is not None and ack < detected:
        return _REASON_MONOTONICITY
    if ack is not None and triage_start is not None and triage_start < ack:
        return _REASON_MONOTONICITY
    if triage_start is not None and triage_end is not None and triage_end < triage_start:
        return _REASON_MONOTONICITY
    if detected is not None and close is not None and close < detected:
        return _REASON_MONOTONICITY
    return None


def _check_future(record: dict[str, Any], now: datetime, tolerance_seconds: int) -> bool:
    """Return True when any timestamp lies beyond now plus tolerance."""
    for key in ("detected_ts", "ack_ts", "triage_start_ts", "triage_end_ts", "close_ts", "open_ts"):
        val = record.get(key)
        if isinstance(val, datetime):
            candidate = val
            if candidate.tzinfo is None:
                candidate = candidate.replace(tzinfo=UTC)
            limit = now.timestamp() + float(tolerance_seconds)
            if candidate.timestamp() > limit:
                return True
    return False


def _model_for_type(record_type: str) -> Any:
    """Resolve the canonical model class for a record type string."""
    from satsa.canonical.models import Alert, Asset, Case, Escalation, Investigation, Telemetry

    mapping = {
        "alert": Alert,
        "alerts": Alert,
        "asset": Asset,
        "assets": Asset,
        "case": Case,
        "cases": Case,
        "investigation": Investigation,
        "investigations": Investigation,
        "escalation": Escalation,
        "escalations": Escalation,
        "telemetry": Telemetry,
    }
    return mapping.get(record_type.lower(), Alert)


def validate_records(
    records: list[dict[str, Any]],
    record_type: str = "alert",
    asset_ids: set[str] | None = None,
    cse_id: str = "unknown",
    run_id: str = "unknown",
    now: datetime | None = None,
    config_dir: str | Path = "configs",
) -> tuple[list[dict[str, Any]], list[Any]]:
    """Validate canonical dicts, splitting them into valid and quarantined.

    Args:
        records: Candidate canonical dicts (already mapped).
        record_type: Logical type used to select the canonical model.
        asset_ids: Known asset identifiers for referential integrity.
        cse_id: CSE identifier stamped onto quarantine records.
        run_id: Run identifier stamped onto quarantine records.
        now: Reference time for future-dated checks (defaults to UTC now).
        config_dir: Directory containing thresholds.yaml.

    Returns:
        Tuple of (valid_records, quarantine_records).
    """
    from satsa.ingest.quarantine import QuarantineRecord

    current = now or datetime.now(UTC)
    tolerance = _load_future_tolerance_seconds(config_dir)
    model_cls = _model_for_type(record_type)
    valid: list[dict[str, Any]] = []
    quarantined: list[Any] = []
    for index, raw in enumerate(records):
        try:
            record = _sanitise_record(dict(raw))
        except Exception as exc:  # noqa: BLE001 - sanitisation must not crash
            logger.warning("sanitise_failed", error=str(exc))
            record = {}
        reason: str | None = None
        details = ""
        if _check_future(record, current, tolerance):
            reason = _REASON_MONOTONICITY
            details = "future-dated timestamp beyond tolerance"
        if reason is None:
            reason = _check_monotonicity(record)
            if reason is not None:
                details = "timestamp monotonicity violated"
        if reason is None and asset_ids is not None and "asset_id" in record:
            asset = record.get("asset_id")
            if isinstance(asset, str) and asset not in asset_ids:
                reason = _REASON_REFERENTIAL
                details = f"asset_id {asset!r} not in inventory"
        if reason is None:
            try:
                model_cls.model_validate(record)
            except ValidationError as exc:
                message = str(exc).lower()
                enum_markers = ("literal_error", "enum", "literal", "severity_norm", "status")
                disposition_markers = ("disposition_code", "tier")
                if any(marker in message for marker in enum_markers + disposition_markers):
                    reason = _REASON_ENUM
                elif "missing" in message or "required" in message:
                    reason = _REASON_REQUIRED
                else:
                    reason = _REASON_SCHEMA
                details = str(exc)[:500]
        if reason is None:
            valid.append(record)
        else:
            quarantined.append(
                QuarantineRecord(
                    cse_id=cse_id,
                    run_id=run_id,
                    record_index=index,
                    reason_code=reason,
                    details=details,
                    raw_record={str(k): str(v)[:500] for k, v in record.items()},
                )
            )
    return valid, quarantined


def validate_batch(
    records: list[dict[str, Any]],
    asset_ids: set[str] | None = None,
    cse_id: str = "unknown",
    run_id: str = "unknown",
    record_type: str = "alert",
) -> tuple[list[dict[str, Any]], list[Any]]:
    """Validate a batch of records with default time and config locations."""
    return validate_records(
        records,
        record_type=record_type,
        asset_ids=asset_ids,
        cse_id=cse_id,
        run_id=run_id,
    )
