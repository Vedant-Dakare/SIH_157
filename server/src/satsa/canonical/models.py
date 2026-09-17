"""Canonical Pydantic v2 models. No business logic lives here."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

HashedAnalystId = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
SeverityNorm = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN"]
AlertStatus = Literal["OPEN", "ACKED", "TRIAGED", "CLOSED", "REOPENED"]
CaseStatus = Literal["OPEN", "ACKED", "TRIAGED", "CLOSED", "REOPENED"]
DispositionCode = Literal["TRUE_POSITIVE", "FALSE_POSITIVE", "BENIGN", "DUPLICATE", "INCONCLUSIVE"]
Criticality = Literal["low", "medium", "high", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
Environment = Literal["production", "staging", "development"]
OsFamily = Literal["linux", "windows", "macos"]
Tier = Literal["T1", "T2", "T3"]


def _ensure_utc(value: datetime | None) -> datetime | None:
    """Validate a datetime is timezone-aware and normalise it to UTC."""
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware (UTC required)")
    return value.astimezone(UTC)


class AuditMixin(BaseModel):
    """Shared audit fields required on every canonical record."""

    ingest_ts: datetime
    source_file_hash: str = Field(min_length=1)
    record_hash: str = Field(min_length=1)

    _utc_ingest = field_validator("ingest_ts", mode="before")(
        lambda v: _ensure_utc(v) if isinstance(v, datetime) else v
    )

    @field_validator("ingest_ts")
    @classmethod
    def _ingest_must_be_utc(cls, value: datetime) -> datetime:
        """Ensure ingest_ts is timezone-aware UTC."""
        result = _ensure_utc(value)
        assert result is not None
        return result


class InvestigationStep(BaseModel):
    """Single step nested inside an Investigation."""

    step_id: str = Field(min_length=1)
    timestamp: datetime
    action: str = Field(min_length=1)
    notes: str = Field(default="")

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, value: object) -> object:
        """Allow datetime passthrough; parsing happens before UTC check."""
        return value

    @field_validator("timestamp")
    @classmethod
    def _timestamp_must_be_utc(cls, value: datetime) -> datetime:
        """Ensure step timestamp is timezone-aware UTC."""
        result = _ensure_utc(value)
        assert result is not None
        return result


class Alert(AuditMixin):
    """Canonical alert record."""

    alert_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    severity_raw: str = Field(min_length=1)
    severity_norm: SeverityNorm
    status: AlertStatus = "OPEN"
    category: str = Field(default="OTHER")
    analyst_id: HashedAnalystId | None = None
    detected_ts: datetime
    ack_ts: datetime | None = None
    source: str = Field(default="edr")

    @field_validator("detected_ts", "ack_ts", mode="before")
    @classmethod
    def _parse_optional_dt(cls, value: object) -> object:
        """Passthrough for datetime parsing."""
        return value

    @field_validator("detected_ts", "ack_ts")
    @classmethod
    def _must_be_utc(cls, value: datetime | None) -> datetime | None:
        """Ensure alert timestamps are timezone-aware UTC."""
        return _ensure_utc(value)


class Asset(AuditMixin):
    """Canonical asset inventory record."""

    asset_id: str = Field(min_length=1)
    hostname: str = Field(default="")
    criticality: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    os_family: str = Field(min_length=1)
    internet_facing: bool = False
    gap_flag: bool = False


class Case(AuditMixin):
    """Canonical case record aggregating one or more alerts."""

    case_id: str = Field(min_length=1)
    asset_id: str | None = None
    alert_ids: list[str] = Field(default_factory=list)
    severity_norm: SeverityNorm
    status: CaseStatus = "OPEN"
    disposition_code: DispositionCode | None = None
    analyst_id: HashedAnalystId | None = None
    tier: Tier = "T1"
    detected_ts: datetime | None = None
    ack_ts: datetime | None = None
    open_ts: datetime
    close_ts: datetime | None = None
    reopen_count: int = Field(default=0, ge=0)

    @field_validator("detected_ts", "ack_ts", "open_ts", "close_ts", mode="before")
    @classmethod
    def _parse_optional_dt(cls, value: object) -> object:
        """Passthrough for datetime parsing."""
        return value

    @field_validator("detected_ts", "ack_ts", "open_ts", "close_ts")
    @classmethod
    def _must_be_utc(cls, value: datetime | None) -> datetime | None:
        """Ensure case timestamps are timezone-aware UTC."""
        return _ensure_utc(value)


class Investigation(AuditMixin):
    """Canonical investigation record linked to a case."""

    investigation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    analyst_id: HashedAnalystId | None = None
    detected_ts: datetime | None = None
    ack_ts: datetime | None = None
    triage_start_ts: datetime | None = None
    triage_end_ts: datetime | None = None
    close_ts: datetime | None = None
    notes: str = Field(default="")
    steps: list[InvestigationStep] = Field(default_factory=list)

    @field_validator(
        "detected_ts", "ack_ts", "triage_start_ts", "triage_end_ts", "close_ts", mode="before"
    )
    @classmethod
    def _parse_optional_dt(cls, value: object) -> object:
        """Passthrough for datetime parsing."""
        return value

    @field_validator("detected_ts", "ack_ts", "triage_start_ts", "triage_end_ts", "close_ts")
    @classmethod
    def _must_be_utc(cls, value: datetime | None) -> datetime | None:
        """Ensure investigation timestamps are timezone-aware UTC."""
        return _ensure_utc(value)


class Escalation(AuditMixin):
    """Canonical escalation record linked to a case."""

    escalation_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    from_tier: Tier = "T1"
    to_tier: Tier = "T2"
    escalated_ts: datetime | None = None

    @field_validator("escalated_ts", mode="before")
    @classmethod
    def _parse_optional_dt(cls, value: object) -> object:
        """Passthrough for datetime parsing."""
        return value

    @field_validator("escalated_ts")
    @classmethod
    def _must_be_utc(cls, value: datetime | None) -> datetime | None:
        """Ensure escalation timestamp is timezone-aware UTC."""
        return _ensure_utc(value)


class Telemetry(AuditMixin):
    """Canonical telemetry observation for coverage analysis."""

    telemetry_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    observed_ts: datetime

    @field_validator("observed_ts", mode="before")
    @classmethod
    def _parse_optional_dt(cls, value: object) -> object:
        """Passthrough for datetime parsing."""
        return value

    @field_validator("observed_ts")
    @classmethod
    def _must_be_utc(cls, value: datetime) -> datetime:
        """Ensure observation timestamp is timezone-aware UTC."""
        result = _ensure_utc(value)
        assert result is not None
        return result
