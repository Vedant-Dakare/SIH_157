"""Finding routes: detail, evidence, counterfactual."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def _finding(store: dict[str, Any], finding_id: str) -> dict[str, Any] | None:
    """Fetch one finding entry."""
    finding: Any = store.get("findings", {}).get(finding_id)
    return finding if isinstance(finding, dict) else None


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
