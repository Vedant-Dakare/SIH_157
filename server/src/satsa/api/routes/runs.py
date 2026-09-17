"""Health + run routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from satsa.api import deps


def health() -> tuple[int, dict[str, Any]]:
    """GET /health."""
    return 200, {"status": "ok", "pipeline_version": "phase6"}


def list_runs() -> tuple[int, dict[str, Any]]:
    """GET /runs — run ids from stores and warehouse manifests."""
    runs = set(deps.known_runs())
    manifests = Path(deps.WAREHOUSE_ROOT) / "runs"
    if manifests.exists():
        runs |= {p.stem.replace(".manifest", "") for p in manifests.glob("*.manifest.json")}
    return 200, {"runs": sorted(runs)}


def run_status(run_id: str) -> tuple[int, dict[str, Any]]:
    """GET /runs/{run_id}: report processing state for uploaded runs."""
    if deps.get_store(run_id) is not None:
        return 200, {"status": "complete"}
    run_dir = Path(deps.WAREHOUSE_ROOT) / "runs" / run_id
    status_file = run_dir / "status.json"
    if status_file.exists():
        try:
            status = json.loads(status_file.read_text(encoding="utf-8")).get("status")
            if status in {"complete", "failed", "processing"}:
                return 200, {"status": status}
        except (OSError, ValueError, TypeError):
            pass
    partial = Path(deps.WAREHOUSE_ROOT) / "runs" / f"{run_id}.partial.json"
    if partial.exists():
        return 200, {"status": "failed"}
    if run_dir.exists():
        return 200, {"status": "processing"}
    if run_id.startswith("upload-"):
        return 202, {"status": "processing"}
    return 404, {"status": "not_found"}


def run_manifest(run_id: str) -> tuple[int, dict[str, Any]]:
    """GET /runs/{run_id}/manifest."""
    path = Path(deps.WAREHOUSE_ROOT) / "runs" / f"{run_id}.manifest.json"
    if not path.exists():
        return 404, {"error": f"unknown run: {run_id}"}
    try:
        return 200, {"manifest": json.loads(path.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return 500, {"error": "manifest unreadable"}
