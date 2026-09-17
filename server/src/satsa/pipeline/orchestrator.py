"""Simple DAG runner with checkpointing, retries and a rich run summary.

Usage: python -m satsa.pipeline.orchestrator --run-id demo [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from satsa.audit.hashing import sha256_dict
from satsa.paths import ROOT
from satsa.pipeline.stages import StageDefinition, default_stages, validate_dag

BACKOFF_SECONDS = (1.0, 2.0, 4.0)
WAREHOUSE_RUNS = Path("data/warehouse/runs")


def _utc_now() -> str:
    """Current UTC timestamp."""
    return datetime.now(UTC).isoformat()


def _marker_path(run_dir: Path, stage: str) -> Path:
    """Completion marker for one stage."""
    return run_dir / "stages" / f"{stage}.done"


def _read_marker(run_dir: Path, stage: str) -> dict[str, Any] | None:
    """Read a stage marker, or None when absent/corrupt."""
    path = _marker_path(run_dir, stage)
    if not path.exists():
        return None
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _write_marker(run_dir: Path, stage: str, input_hash: str, output_hash: str) -> None:
    """Write a stage completion marker."""
    path = _marker_path(run_dir, stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"stage_name": stage, "input_hash": input_hash, "output_hash": output_hash,
             "completed_at": _utc_now()},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _hash_json(data: Any) -> str:
    """Stable hash of JSON-serialisable data."""
    if isinstance(data, dict):
        return sha256_dict(data)
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def _results_to_json(results: dict[str, Any]) -> dict[str, Any]:
    """Serialise signal results to plain dicts for checkpoint rehydration."""
    fields = ("finding_id", "entity_id", "signal_id", "value", "threshold", "score",
              "severity", "confidence", "sample_size", "window_start", "window_end",
              "is_flagged", "insufficient_data", "cohort_too_small", "contributing_rows_ref",
              "metadata")
    flat: dict[str, Any] = {}
    for entity, entity_results in results.items():
        flat[entity] = {
            sid: {f: getattr(res, f, None) for f in fields} for sid, res in entity_results.items()
        }
    return flat


def _results_from_json(data: dict[str, Any]) -> dict[str, Any]:
    """Rebuild result namespaces from checkpoint JSON."""
    from types import SimpleNamespace

    return {
        entity: {sid: SimpleNamespace(**fields) for sid, fields in entity_results.items()}
        for entity, entity_results in data.items()
    }


def _load_json(run_dir: Path, name: str) -> Any:
    """Load a checkpoint JSON artifact, or None."""
    path = run_dir / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _rehydrate(stage_name: str, ctx: dict[str, Any]) -> None:
    """Reload a skipped stage's outputs from run-dir checkpoints."""
    run_dir: Path = ctx["run_dir"]
    if stage_name == "ingest":
        data = _load_json(run_dir, "entities.json")
        if data:
            ctx["entities"] = data.get("entities", [])
    elif stage_name == "canonical":
        data = _load_json(run_dir, "canonical.json")
        if data:
            ctx["canonical_rows"] = int(data.get("row_count", 0))
    elif stage_name == "features":
        data = _load_json(run_dir, "features.json")
        if data:
            ctx["features"] = data
    elif stage_name == "signals":
        index = _load_json(run_dir, "findings_index.json")
        results = _load_json(run_dir, "results.json")
        if index:
            ctx["finding_index"] = index
        if results:
            ctx["results"] = _results_from_json(results)
    elif stage_name == "ml":
        pass
    elif stage_name == "score":
        data = _load_json(run_dir, "records.json")
        if data:
            ctx["records"] = data
    elif stage_name == "prioritise":
        data = _load_json(run_dir, "queue.json")
        if data:
            ctx["queue"] = data
        if "records" in ctx:
            ctx["insufficient"] = [
                e for e, r in ctx["records"].items() if r.get("data_completeness", 1.0) < 0.6
            ]
    elif stage_name == "explain":
        data = _load_json(run_dir, "explanations.json")
        if data:
            ctx["explanations"] = data
    elif stage_name == "narrate":
        pass


# ---------------------------------------------------------------- stage bodies

def stage_ingest(ctx: dict[str, Any]) -> dict[str, Any]:
    """Verify synthetic corpora are present on disk."""
    from satsa.signals.runner import TABLES, list_entities

    entities = list_entities(ctx.get("synthetic_root", "data/synthetic"))
    if not entities:
        raise FileNotFoundError("no synthetic corpora found")
    inventory = sorted(f"{e}/{t}" for e in entities for t in TABLES)
    ctx["entities"] = entities
    (ctx["run_dir"] / "entities.json").write_text(
        json.dumps({"entities": entities}, indent=2, sort_keys=True), encoding="utf-8")
    return {"records_in": 0, "records_out": len(inventory), "warnings": [],
            "output": {"inventory_hash": _hash_json(inventory), "entities": entities}}


def stage_canonical(ctx: dict[str, Any]) -> dict[str, Any]:
    """Read canonical parquet tables and count rows."""
    import pandas as pd

    root = Path(ctx.get("synthetic_root", "data/synthetic"))
    total = 0
    for entity_id in ctx.get("entities", []):
        for table in ("alerts", "cases", "investigations", "escalations", "assets", "telemetry"):
            path = root / entity_id / f"{table}.parquet"
            if path.exists():
                total += len(pd.read_parquet(path))
    ctx["canonical_rows"] = total
    (ctx["run_dir"] / "canonical.json").write_text(
        json.dumps({"row_count": total}, indent=2, sort_keys=True), encoding="utf-8")
    return {"records_in": total, "records_out": total, "warnings": [],
            "output": {"row_count": total}}


def stage_features(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build entity feature vectors and persist them in the run dir."""
    from satsa.signals.runner import build_all_features

    features = build_all_features(ctx.get("synthetic_root", "data/synthetic"))
    ctx["features"] = features
    (ctx["run_dir"] / "features.json").write_text(
        json.dumps(features, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"records_in": ctx.get("canonical_rows", 0), "records_out": len(features),
            "warnings": [], "output": {"entities": sorted(features)}}


def stage_signals(ctx: dict[str, Any]) -> dict[str, Any]:
    """Compute rule signals for every entity; index findings."""
    from satsa.signals.runner import list_entities, run_entity

    features = ctx["features"]
    synthetic_root = ctx.get("synthetic_root", "data/synthetic")
    results: dict[str, Any] = {}
    index: dict[str, Any] = {}
    flagged = 0
    for entity_id in list_entities(synthetic_root):
        entity_results = run_entity(entity_id, features, synthetic_root, ctx["run_id"])
        results[entity_id] = entity_results
        for signal_id, result in entity_results.items():
            index[result.finding_id] = {"entity_id": entity_id, "signal_id": signal_id,
                                       "is_flagged": bool(result.is_flagged)}
            flagged += int(bool(result.is_flagged))
    ctx["results"] = results
    ctx["finding_index"] = index
    (ctx["run_dir"] / "findings_index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    (ctx["run_dir"] / "results.json").write_text(
        json.dumps(_results_to_json(results), indent=2, sort_keys=True, default=str),
        encoding="utf-8")
    return {"records_in": len(features), "records_out": len(index),
            "warnings": [], "output": {"flagged": flagged, "total": len(index)}}


def stage_ml(ctx: dict[str, Any]) -> dict[str, Any]:
    """Light ML check: calibrator presence + embedding smoke test."""
    from satsa.ml.embeddings import encode

    warnings: list[str] = []
    calibrator = Path("models/artifacts/risk_calibrator.joblib")
    if not calibrator.exists():
        warnings.append("risk calibrator artefact missing; scores uncalibrated")
    vectors = encode(["triage note one", "triage note two", "triage note three"])
    output = {"embedding_dim": int(vectors.shape[1]), "calibrated": calibrator.exists()}
    (ctx["run_dir"] / "ml.json").write_text(
        json.dumps(output, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"records_in": 3, "records_out": int(vectors.shape[0]), "warnings": warnings,
            "output": output}


def stage_score(ctx: dict[str, Any]) -> dict[str, Any]:
    """Score every entity, reusing in-memory signal results."""
    from satsa.scoring.risk_engine import score_entity
    from satsa.signals.runner import load_entity

    synthetic_root = ctx.get("synthetic_root", "data/synthetic")
    records: dict[str, Any] = {}
    for entity_id, results in ctx["results"].items():
        frames = load_entity(entity_id, synthetic_root)
        records[entity_id] = score_entity(
            entity_id, results, frames, ctx["features"].get(entity_id, {}),
            run_id=ctx["run_id"], seed=ctx.get("seed", 42))
    ctx["records"] = records
    (ctx["run_dir"] / "records.json").write_text(
        json.dumps(records, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"records_in": len(ctx["results"]), "records_out": len(records),
            "warnings": [], "output": {"bands": sorted({r["band"] for r in records.values()})}}


def stage_prioritise(ctx: dict[str, Any]) -> dict[str, Any]:
    """Build the review queue from in-memory scores and evidence."""
    from satsa.scoring.confidence import ledger_findings
    from satsa.scoring.prioritisation import LEDGER_PATH, build_queue
    from satsa.signals.runner import load_entity

    synthetic_root = ctx.get("synthetic_root", "data/synthetic")
    results_by, bundles_by, frames_by = {}, {}, {}
    from satsa.signals.registry import get_signal

    for entity_id, results in ctx["results"].items():
        frames = load_entity(entity_id, synthetic_root)
        frames_by[entity_id] = frames
        results_by[entity_id] = results
        bundles: dict[str, Any] = {}
        for signal_id, result in results.items():
            if not bool(getattr(result, "is_flagged", False)):
                continue
            signal = get_signal(signal_id)
            try:
                bundles[signal_id] = signal.evidence(result) if signal else None
            except Exception:
                bundles[signal_id] = None
        bundles_by[entity_id] = bundles
    ctx["bundles"] = bundles_by
    main = {e: r for e, r in ctx["records"].items() if r["data_completeness"] >= 0.6}
    queue = build_queue(main, results_by, bundles_by, frames_by,
                        ledger_findings(LEDGER_PATH), seed=ctx.get("seed", 42))
    ctx["queue"] = queue
    insufficient = [e for e, r in ctx["records"].items() if r["data_completeness"] < 0.6]
    ctx["insufficient"] = insufficient
    (ctx["run_dir"] / "queue.json").write_text(
        json.dumps(queue, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"records_in": len(main), "records_out": len(queue), "warnings": [],
            "output": {"top": queue[0]["entity_id"] if queue else None,
                       "insufficient": insufficient}}


def stage_explain(ctx: dict[str, Any]) -> dict[str, Any]:
    """Reason codes + counterfactuals + evidence for the top-5 queue findings."""
    import duckdb

    from satsa.explain import counterfactual as cf_mod
    from satsa.explain import evidence as ev_mod
    from satsa.explain import reason_codes as rc_mod
    from satsa.signals.registry import get_signal

    conn = duckdb.connect(str(Path("data/warehouse/evidence.duckdb")))
    conn.execute(ev_mod._SCHEMA)
    explained: dict[str, Any] = {}
    try:
        for entry in ctx.get("queue", [])[:5]:
            for signal_id in entry.get("signal_ids", [])[:2]:
                result = ctx["results"][entry["entity_id"]][signal_id]
                signal = get_signal(signal_id)
                bundle = ev_mod.materialize(
                    result.finding_id, signal_id, entry["entity_id"],
                    f"{result.window_start}..{result.window_end}",
                    signal.evidence(result) if signal else None, conn)
                reason = rc_mod.from_result(result, getattr(signal, "name", ""), bundle)
                explained[result.finding_id] = {
                    "reason": reason.model_dump(),
                    "counterfactual": cf_mod.counterfactual_for(result).model_dump(),
                    "evidence_id": bundle.evidence_id,
                }
    finally:
        conn.close()
    ctx["explanations"] = explained
    (ctx["run_dir"] / "explanations.json").write_text(
        json.dumps(explained, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"records_in": len(ctx.get("queue", [])), "records_out": len(explained),
            "warnings": [], "output": {"explained": sorted(explained)}}


def stage_narrate(ctx: dict[str, Any]) -> dict[str, Any]:
    """Narrate the top-ranked entity (template when LLM is off)."""
    from satsa.ai.narrate import narrate_entity

    queue = ctx.get("queue", [])
    if not queue:
        return {"records_in": 0, "records_out": 0, "warnings": ["empty queue; nothing narrated"],
                "output": {}}
    out = narrate_entity(queue[0]["entity_id"], seed=ctx.get("seed", 42))
    (ctx["run_dir"] / "narratives.json").write_text(
        json.dumps(out, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"records_in": 1, "records_out": len(out.get("narratives", {})),
            "warnings": [], "output": {"entity": out["entity_id"]}}


def _quality_stats(ctx: dict[str, Any]) -> dict[str, Any]:
    """Per-entity ingestion scorecard from frames + quarantine ledger."""
    from satsa.signals.runner import load_entity

    synthetic_root = ctx.get("synthetic_root", "data/synthetic")
    quality: dict[str, Any] = {}
    for entity_id in ctx.get("entities", []):
        frames = load_entity(entity_id, synthetic_root)
        tables = ("alerts", "cases", "investigations")
        total = sum(len(frames[t]) for t in tables if not frames[t].empty)
        nulls = sum(int(frames[t].isna().sum().sum()) for t in tables if not frames[t].empty)
        qpath = Path("data/quarantine") / f"{entity_id}.jsonl"
        if qpath.exists():
            quarantined = sum(
                1 for line in qpath.read_text(encoding="utf-8").splitlines() if line.strip()
            )
        else:
            quarantined = 0
        quality[entity_id] = {"total": total, "valid": max(0, total - quarantined),
                              "quarantined": quarantined,
                              "quarantine_rate": round(quarantined / max(1, total), 4),
                              "null_cells": nulls,
                              "top_reason": "partial feed" if quarantined else "—"}
    return quality


def stage_report(ctx: dict[str, Any]) -> dict[str, Any]:
    """Render all six HTML reports plus CSV/JSON/XLSX exports and the store."""
    from satsa.report import exports as exports_mod
    from satsa.report import render_html as rh
    from satsa.report import render_pdf as pdf_mod

    run_id = ctx["run_id"]
    out_dir = Path("data/curated/reports") / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    records = ctx["records"]
    for entity_id, record in records.items():
        try:
            from satsa.settings import load_settings  # noqa: F401
            record["sector"] = _sector_of(entity_id)
        except Exception:
            record["sector"] = "unknown"
    findings: dict[str, Any] = {}
    from satsa.signals.registry import get_signal as _get_signal

    for finding_id, meta in ctx.get("finding_index", {}).items():
        if not meta["is_flagged"]:
            continue
        entity_id, signal_id = meta["entity_id"], meta["signal_id"]
        result = ctx["results"][entity_id][signal_id]
        bundle = (ctx.get("bundles", {}).get(entity_id, {}) or {}).get(signal_id)
        if bundle is None:
            try:
                _signal = _get_signal(signal_id)
                bundle = _signal.evidence(result) if _signal else None
            except Exception:
                bundle = None
        rows = list(getattr(bundle, "supporting_rows", []) or []) if bundle else []
        counter = list(getattr(bundle, "counter_rows", []) or []) if bundle else []
        reason_text = getattr(bundle, "counter_none_reason", "") if bundle else ""
        record = records[entity_id]
        findings[finding_id] = {
            "entity_id": entity_id, "signal_id": signal_id, "observed": result.value,
            "threshold": result.threshold, "severity": result.severity,
            "confidence": result.confidence,
            "score": result.score, "band": record["band"],
            "window": f"{result.window_start}..{result.window_end}",
            "label": signal_id, "plain_language": f"{signal_id} observed at {result.value}.",
            "peer_baseline": dict(getattr(bundle, "cohort_comparison", {}) or {}) if bundle else {},
            "counterfactual": {}, "supporting_rows": rows[:10], "counter_rows": counter[:10],
            "counter_absent_reason": reason_text,
            "evidence_id": getattr(bundle, "evidence_id", "") if bundle else "",
            "audit_ref": "", "is_flagged": True,
            "confidence_reason": record.get("confidence_reason", ""),
        }
    # Counterfactuals for stored findings.
    from satsa.explain import counterfactual as cf_mod

    for finding_id, finding in findings.items():
        result = ctx["results"][finding["entity_id"]][finding["signal_id"]]
        finding["counterfactual"] = cf_mod.counterfactual_for(result).model_dump()
    coverage_cells = _coverage_cells(ctx)
    store = {
        "run_id": run_id, "window": "2024-05-03..2024-05-31", "generated_at": _utc_now(),
        "pipeline_version": "phase6", "merkle_root": ctx.get("merkle_root", ""),
        "records": records, "ranking": [e["entity_id"] for e in ctx.get("queue", [])],
        "insufficient": ctx.get("insufficient", []), "queue": ctx.get("queue", []),
        "findings": findings, "data_quality": _quality_stats(ctx), "coverage_cells": coverage_cells,
        "quality_trend": "Single-window run; trends appear after repeat runs.",
        "portfolio_trend": "STABLE",
        "trend_windows": {
            e: [{"window": "2024-05-03..2024-05-31", "overall_score": r["overall_score"]}]
            for e, r in records.items()
        },
    }
    (ctx["run_dir"] / "run_store.json").write_text(
        json.dumps(store, indent=2, sort_keys=True, default=str), encoding="utf-8")
    (out_dir / "run_store.json").write_text(
        json.dumps(store, indent=2, sort_keys=True, default=str), encoding="utf-8")
    ctx["store"] = store
    rh.render_portfolio_report(run_id, store=store, out_dir=out_dir)
    for entity_id in records:
        rh.render_entity_report(entity_id, run_id, store=store, out_dir=out_dir)
    for finding_id in findings:
        rh.render_finding_detail(finding_id, run_id, store=store, out_dir=out_dir)
    rh.render_review_queue(run_id, store=store, out_dir=out_dir)
    rh.render_negative_space_map(run_id, store=store, out_dir=out_dir)
    rh.render_data_quality_report(run_id, store=store, out_dir=out_dir)
    portfolio_html = (out_dir / "portfolio_report.html").read_text(encoding="utf-8")
    pdf_mod.render_pdf(portfolio_html, out_dir / "portfolio_report.pdf",
                       footer=f"{run_id} | {store['merkle_root']}")
    exports_mod.export_findings_csv(run_id, out_dir / "findings.csv", store)
    exports_mod.export_findings_json(run_id, out_dir / "findings.json", store)
    exports_mod.export_findings_xlsx(run_id, out_dir / "findings.xlsx", store)
    return {"records_in": len(records), "records_out": 6, "warnings": [],
            "output": {"dir": str(out_dir)}}


def _sector_of(entity_id: str) -> str:
    """Sector lookup (read-only)."""
    import yaml

    try:
        with open("configs/entity_registry.yaml", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return str(data.get("entities", {}).get(entity_id, {}).get("sector", "unknown"))
    except OSError:
        return "unknown"


def _coverage_cells(ctx: dict[str, Any]) -> list[dict[str, Any]]:
    """Coverage heatmap cells from the negative-space engine."""
    from satsa.features import coverage as coverage_mod
    from satsa.signals.runner import load_entity

    synthetic_root = ctx.get("synthetic_root", "data/synthetic")
    cells: list[dict[str, Any]] = []
    finding_by_entity: dict[str, str] = {}
    for finding_id, meta in ctx.get("finding_index", {}).items():
        if meta["is_flagged"] and meta["signal_id"].startswith("NS-"):
            finding_by_entity.setdefault(meta["entity_id"], finding_id)
    for entity_id in ctx.get("entities", []):
        frames = load_entity(entity_id, synthetic_root)
        try:
            space = coverage_mod.negative_space_map(
                entity_id, frames.get("assets"), frames.get("telemetry"))
        except Exception:
            continue
        for _, row in space.iterrows():
            gap = bool(row.get("gap_flag", False))
            fid = finding_by_entity.get(entity_id, "")
            cells.append({
                "entity_id": entity_id, "asset_type": str(row.get("asset_id", ""))[:24],
                "source": str(row.get("expected_source", "")), "gap": "gap" if gap else "ok",
                "css": "gap-expected" if gap else "gap-ok",
                "link": f"finding_{fid}.html" if fid else "#", "finding_id": fid or "—",
            })
    return cells[:500]


def stage_audit_seal(ctx: dict[str, Any]) -> dict[str, Any]:
    """Append RUN_END, sign the manifest, verify the chain."""
    import duckdb

    from satsa.audit import ledger as audit_ledger
    from satsa.audit.merkle import compute_run_manifest
    from satsa.settings import load_settings

    run_id = ctx["run_id"]
    _record_event(ctx, run_id, "RUN_END", {"stages": sorted(ctx.get("completed", []))})
    db_path = ctx.get("ledger_db") or "data/warehouse/audit.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        manifest = compute_run_manifest(
            run_id, conn, load_settings(),
            manifest_dir=ctx.get("manifest_dir", "data/warehouse/runs"))
        verification = audit_ledger.verify_chain(
            conn, ctx.get("ledger_jsonl") or audit_ledger.LEDGER_JSONL
        )
    finally:
        conn.close()
    ctx["merkle_root"] = manifest.merkle_root
    return {"records_in": len(ctx.get("completed", [])), "records_out": 1,
            "warnings": [] if verification.valid else ["ledger verification failed"],
            "output": {"merkle_root": manifest.merkle_root, "valid": verification.valid}}


# ------------------------------------------------------------------- runner

def _input_hash(stage: StageDefinition, ctx: dict[str, Any], prev_output: str) -> str:
    """Chain input hashes so upstream changes invalidate downstream markers."""
    if not stage.dependencies:
        return _hash_json(ctx.get("entities_seed", "synthetic-v1"))
    return _hash_json({"prev": prev_output, "stage": stage.name})


def run_pipeline(
    run_id: str = "demo",
    stages: list[StageDefinition] | None = None,
    force: bool = False,
    seed: int = 42,
    run_dir: str | Path | None = None,
    synthetic_root: str = "data/synthetic",
    ledger_jsonl: str | Path | None = None,
    ledger_db: str | Path | None = None,
    manifest_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run the DAG with checkpointing, retries and a rich summary table."""
    stages = stages or default_stages()
    validate_dag(stages)
    directory = Path(run_dir) if run_dir else WAREHOUSE_RUNS / run_id
    directory.mkdir(parents=True, exist_ok=True)
    if force:
        for stale in (directory / "stages").glob("*.done"):
            stale.unlink()
    ctx: dict[str, Any] = {"run_id": run_id, "run_dir": directory, "seed": seed,
                           "synthetic_root": synthetic_root, "completed": [],
                           "ledger_jsonl": ledger_jsonl, "ledger_db": ledger_db,
                           "manifest_dir": manifest_dir or "data/warehouse/runs"}
    _record_event(ctx, run_id, "RUN_START", {"seed": seed})
    rows: list[dict[str, Any]] = []
    prev_output = "genesis"
    aborted = False
    for stage in stages:
        started = time.monotonic()
        marker = _read_marker(directory, stage.name)
        input_hash = _input_hash(stage, ctx, prev_output)
        if marker and marker.get("input_hash") == input_hash and not force:
            rows.append({"stage": stage.name, "status": "skipped", "duration": 0.0,
                         "records_in": 0, "records_out": 0, "warnings": []})
            prev_output = str(marker.get("output_hash", prev_output))
            ctx["completed"].append(stage.name)
            _rehydrate(stage.name, ctx)
            continue
        attempts = 0
        outcome: dict[str, Any] | None = None
        error: str | None = None
        while attempts <= stage.retry_count:
            try:
                outcome = stage.function(ctx)
                error = None
                break
            except Exception as exc:
                error = str(exc)[:300]
                if attempts < stage.retry_count:
                    time.sleep(BACKOFF_SECONDS[min(attempts, len(BACKOFF_SECONDS) - 1)])
                attempts += 1
        duration = time.monotonic() - started
        if outcome is None:
            _record_event(ctx, run_id, "STAGE_COMPLETE",
                          {"stage": stage.name, "status": "failed", "error": error})
            if stage.required:
                rows.append({"stage": stage.name, "status": "aborted", "duration": duration,
                             "records_in": 0, "records_out": 0, "warnings": [error or "failed"]})
                aborted = True
                _write_partial_manifest(run_id, rows, directory)
                break
            rows.append({"stage": stage.name, "status": "failed-optional", "duration": duration,
                         "records_in": 0, "records_out": 0, "warnings": [error or "failed"]})
            continue
        output_hash = _hash_json(outcome.get("output", {}))
        _write_marker(directory, stage.name, input_hash, output_hash)
        _record_event(ctx, run_id, "STAGE_COMPLETE",
                      {"stage": stage.name, "status": "ok", "output_hash": output_hash})
        prev_output = output_hash
        ctx["completed"].append(stage.name)
        rows.append({"stage": stage.name, "status": "ok", "duration": duration,
                     "records_in": int(outcome.get("records_in", 0)),
                     "records_out": int(outcome.get("records_out", 0)),
                     "warnings": list(outcome.get("warnings", []))})
    console = Console()
    table = Table(title=f"Run {run_id} summary")
    for col in ("stage", "status", "duration", "records_in", "records_out", "warnings"):
        table.add_column(col)
    for row in rows:
        table.add_row(
            row["stage"], row["status"], f"{row['duration']:.1f}s",
            str(row["records_in"]), str(row["records_out"]), "; ".join(row["warnings"][:2]))
    console.print(table)
    status = "failed" if aborted or not (directory / "run_store.json").exists() else "complete"
    (directory / "status.json").write_text(
        json.dumps({"run_id": run_id, "status": status, "updated_at": _utc_now()}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"run_id": run_id, "rows": rows, "aborted": aborted, "run_dir": str(directory)}


def _ledger_kwargs(ctx: dict[str, Any]) -> dict[str, Any]:
    """Explicit ledger paths when provided (tests), else module defaults."""
    kwargs: dict[str, Any] = {}
    if ctx.get("ledger_jsonl") is not None:
        kwargs["jsonl_path"] = ctx["ledger_jsonl"]
    if ctx.get("ledger_db") is not None:
        kwargs["db_path"] = ctx["ledger_db"]
    return kwargs


def _record_event(
    ctx: dict[str, Any], run_id: str, event_type: str, payload: dict[str, Any]
) -> None:
    """Append a ledger event without ever failing the pipeline."""
    from satsa.audit import ledger as audit_ledger

    try:
        audit_ledger.append_event(run_id, event_type, payload, **_ledger_kwargs(ctx))
    except Exception:
        pass


def _write_partial_manifest(
    run_id: str, rows: list[dict[str, Any]], run_dir: Path | None = None
) -> None:
    """Persist a partial manifest when a required stage aborts the run."""
    target = (Path(run_dir) if run_dir else WAREHOUSE_RUNS) / f"{run_id}.partial.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"run_id": run_id, "status": "aborted",
                                  "stages": rows, "completed_at": _utc_now()},
                                 indent=2, default=str) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """CLI entry: --run-id ID [--force] (module runner; cli.py untouched)."""
    parser = argparse.ArgumentParser(description="SATSA pipeline orchestrator (Phase 6)")
    parser.add_argument("--run-id", default="demo")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    import os

    os.chdir(ROOT)
    out = run_pipeline(run_id=args.run_id, force=args.force, seed=args.seed)
    return 1 if out["aborted"] else 0


if __name__ == "__main__":
    sys.exit(main())
