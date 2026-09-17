"""Phase 6 render tests (new file, prior phases untouched)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _store() -> dict[str, Any]:
    """Minimal run store covering all ten synthetic CSEs."""
    entities = [
        "cse_alpha", "cse_bravo", "cse_charlie", "cse_delta", "cse_echo",
        "cse_foxtrot", "cse_golf", "cse_hotel", "cse_india", "cse_juliet",
    ]
    records = {
        entity: {
            "entity_id": entity, "overall_score": 10.0, "band": "LOW", "confidence": "HIGH",
            "confidence_reason": "test feed", "sector": "finance",
            "domain_scores": {"governance": 5.0}, "domain_contributions": {"governance": 5.0},
            "domain_members": {"governance": []}, "data_completeness": 0.95,
        }
        for entity in entities
    }
    findings = {
        "f1": {
            "entity_id": "cse_bravo", "signal_id": "EG-001", "observed": 1.0, "threshold": 0.2,
            "severity": "HIGH", "confidence": "MEDIUM", "score": 1.0, "band": "LOW",
            "window": "w", "label": "Premature closure", "plain_language": "Too fast.",
            "peer_baseline": {"median": 0.0, "p95": 0.0, "n": 12, "cohort_id": "c"},
            "counterfactual": {"computable": True, "plain_language": "Slow down.",
                               "required_value": 0.19, "reason_if_null": ""},
            "supporting_rows": [{"case_id": "c1"}], "counter_rows": [],
            "counter_absent_reason": "none found", "evidence_id": "e1",
            "audit_ref": "seq 3", "is_flagged": True, "confidence_reason": "ok",
        }
    }
    return {
        "run_id": "t", "window": "w", "generated_at": "now", "pipeline_version": "phase6",
        "merkle_root": "ab" * 32, "records": records, "ranking": entities,
        "insufficient": [], "queue": [], "findings": findings,
        "data_quality": {e: {"total": 1, "valid": 1, "quarantined": 0, "quarantine_rate": 0.0,
                             "top_reason": "—"} for e in entities},
        "coverage_cells": [], "quality_trend": "t", "portfolio_trend": "STABLE",
        "trend_windows": {},
    }


def test_entity_report_all_ten(tmp_path: Path) -> None:
    """All ten CSE entity reports render without error."""
    from satsa.report import render_html as rh

    store = _store()
    for entity in store["records"]:
        text = rh.render_entity_report(entity, "t", store=store, out_dir=tmp_path)
        assert "Assumptions" in text
        assert entity in text


def test_portfolio_report(tmp_path: Path) -> None:
    """Portfolio report renders with footer fields."""
    from satsa.report import render_html as rh

    text = rh.render_portfolio_report("t", store=_store(), out_dir=tmp_path)
    assert "ab" * 32 in text
    assert (tmp_path / "portfolio_report.html").exists()


def test_pdf_renders_with_merkle(tmp_path: Path) -> None:
    """PDF fallback renders bytes containing the Merkle root."""
    from satsa.report import render_html as rh
    from satsa.report import render_pdf as pdf_mod

    store = _store()
    text = rh.render_portfolio_report("t", store=store, out_dir=tmp_path)
    target = pdf_mod.render_pdf(text, tmp_path / "report.pdf", footer=f"t | {'ab' * 32}")
    assert target.stat().st_size > 0
    assert ("ab" * 32).encode() in target.read_bytes()


def test_charts_deterministic_with_tables() -> None:
    """Same input yields identical SVG bytes embedding a data table."""
    import base64

    from satsa.report import charts as chart_mod

    first = chart_mod.risk_band_distribution({"LOW": 8, "HIGH": 2}, seed=7)
    second = chart_mod.risk_band_distribution({"LOW": 8, "HIGH": 2}, seed=7)
    assert first == second
    assert "<table" in base64.b64decode(first).decode("utf-8", errors="replace")
