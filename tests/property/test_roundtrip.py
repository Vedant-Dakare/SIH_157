"""Property tests: canonical round-trip serialisation."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st
from satsa.canonical.models import Alert, Case, Investigation

UTC = UTC
_SEVERITIES = st.sampled_from(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN"])
_STATUSES = st.sampled_from(["OPEN", "ACKED", "TRIAGED", "CLOSED", "REOPENED"])
_AWARE_DT = st.datetimes(timezones=st.just(UTC), min_value=datetime(2020, 1, 1, tzinfo=UTC))
_HEX64 = st.from_regex(r"\A[0-9a-f]{64}\Z", fullmatch=True)


def _digest(text: str) -> str:
    """Hash helper producing deterministic audit hashes."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


@given(
    alert_id=st.text(min_size=1, max_size=20),
    asset_id=st.text(min_size=1, max_size=20),
    severity=_SEVERITIES,
    status=_STATUSES,
    detected=_AWARE_DT,
    analyst=_HEX64,
)
@settings(max_examples=200)
def test_alert_roundtrip(alert_id, asset_id, severity, status, detected, analyst) -> None:
    """Any valid Alert survives model_validate(model_dump())."""
    original = Alert(
        alert_id=alert_id,
        asset_id=asset_id,
        title="t",
        severity_raw=severity,
        severity_norm=severity,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        detected_ts=detected,
        analyst_id=analyst,  # type: ignore[arg-type]
        ingest_ts=detected,
        source_file_hash=_digest(alert_id),
        record_hash=_digest(asset_id),
    )
    assert Alert.model_validate(original.model_dump()) == original


@given(
    case_id=st.text(min_size=1, max_size=20),
    severity=_SEVERITIES,
    opened=_AWARE_DT,
    analyst=_HEX64,
)
@settings(max_examples=200)
def test_case_roundtrip(case_id, severity, opened, analyst) -> None:
    """Any valid Case survives model_validate(model_dump())."""
    original = Case(
        case_id=case_id,
        severity_norm=severity,  # type: ignore[arg-type]
        open_ts=opened,
        analyst_id=analyst,  # type: ignore[arg-type]
        ingest_ts=opened,
        source_file_hash=_digest(case_id),
        record_hash=_digest(case_id + "r"),
    )
    assert Case.model_validate(original.model_dump()) == original


@given(case_id=st.text(min_size=1, max_size=20), opened=_AWARE_DT, analyst=_HEX64)
@settings(max_examples=200)
def test_investigation_roundtrip(case_id, opened, analyst) -> None:
    """Any valid Investigation survives model_validate(model_dump())."""
    original = Investigation(
        investigation_id="inv-" + _digest(case_id),
        case_id=case_id,
        analyst_id=analyst,  # type: ignore[arg-type]
        triage_start_ts=opened,
        ingest_ts=opened,
        source_file_hash=_digest(case_id),
        record_hash=_digest(case_id + "inv"),
    )
    assert Investigation.model_validate(original.model_dump()) == original
