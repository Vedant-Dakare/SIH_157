"""Pipeline runner: features + all signals + composites + anomaly per entity.

New in Phase 2. Kept separate from cli.py (a Phase 0+1 file) on purpose:
`python -m satsa.signals.runner --cse-id <id>` is the Phase 2 entry point.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from rich import print as rprint

from satsa.features.entity_features import PEER_Z_METRICS, build_entity_features
from satsa.signals._config import load_thresholds
from satsa.signals.anomaly import ensemble_scores, feature_contributions, top_contributors
from satsa.signals.base import SignalContext
from satsa.signals.composite import evaluate_composite
from satsa.signals.registry import (
    composite_rules,
    generate_catalogue,
    get_enabled_signals,
    validate_schema,
)

TABLES = ["alerts", "cases", "investigations", "escalations", "assets", "telemetry"]


def load_entity(
    entity_id: str, synthetic_root: str | Path = "data/synthetic"
) -> dict[str, pd.DataFrame]:
    """Load the six canonical tables for one entity (empty-safe)."""
    frames: dict[str, pd.DataFrame] = {}
    for table in TABLES:
        path = Path(synthetic_root) / entity_id / f"{table}.parquet"
        if not path.exists():
            frames[table] = pd.DataFrame()
            continue
        frame = pd.read_parquet(path)
        if set(frame.columns) == {"_empty"}:
            frame = pd.DataFrame()
        frames[table] = frame
    return frames


def list_entities(synthetic_root: str | Path = "data/synthetic") -> list[str]:
    """List entity ids with parquet corpora on disk."""
    root = Path(synthetic_root)
    if not root.exists():
        return []
    return sorted(
        p.name for p in root.iterdir() if p.is_dir() and (p / "alerts.parquet").exists()
    )


def build_all_features(
    synthetic_root: str | Path = "data/synthetic",
) -> dict[str, dict[str, float]]:
    """Build entity feature vectors for every corpus entity."""
    from satsa.features.entity_features import FEATURE_SCHEMA

    validate_schema(FEATURE_SCHEMA)
    features: dict[str, dict[str, float]] = {}
    for entity_id in list_entities(synthetic_root):
        frames = load_entity(entity_id, synthetic_root)
        features[entity_id] = build_entity_features(
            entity_id,
            frames["alerts"],
            frames["cases"],
            frames["investigations"],
            frames["escalations"],
            frames["assets"],
            frames["telemetry"],
        )
    return features


def _cohort_features(
    target: str, features: dict[str, dict[str, float]]
) -> dict[str, list[float]]:
    """Assemble peer value lists for quartile/cohort-aware signals."""
    extra = ["closure_rate", "reopen_rate", "root_cause_rate"]
    extra += ["category_missing_count", "night_fraction"]
    cohort: dict[str, list[float]] = {}
    for metric in PEER_Z_METRICS + extra:
        cohort[metric] = []
    for entity_id, feats in features.items():
        if entity_id == target:
            continue
        for metric in cohort:
            cohort[metric].append(float(feats.get(metric, 0.0)))
    return cohort


def make_context(
    entity_id: str,
    frames: dict[str, pd.DataFrame],
    features: dict[str, dict[str, float]],
    run_id: str = "phase2-run",
) -> SignalContext:
    """Assemble the SignalContext for one entity."""
    config = load_thresholds()
    alerts = frames.get("alerts", pd.DataFrame())
    window_start, window_end = "2024-05-02", "2024-06-01"
    if not alerts.empty and "detected_ts" in alerts.columns:
        try:
            times = pd.to_datetime(alerts["detected_ts"], utc=True).dropna()
            if len(times):
                window_start = str(times.min().date())
                window_end = str(times.max().date())
        except Exception:
            pass
    return SignalContext(
        entity_id=entity_id,
        run_id=run_id,
        window_start=window_start,
        window_end=window_end,
        features=features.get(entity_id, {}),
        alerts=frames.get("alerts", pd.DataFrame()),
        cases=frames.get("cases", pd.DataFrame()),
        investigations=frames.get("investigations", pd.DataFrame()),
        escalations=frames.get("escalations", pd.DataFrame()),
        assets=frames.get("assets", pd.DataFrame()),
        telemetry=frames.get("telemetry", pd.DataFrame()),
        cohort_stats={},
        cohort_features=_cohort_features(entity_id, features),
        config=config,
    )


def run_entity(
    entity_id: str,
    features: dict[str, dict[str, float]] | None = None,
    synthetic_root: str | Path = "data/synthetic",
    run_id: str = "phase2-run",
) -> dict[str, Any]:
    """Run every enabled signal plus composites for one entity."""
    features = features if features is not None else build_all_features(synthetic_root)
    frames = load_entity(entity_id, synthetic_root)
    ctx = make_context(entity_id, frames, features, run_id)
    results: dict[str, Any] = {}
    for signal in get_enabled_signals():
        try:
            results[signal.id] = signal.compute(ctx)
        except Exception as exc:
            results[signal.id] = signal.insufficient(ctx, 0, 1.0)
            results[signal.id].metadata["compute_error"] = str(exc)[:200]
    assets = frames.get("assets", pd.DataFrame())
    high_band = False
    if not assets.empty and "criticality" in assets.columns:
        crit_upper = assets["criticality"].astype(str).str.upper()
        high_band = bool((crit_upper == "HIGH").any())
    for comp_id in composite_rules():
        try:
            results[comp_id] = evaluate_composite(comp_id, results, ctx, high_band=high_band)
        except Exception as exc:
            fallback = evaluate_composite(comp_id, {}, ctx, high_band=False)
            fallback.metadata["compute_error"] = str(exc)[:200]
            results[comp_id] = fallback
    return results


def _is_fired(result: Any) -> bool:
    """Check whether a rule result is a genuine (non-insufficient) finding."""
    return bool(getattr(result, "is_flagged", False)) and not bool(
        getattr(result, "insufficient_data", False)
    )


def run_anomaly(
    features: dict[str, dict[str, float]] | None = None,
    synthetic_root: str | Path = "data/synthetic",
    rule_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Run the anomaly ensemble with ablation contributions and paired signals."""
    from satsa.features.entity_features import FEATURE_SCHEMA

    features = features if features is not None else build_all_features(synthetic_root)
    entities = sorted(features.keys())
    frame = pd.DataFrame(
        [[float(features[e].get(c, 0.0)) for c in FEATURE_SCHEMA] for e in entities],
        columns=FEATURE_SCHEMA,
    )
    scores = ensemble_scores(frame)
    contributions = feature_contributions(frame)
    output: dict[str, dict[str, Any]] = {}
    order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
    for i, entity_id in enumerate(entities):
        contrib = contributions[i] if i < len(contributions) else {}
        paired: str | None = None
        if rule_results and entity_id in rule_results:
            unenriched = rule_results[entity_id].values()
            fired = [r for r in unenriched if _is_fired(r)]
            if fired:
                top = max(fired, key=lambda r: (order.get(r.severity, 0), r.score))
                paired = top.signal_id
            else:
                scored = [r for r in unenriched if not getattr(r, "insufficient_data", False)]
                if scored:
                    paired = max(scored, key=lambda r: r.score).signal_id
        output[entity_id] = {
            "anomaly_score": float(scores["anomaly_score"][i]),
            "anomaly_rank": int(scores["anomaly_rank"][i]),
            "top5_contributing_features": top_contributors(contrib),
            "contributions": {k: float(v) for k, v in contrib.items()},
            "paired_signal_id": paired,
        }
    return output


def run_all(
    synthetic_root: str | Path = "data/synthetic", run_id: str = "phase2-run"
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Run rule signals and the anomaly ensemble for every entity."""
    features = build_all_features(synthetic_root)
    rule_results = {e: run_entity(e, features, synthetic_root, run_id) for e in features}
    anomaly_results = run_anomaly(features, synthetic_root, rule_results)
    return rule_results, anomaly_results


def main(argv: list[str] | None = None) -> int:
    """CLI entry: --cse-id ID | --all | --catalogue."""
    parser = argparse.ArgumentParser(description="SATSA Phase 2 signal runner")
    parser.add_argument("--cse-id", default=None, help="Run signals for one CSE id")
    parser.add_argument("--all", action="store_true", help="Run signals for all CSEs")
    parser.add_argument("--catalogue", action="store_true", help="Regenerate catalogue")
    args = parser.parse_args(argv)
    if args.catalogue or (not args.cse_id and not args.all):
        path = generate_catalogue()
        rprint(f"catalogue written to {path}")
    if args.cse_id:
        results = run_entity(args.cse_id)
        flagged = [rid for rid, res in results.items() if getattr(res, "is_flagged", False)]
        rprint(f"{args.cse_id}: {len(flagged)} flagged: {sorted(flagged)}")
    elif args.all:
        rule_results, anomaly_results = run_all()
        for entity_id, results in sorted(rule_results.items()):
            flagged = [r for r in results if results[r].is_flagged]
            rprint(f"{entity_id}: {len(flagged)} flagged: {sorted(flagged)}")
        for entity_id, anomaly in sorted(anomaly_results.items()):
            score = float(anomaly["anomaly_score"])
            rprint(f"{entity_id}: anomaly={score:.3f} paired={anomaly['paired_signal_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
