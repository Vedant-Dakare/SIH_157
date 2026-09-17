"""Entity routes."""

from __future__ import annotations

from typing import Any

from satsa.api import deps


def _record(store: dict[str, Any], entity_id: str) -> dict[str, Any] | None:
    """Fetch one score record."""
    record: Any = store.get("records", {}).get(entity_id)
    return record if isinstance(record, dict) else None


def list_entities(query: dict[str, str], store: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """GET /entities with optional run/band/sector filters."""
    entities = [
        {
            "entity_id": entity_id,
            "band": record.get("band", "LOW"),
            "sector": str(record.get("sector", "unknown")),
            "overall_score": float(record.get("overall_score", 0.0)),
            "confidence": str(record.get("confidence", "LOW")),
        }
        for entity_id, record in store.get("records", {}).items()
        if (not query.get("band") or record.get("band") == query["band"])
        and (not query.get("sector") or str(record.get("sector", "")) == query["sector"])
    ]
    entities.sort(key=lambda e: e["entity_id"])
    return 200, {"entities": entities}


def entity_detail(entity_id: str, store: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """GET /entities/{entity_id} with decomposition and confidence."""
    record = _record(store, entity_id)
    if record is None:
        return 404, {"error": f"unknown entity: {entity_id}"}
    return 200, {"entity": record}


def entity_findings(entity_id: str, store: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """GET /entities/{entity_id}/findings."""
    if entity_id not in store.get("records", {}):
        return 404, {"error": f"unknown entity: {entity_id}"}
    findings = [
        {
            "finding_id": fid,
            "entity_id": finding.get("entity_id", ""),
            "signal_id": finding.get("signal_id", ""),
            "severity": finding.get("severity", "INFO"),
            "confidence": finding.get("confidence", "LOW"),
        }
        for fid, finding in store.get("findings", {}).items()
        if finding.get("entity_id") == entity_id
    ]
    findings.sort(key=lambda f: f["finding_id"])
    return 200, {"findings": findings}


def resolve_store(query: dict[str, str]) -> tuple[dict[str, Any] | None, str]:
    """Pick the store for ?run_id= (default: latest known run)."""
    run_id = query.get("run_id", "")
    if not run_id:
        known = deps.known_runs()
        run_id = known[-1] if known else ""
    if not run_id:
        return None, ""
    return deps.get_store(run_id), run_id
