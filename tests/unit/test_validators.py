"""Unit tests for post-mapping validators."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

from satsa.ingest.validators import validate_records

UTC = UTC


def _analyst() -> str:
    """Return a valid hashed analyst id."""
    return hashlib.sha256(b"validator-test").hexdigest()


def _base_alert(**overrides) -> dict:
    """Build a minimal valid alert dict."""
    now = datetime.now(UTC)
    record = {
        "alert_id": "a1",
        "asset_id": "asset1",
        "title": "suspicious",
        "severity_raw": "P1",
        "severity_norm": "CRITICAL",
        "status": "OPEN",
        "detected_ts": now - timedelta(hours=1),
        "ack_ts": now,
        "ingest_ts": now,
        "source_file_hash": "sfh",
        "record_hash": "rh",
        "analyst_id": _analyst(),
    }
    record.update(overrides)
    return record


def test_close_before_detected_quarantined() -> None:
    """close_ts earlier than detected_ts yields TIMESTAMP_MONOTONICITY_VIOLATION."""
    now = datetime.now(UTC)
    record = _base_alert(detected_ts=now, close_ts=now - timedelta(hours=1))
    valid, quarantined = validate_records([record], cse_id="cse_alpha", run_id="r1")
    assert valid == []
    assert quarantined[0].reason_code == "TIMESTAMP_MONOTONICITY_VIOLATION"


def test_bad_severity_enum_violation() -> None:
    """severity_norm BANANA yields ENUM_VIOLATION."""
    valid, quarantined = validate_records([_base_alert(severity_norm="BANANA")])
    assert valid == []
    assert quarantined[0].reason_code == "ENUM_VIOLATION"


def test_valid_record_passes() -> None:
    """Valid record passes with empty quarantine list."""
    valid, quarantined = validate_records([_base_alert()], asset_ids={"asset1"})
    assert len(valid) == 1
    assert quarantined == []


def test_referential_integrity_failure() -> None:
    """Unknown asset_id yields REFERENTIAL_INTEGRITY_VIOLATION."""
    valid, quarantined = validate_records([_base_alert()], asset_ids={"other-asset"})
    assert valid == []
    assert quarantined[0].reason_code == "REFERENTIAL_INTEGRITY_VIOLATION"


def test_future_dated_quarantined() -> None:
    """Future-dated timestamp yields TIMESTAMP_MONOTONICITY_VIOLATION."""
    future = datetime.now(UTC) + timedelta(days=2)
    valid, quarantined = validate_records([_base_alert(detected_ts=future, ack_ts=future)])
    assert valid == []
    assert quarantined[0].reason_code == "TIMESTAMP_MONOTONICITY_VIOLATION"


def test_non_utf8_sanitised_not_crashed() -> None:
    """Non-UTF8 content is sanitised without crashing."""
    record = _base_alert(title=b"bad\xffbytes")  # type: ignore[dict-item]
    valid, quarantined = validate_records([record], asset_ids={"asset1"})
    assert len(valid) + len(quarantined) == 1
