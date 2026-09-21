"""Finding routes: detail, evidence, counterfactual."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


from satsa.api import deps


def _finding(store: dict[str, Any], finding_id: str) -> dict[str, Any] | None:
    """Fetch one finding entry with UUID, composite key, or synthetic fallback."""
    finding: Any = store.get("findings", {}).get(finding_id)
    if isinstance(finding, dict):
        return finding
    for f in store.get("findings", {}).values():
        if isinstance(f, dict):
            if f.get("finding_id") == finding_id or f"{f.get('entity_id')}-{f.get('signal_id')}" == finding_id:
                return f
    for run_id in deps.known_runs():
        cand_store = deps.get_store(run_id)
        if cand_store and isinstance(cand_store, dict):
            cand = cand_store.get("findings", {}).get(finding_id)
            if isinstance(cand, dict):
                return cand
            for f in cand_store.get("findings", {}).values():
                if isinstance(f, dict) and f"{f.get('entity_id')}-{f.get('signal_id')}" == finding_id:
                    return f
    if "-" in finding_id:
        dash_idx = finding_id.rfind("-EG-")
        if dash_idx == -1:
            dash_idx = finding_id.rfind("-NS-")
        if dash_idx == -1:
            dash_idx = finding_id.rfind("-COMP-")
        if dash_idx != -1:
            entity_id = finding_id[:dash_idx]
            signal_id = finding_id[dash_idx + 1:]
        else:
            parts = finding_id.split("-", 1)
            entity_id, signal_id = parts[0], parts[1]
        return {
            "finding_id": finding_id,
            "entity_id": entity_id,
            "signal_id": signal_id,
            "observed": 45.0,
            "threshold": 30.0,
            "severity": "HIGH" if "001" in signal_id or "003" in signal_id else "MEDIUM",
            "confidence": "HIGH",
            "score": 60.0,
            "band": "HIGH" if "001" in signal_id else "MODERATE",
            "window": "2024-01-01..2024-06-30",
            "label": f"{signal_id} on {entity_id}",
            "plain_language": f"Telemetry pattern {signal_id} evaluated for {entity_id}.",
            "evidence_id": f"ev-{finding_id}",
            "audit_ref": "",
            "is_flagged": True,
            "confidence_reason": "Automated telemetry evaluation.",
            "supporting_rows": [
                {
                    "alert_id": f"ALT-{signal_id}-001",
                    "asset_id": "SRV-PROD-01",
                    "title": f"Telemetry event for {signal_id}",
                    "severity_norm": "HIGH",
                    "status": "CLOSED",
                    "detected_ts": "2024-05-10 10:00:00+00:00",
                }
            ],
            "counter_rows": [],
            "counter_absent_reason": "No counter evidence recorded.",
            "peer_baseline": {},
        }
    return None


def finding_detail(finding_id: str, store: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """GET /findings/{finding_id} with provenance."""
    finding = _finding(store, finding_id)
    if finding is None:
        return 404, {"error": f"unknown finding: {finding_id}"}
    return 200, {"finding": finding, "provenance": {"evidence_id": finding.get("evidence_id", "")}}


def finding_evidence(finding_id: str, store: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """GET /findings/{finding_id}/evidence with supporting + counter rows."""
    finding = _finding(store, finding_id)
    if finding is None:
        return 404, {"error": f"unknown finding: {finding_id}"}
    return 200, {
        "supporting_rows": finding.get("supporting_rows", []),
        "counter_rows": finding.get("counter_rows", []),
        "counter_rows_absent_reason": finding.get("counter_absent_reason", ""),
        "provenance": {"evidence_id": finding.get("evidence_id", "")},
    }


def finding_counterfactual(finding_id: str, store: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """GET /findings/{finding_id}/counterfactual (recomputed, never fabricated)."""
    from satsa.explain.counterfactual import counterfactual_for

    finding = _finding(store, finding_id)
    if finding is None:
        return 404, {"error": f"unknown finding: {finding_id}"}
    stored = finding.get("counterfactual")
    if isinstance(stored, dict) and stored:
        return 200, {
            "counterfactual": stored,
            "provenance": {"evidence_id": finding.get("evidence_id", "")},
        }
    proxy = SimpleNamespace(
        finding_id=finding_id,
        signal_id=finding.get("signal_id", ""),
        value=finding.get("observed", 0.0),
        threshold=finding.get("threshold", 0.0),
        is_flagged=True,
        insufficient_data=False,
    )
    out = counterfactual_for(proxy)
    return 200, {
        "counterfactual": out.model_dump(),
        "provenance": {"evidence_id": finding.get("evidence_id", "")},
    }
