"""Manual-review queue: utility-ranked prioritisation with deterministic sampling.

priority = risk_score * confidence_weight * novelty_weight * coverage_gap_weight

Module runner (cli.py untouched): python -m satsa.scoring.prioritisation
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from satsa.scoring._config import load_scoring_config
from satsa.scoring.confidence import ledger_findings

CONFIDENCE_WEIGHTS = {"HIGH": 1.0, "MEDIUM": 0.75, "LOW": 0.5}

LEDGER_PATH = Path("data/scoring/ledger.json")


def _parse_ts(value: Any) -> datetime | None:
    """Parse an ISO timestamp, returning None when unparseable."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def novelty_weight(
    entity_id: str,
    ledger: dict[str, Any],
    prior_runs: int = 2,
    downweight: float = 0.4,
) -> float:
    """Downweight findings surfaced in N prior consecutive runs (R1: 1.0 first run).

    Stale findings decay geometrically: downweight^(streak - N + 1) once the
    streak reaches N, so long-surfaced items keep sinking while new items rank.
    """
    runs = ledger.get("runs", []) if isinstance(ledger, dict) else []
    if not runs:
        return 1.0
    consecutive = 0
    for run in reversed(runs):
        findings = run.get("findings", {}) if isinstance(run, dict) else {}
        if entity_id in findings and findings[entity_id]:
            consecutive += 1
        else:
            break
    if consecutive >= prior_runs:
        return float(downweight ** (consecutive - prior_runs + 1))
    return 1.0


def coverage_gap_weight(
    entity_id: str,
    ledger: dict[str, Any],
    gap_days: int = 30,
    upweight: float = 1.25,
    now: datetime | None = None,
) -> float:
    """Upweight entities unreviewed for more than M days (never-reviewed counts)."""
    current = now or datetime.now(UTC)
    last = (ledger.get("last_reviewed", {}) if isinstance(ledger, dict) else {}).get(entity_id)
    reviewed = _parse_ts(last)
    if reviewed is None:
        return float(upweight)
    if (current - reviewed).days > gap_days:
        return float(upweight)
    return 1.0


def _seeded_order(ids: list[str], seed: int, salt: str) -> list[str]:
    """Deterministically order ids by hash(seed + salt + id)."""
    keyed = [
        (hashlib.sha256(f"{seed}|{salt}|rid".encode()).hexdigest(), rid) for rid in ids
    ]
    return [rid for _, rid in sorted(keyed)]


def sample_ids(
    signal_id: str,
    bundle: Any,
    alerts_table: Any,
    seed: int,
    top_k: int,
) -> tuple[list[str], list[str]]:
    """Select up to K representative alert/case IDs (deterministic, stratified).

    Drawn from the signal's supporting evidence rows and validated against
    the canonical alerts table; falls back to evidence ids when the table is
    unavailable.
    """
    rows = list(getattr(bundle, "supporting_rows", []) or []) if bundle else []
    alert_ids = [str(r["alert_id"]) for r in rows if isinstance(r, dict) and r.get("alert_id")]
    case_ids = [str(r["case_id"]) for r in rows if isinstance(r, dict) and r.get("case_id")]
    valid_alerts: set[str] = set()
    if alerts_table is not None and hasattr(alerts_table, "columns"):
        try:
            if "alert_id" in alerts_table.columns:
                valid_alerts = set(alerts_table["alert_id"].astype(str).tolist())
        except Exception:
            valid_alerts = set()
    if valid_alerts:
        alert_ids = [a for a in alert_ids if a in valid_alerts]
    ordered_alerts = _seeded_order(list(dict.fromkeys(alert_ids)), seed, signal_id + ":alert")
    ordered_cases = _seeded_order(list(dict.fromkeys(case_ids)), seed, signal_id + ":case")
    return ordered_alerts[:top_k], ordered_cases[:top_k]


def build_queue(
    scored: dict[str, dict[str, Any]],
    results_by_entity: dict[str, dict[str, Any]],
    bundles_by_entity: dict[str, dict[str, Any]],
    frames_by_entity: dict[str, dict[str, Any]],
    ledger: dict[str, Any] | None = None,
    seed: int = 42,
    config_dir: str | Path = "configs",
) -> list[dict[str, Any]]:
    """Rank main-queue entities by utility; attach focus area and samples."""
    ledger = ledger if isinstance(ledger, dict) else {}
    config = load_scoring_config(config_dir)
    prior_runs = int(config.get("novelty_prior_runs", 2))
    downweight = float(config.get("novelty_downweight", 0.4))
    gap_days = int(config.get("coverage_gap_days", 30))
    gap_weight = float(config.get("coverage_gap_weight", 1.25))
    top_k = int(config.get("sample_top_k", 5))
    avg_minutes = int(config.get("avg_review_minutes", 10))

    queue: list[dict[str, Any]] = []
    for entity_id in sorted(scored):
        record = scored[entity_id]
        conf_w = CONFIDENCE_WEIGHTS.get(record.get("confidence", "LOW"), 0.5)
        nov_w = novelty_weight(entity_id, ledger, prior_runs, downweight)
        cov_w = coverage_gap_weight(entity_id, ledger, gap_days, gap_weight)
        priority = float(record.get("overall_score", 0.0)) * conf_w * nov_w * cov_w
        contributions = record.get("domain_contributions", {})
        focus = max(contributions, key=lambda d: contributions[d]) if contributions else ""
        bundles = bundles_by_entity.get(entity_id, {})
        frames = frames_by_entity.get(entity_id, {})
        alerts_table = frames.get("alerts") if isinstance(frames, dict) else None
        sample_alerts: list[str] = []
        sample_cases: list[str] = []
        for signal_id in sorted(record.get("flagged_signals", [])):
            alerts, cases = sample_ids(
                signal_id, bundles.get(signal_id), alerts_table, seed, top_k
            )
            sample_alerts.extend(a for a in alerts if a not in sample_alerts)
            sample_cases.extend(c for c in cases if c not in sample_cases)
        queue.append(
            {
                "entity_id": entity_id,
                "priority": float(priority),
                "risk_score": float(record.get("overall_score", 0.0)),
                "band": record.get("band", "LOW"),
                "confidence": record.get("confidence", "LOW"),
                "focus_area": focus,
                "signal_ids": sorted(record.get("flagged_signals", [])),
                "expected_review_minutes": int(
                    max(1, len(record.get("flagged_signals", [])) * avg_minutes)
                ),
                "sample_alert_ids": sample_alerts,
                "sample_case_ids": sample_cases,
                "novelty_weight": float(nov_w),
                "coverage_gap_weight": float(cov_w),
            }
        )
    queue.sort(key=lambda e: (-e["priority"], e["entity_id"]))
    for rank, entry in enumerate(queue, start=1):
        entry["rank"] = rank
    return queue


def prioritise(
    run_id: str = "demo",
    seed: int = 42,
    synthetic_root: str | Path = "data/synthetic",
    ledger_path: str | Path = LEDGER_PATH,
    config_dir: str | Path = "configs",
    top: int = 10,
) -> dict[str, Any]:
    """Score all entities and build the main + insufficient review queues."""
    from satsa.scoring.risk_engine import score_all
    from satsa.signals.runner import build_all_features, load_entity, run_entity

    scored = score_all(
        run_id=run_id, synthetic_root=synthetic_root, seed=seed, config_dir=config_dir
    )
    features = build_all_features(synthetic_root)
    results_by: dict[str, dict[str, Any]] = {}
    bundles_by: dict[str, dict[str, Any]] = {}
    frames_by: dict[str, dict[str, Any]] = {}
    for entity_id in scored["records"]:
        frames = load_entity(entity_id, synthetic_root)
        results = run_entity(entity_id, features, synthetic_root, run_id)
        frames_by[entity_id] = frames
        results_by[entity_id] = results
        bundles: dict[str, Any] = {}
        from satsa.signals.registry import get_signal

        for signal_id, result in results.items():
            if not bool(getattr(result, "is_flagged", False)):
                continue
            try:
                signal = get_signal(signal_id)
                bundles[signal_id] = signal.evidence(result) if signal is not None else None
            except Exception:
                bundles[signal_id] = None
        bundles_by[entity_id] = bundles
    ledger = ledger_findings(ledger_path)
    main_scored = {r["entity_id"]: r for r in scored["ranking"]}
    queue = build_queue(main_scored, results_by, bundles_by, frames_by, ledger, seed, config_dir)
    return {
        "run_id": run_id,
        "queue": queue[:top],
        "full_queue": queue,
        "insufficient_queue": [r["entity_id"] for r in scored["insufficient_queue"]],
    }


def record_run(
    run_id: str,
    queue: list[dict[str, Any]],
    ledger_path: str | Path = LEDGER_PATH,
) -> dict[str, Any]:
    """Append a run to the audit ledger for novelty tracking (R1)."""
    ledger = ledger_findings(ledger_path)
    runs = ledger.get("runs", []) if isinstance(ledger, dict) else []
    now = datetime.now(UTC).isoformat()
    runs.append(
        {
            "run_id": run_id,
            "ts": now,
            "findings": {e["entity_id"]: e["signal_ids"] for e in queue},
        }
    )
    ledger = dict(ledger) if isinstance(ledger, dict) else {}
    ledger["runs"] = runs[-10:]
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return ledger


def main(argv: list[str] | None = None) -> int:
    """CLI entry: --top N [--run-id ID] (module runner; cli.py untouched)."""
    parser = argparse.ArgumentParser(description="SATSA prioritisation runner (Phase 4)")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--run-id", default="demo")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    out = prioritise(run_id=args.run_id, seed=args.seed, top=args.top)
    for entry in out["queue"]:
        print(
            f"#{entry['rank']} {entry['entity_id']}: priority={entry['priority']:.1f} "
            f"risk={entry['risk_score']:.1f} focus={entry['focus_area']} "
            f"signals={entry['signal_ids']}"
        )
    if out["insufficient_queue"]:
        print(f"insufficient-evidence (unranked): {out['insufficient_queue']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
