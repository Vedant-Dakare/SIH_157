"""Pydantic response models for every API endpoint."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    """Evidence linkage for a payload."""

    evidence_id: str = ""


class Envelope(BaseModel):
    """Fields present on every response."""

    run_id: str = ""
    generated_at: str = ""


class HealthResponse(Envelope):
    """GET /health."""

    status: str = "ok"
    pipeline_version: str = "phase6"


class RunInfo(BaseModel):
    """One known run id."""

    run_id: str = ""


class RunsResponse(Envelope):
    """GET /runs."""

    runs: list[str] = Field(default_factory=list)


class ManifestResponse(Envelope):
    """GET /runs/{run_id}/manifest."""

    manifest: dict[str, Any] = Field(default_factory=dict)


class EntitySummary(BaseModel):
    """One row of the entity list."""

    entity_id: str = ""
    band: str = "LOW"
    sector: str = "unknown"
    overall_score: float = 0.0
    confidence: str = "LOW"


class EntitiesResponse(Envelope):
    """GET /entities."""

    entities: list[EntitySummary] = Field(default_factory=list)


class EntityDetailResponse(Envelope):
    """GET /entities/{entity_id}."""

    entity: dict[str, Any] = Field(default_factory=dict)


class FindingSummary(BaseModel):
    """One finding in a list."""

    finding_id: str = ""
    entity_id: str = ""
    signal_id: str = ""
    severity: str = "INFO"
    confidence: str = "LOW"


class EntityFindingsResponse(Envelope):
    """GET /entities/{entity_id}/findings."""

    findings: list[FindingSummary] = Field(default_factory=list)


class FindingDetailResponse(Envelope):
    """GET /findings/{finding_id}."""

    finding: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance = Field(default_factory=Provenance)


class EvidenceResponse(Envelope):
    """GET /findings/{finding_id}/evidence."""

    supporting_rows: list[dict[str, Any]] = Field(default_factory=list)
    counter_rows: list[dict[str, Any]] = Field(default_factory=list)
    counter_rows_absent_reason: str = ""
    provenance: Provenance = Field(default_factory=Provenance)


class CounterfactualResponse(Envelope):
    """GET /findings/{finding_id}/counterfactual."""

    counterfactual: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance = Field(default_factory=Provenance)


class QueueResponse(Envelope):
    """GET /queue."""

    queue: list[dict[str, Any]] = Field(default_factory=list)
    insufficient_queue: list[str] = Field(default_factory=list)


class AuditVerifyResponse(Envelope):
    """GET /audit/verify."""

    valid: bool = False
    entry_count: int = 0
    merkle_root: str = ""


class AuditEntriesResponse(Envelope):
    """GET /audit/entries."""

    entries: list[dict[str, Any]] = Field(default_factory=list)


class RunTriggerResponse(Envelope):
    """POST /runs."""

    run_id: str = ""
    status: str = "started"


class ErrorResponse(Envelope):
    """Error payload."""

    error: str = ""
