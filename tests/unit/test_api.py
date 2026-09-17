"""Phase 6 API tests via the backend-agnostic dispatcher (prior phases untouched)."""

from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path
from typing import Any


def _store() -> dict[str, Any]:
    """Ten-entity store with one evidenced finding."""
    entities = [
        "cse_alpha", "cse_bravo", "cse_charlie", "cse_delta", "cse_echo",
        "cse_foxtrot", "cse_golf", "cse_hotel", "cse_india", "cse_juliet",
    ]
    records = {
        entity: {"entity_id": entity, "overall_score": 5.0, "band": "LOW", "sector": "finance",
                 "confidence": "HIGH", "domain_scores": {}, "domain_contributions": {},
                 "domain_members": {}, "confidence_reason": "ok", "data_completeness": 0.9}
        for entity in entities
    }
    findings = {
        "f1": {"entity_id": "cse_bravo", "signal_id": "EG-001", "observed": 1.0,
               "threshold": 0.2, "severity": "HIGH", "confidence": "MEDIUM",
               "supporting_rows": [{"case_id": "c1"}], "counter_rows": [],
               "counter_absent_reason": "none found", "evidence_id": "e1",
               "counterfactual": {"computable": True}, "peer_baseline": {},
               "plain_language": "x", "label": "y", "window": "w",
               "confidence_reason": "ok", "audit_ref": "", "is_flagged": True,
               "score": 1.0, "band": "LOW"},
    }
    return {"run_id": "t", "generated_at": "now", "pipeline_version": "phase6",
            "merkle_root": "r", "records": records, "ranking": entities,
            "insufficient": [], "queue": [{"entity_id": "cse_bravo"}], "findings": findings,
            "data_quality": {}, "coverage_cells": []}


def _write_store(tmp_path: Path) -> None:
    target = tmp_path / "reports" / "t"
    target.mkdir(parents=True)
    (target / "run_store.json").write_text(json.dumps(_store()), encoding="utf-8")


def test_health_and_entities(monkeypatch: Any, tmp_path: Path) -> None:
    """GET /health 200; GET /entities lists all ten synthetic entities."""
    from satsa.api import deps
    from satsa.api.main import handle_request

    _write_store(tmp_path)
    monkeypatch.setattr(deps, "STORE_ROOT", tmp_path / "reports")
    status, body = handle_request("GET", "/health", {}, {})
    assert status == 200
    assert body["status"] == "ok"
    assert body["run_id"] == "" and body["generated_at"]
    status, body = handle_request("GET", "/entities", {"run_id": "t"}, {})
    assert status == 200
    assert len(body["entities"]) == 10
    assert body["run_id"] == "t"


def test_evidence_and_audit(monkeypatch: Any, tmp_path: Path) -> None:
    """Evidence carries supporting rows; audit verify is valid on clean ledger."""
    from satsa.api import deps
    from satsa.api.main import handle_request
    from satsa.audit.ledger import append_event

    _write_store(tmp_path)
    monkeypatch.setattr(deps, "STORE_ROOT", tmp_path / "reports")
    monkeypatch.setattr(deps, "WAREHOUSE_ROOT", tmp_path)
    append_event(
        "t", "RUN_START", {}, jsonl_path=tmp_path / "l.jsonl", db_path=tmp_path / "audit.duckdb"
    )
    status, body = handle_request("GET", "/findings/f1/evidence", {"run_id": "t"}, {})
    assert status == 200
    assert body["supporting_rows"]
    assert body["provenance"]["evidence_id"] == "e1"
    status, body = handle_request("GET", "/audit/verify", {}, {})
    assert status == 200
    assert body["valid"] is True


def test_token_gate(monkeypatch: Any, tmp_path: Path) -> None:
    """Token enabled without header returns 401; loopback host asserted."""
    from satsa.api import deps
    from satsa.api.main import API_HOST, handle_request

    _write_store(tmp_path)
    monkeypatch.setattr(deps, "STORE_ROOT", tmp_path / "reports")
    monkeypatch.setenv("SATSA_API_TOKEN_ENABLED", "1")
    monkeypatch.setenv("SATSA_API_TOKEN", "secret")
    assert API_HOST == "127.0.0.1"
    status, _ = handle_request("GET", "/entities", {"run_id": "t"}, {})
    assert status == 401
    status, body = handle_request("GET", "/entities", {"run_id": "t"}, {"X-API-Token": "secret"})
    assert status == 200
    assert len(body["entities"]) == 10


def test_stdlib_server_binds_loopback(monkeypatch: Any, tmp_path: Path) -> None:
    """Live stdlib server answers on 127.0.0.1 with JSON."""
    import json as json_mod
    from http.server import HTTPServer

    from satsa.api import deps
    from satsa.api.main import _Handler

    _write_store(tmp_path)
    monkeypatch.setattr(deps, "STORE_ROOT", tmp_path / "reports")
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    assert server.server_address[0] == "127.0.0.1"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/health"
        with urllib.request.urlopen(url, timeout=10) as resp:
            assert resp.status == 200
            assert json_mod.loads(resp.read())["status"] == "ok"
    finally:
        server.shutdown()
        thread.join(timeout=10)


def test_trigger_runs_without_blocking(monkeypatch: Any) -> None:
    """POST /runs returns 202 with a run id via patched spawner."""
    from satsa.api import main as api_main

    calls: list[str] = []
    monkeypatch.setattr(api_main, "_spawn_run", lambda run_id: calls.append(run_id))
    status, body = api_main.handle_request("POST", "/runs", {}, {}, {"run_id": "demo-x"})
    assert status == 202
    assert body["run_id"] == "demo-x"
    assert calls == ["demo-x"]
