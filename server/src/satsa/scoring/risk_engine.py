"""Entity supervisory risk: transparent weighted composite (ADR-004).

domain_score = max(severity_weighted_signal_scores) * (1 - exp(-k * n_flagged))
overall      = sum(domain_weight * domain_score) over the seven domains.

Module runner (cli.py untouched): python -m satsa.scoring.risk_engine
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from satsa.scoring._config import domain_of, domain_weights, load_scoring_config, severity_weight
from satsa.scoring.confidence import assess_confidence


def _clamp01(value: Any) -> float:
    """Coerce to a finite 0-1 float (never leaks NaN)."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    if result != result or result in (float("inf"), float("-inf")):
        return 0.0
    return float(max(0.0, min(1.0, result)))


def signal_contribution(result: Any) -> float:
    """Severity-weighted 0-100 contribution of one flagged signal."""
    if not bool(getattr(result, "is_flagged", False)):
        return 0.0
    if bool(getattr(result, "insufficient_data", False)):
        return 0.0
    score = _clamp01(getattr(result, "score", 0.0))
    weight = severity_weight(str(getattr(result, "severity", "INFO")))
    return float(score * weight * 100.0)


def domain_score(contributions: list[float], k: float) -> float:
    """Max severity-weighted score dampened by breadth of evidence."""
    flagged = [c for c in contributions if c > 0]
    if not flagged:
        return 0.0
    breadth = 1.0 - math.exp(-k * len(flagged))
    return float(max(flagged) * breadth)


def assign_band(score: float, config: dict[str, Any]) -> str:
    """Map 0-100 to LOW | MODERATE | ELEVATED | HIGH via thresholds.yaml."""
    low = float(config.get("risk_band_low", 25.0))
    moderate = float(config.get("risk_band_moderate", 50.0))
    elevated = float(config.get("risk_band_elevated", 75.0))
    if score >= elevated:
        return "HIGH"
    if score >= moderate:
        return "ELEVATED"
    if score >= low:
        return "MODERATE"
    return "LOW"


def score_entity(
    entity_id: str,
    results: dict[str, Any],
    frames: dict[str, Any],
    features: dict[str, float],
    run_id: str = "demo",
    window: str = "",
    seed: int = 42,
    config_dir: str | Path = "configs",
    data_root: str | Path = "data",
    synthetic_root: str | Path = "data/synthetic",
) -> dict[str, Any]:
    """Score one entity with full domain → signal → evidence decomposition."""
    _ = seed  # Scoring is deterministic; seed documents the run.
    config = load_scoring_config(config_dir)
    weights = domain_weights(config_dir)
    k = float(config.get("risk_breadth_k", 0.8))

    by_domain: dict[str, list[tuple[str, float]]] = {domain: [] for domain in weights}
    for signal_id, result in results.items():
        by_domain.setdefault(domain_of(signal_id), []).append(
            (signal_id, signal_contribution(result))
        )
    domain_scores: dict[str, float] = {}
    domain_members: dict[str, list[str]] = {}
    for domain in weights:
        members = by_domain.get(domain, [])
        domain_scores[domain] = domain_score([c for _, c in members], k)
        domain_members[domain] = [sid for sid, c in members if c > 0]

    contributions = {d: weights[d] * s for d, s in domain_scores.items()}
    raw_overall = float(sum(contributions.values()))
    calibrated_score, calibrated = _calibrated_score(raw_overall)
    band = assign_band(raw_overall, config)
    confidence = assess_confidence(
        entity_id, frames, results, features, config_dir, data_root, synthetic_root
    )
    flagged = [sid for sid, r in results.items() if bool(getattr(r, "is_flagged", False))]
    window_label = window or _window_of(results)
    return {
        "entity_id": entity_id,
        "run_id": run_id,
        "window": window_label,
        "domain_scores": {d: float(s) for d, s in domain_scores.items()},
        "domain_contributions": {d: float(c) for d, c in contributions.items()},
        "domain_members": domain_members,
        "domain_weights": dict(weights),
        "overall_score": float(raw_overall),
        "calibrated_score": float(calibrated_score),
        "band": band,
        "confidence": confidence.level,
        "confidence_reason": confidence.reason,
        "n_signals_flagged": int(len(flagged)),
        "flagged_signals": sorted(flagged),
        "data_completeness": float(confidence.data_completeness),
        "capped_by_completeness": bool(confidence.capped_by_completeness),
        "calibrated": bool(calibrated),
        "computed_at": datetime.now(UTC).isoformat(),
    }


def _calibrated_score(raw: float) -> tuple[float, bool]:
    """Map raw 0-100 through the Phase 3 calibrator when available.

    overall_score stays the transparent composite (ADR-004); the supervised
    mapping is reported separately so calibrated:true is never silent.
    """
    try:
        from satsa.features.entity_features import FEATURE_SCHEMA
        from satsa.ml.calibration import calibrate_scores

        out = calibrate_scores([float(raw) / 100.0], FEATURE_SCHEMA)
        if out.get("calibrated"):
            return float(out["calibrated_scores"][0]), True
    except Exception:
        pass
    return float(max(0.0, min(100.0, raw))), False


def _window_of(results: dict[str, Any]) -> str:
    """Derive window label from the first result (fallback when unknown)."""
    for result in results.values():
        start = getattr(result, "window_start", "")
        end = getattr(result, "window_end", "")
        if start or end:
            return f"{start}..{end}"
    return "unknown"


def score_all(
    run_id: str = "demo",
    synthetic_root: str | Path = "data/synthetic",
    seed: int = 42,
    config_dir: str | Path = "configs",
) -> dict[str, Any]:
    """Score every corpus entity; split main ranking from insufficient queue."""
    from satsa.signals.runner import build_all_features, list_entities, load_entity, run_entity

    config = load_scoring_config(config_dir)
    low_cap = float(config.get("completeness_low_cap", 0.6))
    features = build_all_features(synthetic_root)
    records: dict[str, dict[str, Any]] = {}
    for entity_id in list_entities(synthetic_root):
        frames = load_entity(entity_id, synthetic_root)
        results = run_entity(entity_id, features, synthetic_root, run_id)
        records[entity_id] = score_entity(
            entity_id, results, frames, features.get(entity_id, {}),
            run_id=run_id, seed=seed, config_dir=config_dir,
            synthetic_root=synthetic_root,
        )
    main = sorted(
        (r for r in records.values() if r["data_completeness"] >= low_cap),
        key=lambda r: r["overall_score"],
        reverse=True,
    )
    insufficient = sorted(
        (r for r in records.values() if r["data_completeness"] < low_cap),
        key=lambda r: r["overall_score"],
        reverse=True,
    )
    return {
        "run_id": run_id,
        "records": records,
        "ranking": main,
        "insufficient_queue": insufficient,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry: --run-id ID [--top N] (module runner; cli.py untouched)."""
    parser = argparse.ArgumentParser(description="SATSA risk scoring runner (Phase 4)")
    parser.add_argument("--run-id", default="demo")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    out = score_all(run_id=args.run_id, seed=args.seed)
    print(f"run {out['run_id']}: {len(out['records'])} entities scored")
    for record in out["ranking"][: args.top]:
        print(
            f"  {record['entity_id']}: {record['overall_score']:.1f} "
            f"{record['band']} conf={record['confidence']} "
            f"flagged={record['n_signals_flagged']}"
        )
    if out["insufficient_queue"]:
        print("insufficient-evidence queue (excluded from ranking):")
        for record in out["insufficient_queue"]:
            print(f"  {record['entity_id']}: completeness={record['data_completeness']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
