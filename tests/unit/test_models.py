"""Unit tests for canonical Pydantic models."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from satsa.canonical.models import (
    Alert,
    Asset,
    Case,
    Escalation,
    Investigation,
    InvestigationStep,
    Telemetry,
)

UTC = UTC


def _analyst(label: str = "analyst-test") -> str:
    """Return a valid hashed analyst identifier."""
    return hashlib.sha256(label.encode()).hexdigest()


def _audit() -> dict:
    """Return valid audit fields."""
    return {
        "ingest_ts": datetime.now(UTC),
        "source_file_hash": "abc123",
        "record_hash": "def456",
    }


def test_every_canonical_model_instantiates() -> None:
    """Every canonical model instantiates with valid data."""
    now = datetime.now(UTC)
    assert Alert(
        alert_id="a1",
        asset_id="asset1",
        title="t",
        severity_raw="P1",
        severity_norm="CRITICAL",
        detected_ts=now,
        **_audit(),
    )
    assert Asset(
        asset_id="asset1",
        criticality="high",
        environment="production",
        os_family="linux",
        **_audit(),
    )
    assert Case(
        case_id="c1",
        severity_norm="HIGH",
        open_ts=now,
        **_audit(),
    )
    assert Investigation(investigation_id="i1", case_id="c1", **_audit())
    assert Escalation(escalation_id="e1", case_id="c1", **_audit())
    assert Telemetry(
        telemetry_id="t1", asset_id="asset1", source="edr", observed_ts=now, **_audit()
    )
    assert InvestigationStep(step_id="s1", timestamp=now, action="review")


def test_missing_required_field_raises() -> None:
    """Missing required field raises ValidationError."""
    with pytest.raises(ValidationError):
        Alert(asset_id="a", title="t", severity_raw="P1", severity_norm="HIGH", **_audit())  # type: ignore[call-arg]


def test_audit_fields_required() -> None:
    """Audit fields are required on every model."""
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        Alert(
            alert_id="a1",
            asset_id="asset1",
            title="t",
            severity_raw="P1",
            severity_norm="HIGH",
            detected_ts=now,
        )  # type: ignore[call-arg]


def test_datetime_enforces_utc() -> None:
    """Naive datetimes are rejected; aware datetimes are normalised to UTC."""
    naive = datetime.now()
    with pytest.raises(ValidationError):
        Alert(
            alert_id="a1",
            asset_id="asset1",
            title="t",
            severity_raw="P1",
            severity_norm="HIGH",
            detected_ts=naive,  # type: ignore[arg-type]
            **_audit(),
        )


def test_analyst_id_accepts_only_hashed() -> None:
    """analyst_id accepts only 64-char hex strings."""
    now = datetime.now(UTC)
    valid = _analyst()
    alert = Alert(
        alert_id="a1",
        asset_id="asset1",
        title="t",
        severity_raw="P1",
        severity_norm="HIGH",
        detected_ts=now,
        analyst_id=valid,  # type: ignore[arg-type]
        **_audit(),
    )
    assert alert.analyst_id == valid
    with pytest.raises(ValidationError):
        Alert(
            alert_id="a1",
            asset_id="asset1",
            title="t",
            severity_raw="P1",
            severity_norm="HIGH",
            detected_ts=now,
            analyst_id="ANON_A1",  # type: ignore[arg-type]
            **_audit(),
        )
