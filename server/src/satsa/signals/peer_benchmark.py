"""Robust peer-benchmarking engine (modified z-scores with fallbacks)."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def load_cohorts(config_dir: str | Path = "configs") -> dict[str, Any]:
    """Load peer cohort definitions (falls back to a single global cohort)."""
    path = Path(config_dir) / "peer_cohorts.yaml"
    if not path.exists():
        return {"cohorts": [], "definitions": {}}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def cohort_for_entity(entity_id: str, config_dir: str | Path = "configs") -> str:
    """Return the cohort_id containing the entity, or 'GLOBAL'."""
    cohorts = load_cohorts(config_dir).get("cohorts", []) or []
    for cohort in cohorts:
        if entity_id in (cohort.get("members", []) or []):
            return str(cohort.get("cohort_id", "GLOBAL"))
    return "GLOBAL"


def modified_z(value: float, peers: list[float]) -> dict[str, Any]:
    """Compute the modified z-score with MAD → IQR → range → skip fallbacks.

    Returns value, median, mad, modified_z, method. Ties are handled naturally
    by the MAD formula; a zero range logs WARNING and yields z=0.0 (skip).
    """
    series = pd.Series([float(v) for v in peers], dtype=float).dropna()
    median = float(series.median()) if len(series) else float(value)
    mad = float((series - median).abs().median()) if len(series) else 0.0
    if mad > 0:
        return {
            "value": float(value),
            "median": median,
            "mad": mad,
            "modified_z": float(0.6745 * (value - median) / mad),
            "method": "MAD",
        }
    iqr = float(series.quantile(0.75) - series.quantile(0.25)) if len(series) else 0.0
    if iqr > 0:
        return {
            "value": float(value),
            "median": median,
            "mad": mad,
            "modified_z": float(0.7413 * (value - median) / iqr),
            "method": "IQR",
        }
    span = float(series.max() - series.min()) if len(series) else 0.0
    if span > 0:
        return {
            "value": float(value),
            "median": median,
            "mad": mad,
            "modified_z": float((value - median) / span),
            "method": "RANGE",
        }
    warnings.warn("zero dispersion peer group; skipped", UserWarning, stacklevel=2)
    return {
        "value": float(value),
        "median": median,
        "mad": 0.0,
        "modified_z": 0.0,
        "method": "SKIP",
    }


def benchmark_metric(
    entity_id: str,
    metric: str,
    value: float,
    cohort_values: dict[str, float],
    config_dir: str | Path = "configs",
    min_n: int = 5,
    penalty: float = 0.20,
    max_penalty: float = 0.40,
) -> dict[str, Any]:
    """Benchmark one metric against its cohort with global fallback.

    When cohort_n < min_n (or single-member), falls back to global values,
    applies the confidence penalty, and sets cohort_too_small=True.
    """
    path = Path(config_dir) / "thresholds.yaml"
    file_cfg: dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            file_cfg = yaml.safe_load(handle) or {}
    min_n = int(file_cfg.get("peer_min_cohort_n", min_n))
    penalty = float(file_cfg.get("peer_confidence_penalty", penalty))
    max_penalty = float(file_cfg.get("peer_max_confidence_penalty", max_penalty))
    cohort_id = cohort_for_entity(entity_id, config_dir)
    members = load_cohorts(config_dir).get("cohorts", []) or []
    cohort_members = [c for c in members if str(c.get("cohort_id")) == cohort_id]
    cohort_ids: set[str] = set()
    if cohort_members:
        cohort_ids = set(cohort_members[0].get("members", []) or [])
    peers = [v for eid, v in cohort_values.items() if eid in cohort_ids and eid != entity_id]
    cohort_n = len(peers) + (1 if entity_id in cohort_ids else 0)
    too_small = bool(cohort_n < min_n)
    used_penalty = 0.0
    is_relative = True
    if too_small:
        peers = [v for eid, v in cohort_values.items() if eid != entity_id]
        used_penalty = max_penalty if cohort_n <= 1 else penalty
        is_relative = False
    stats = modified_z(value, peers if peers else [value])
    ranked = sorted([float(v) for v in (peers + [value]) if v == v])
    pct = float(ranked.index(float(value)) / max(1, len(ranked) - 1)) if len(ranked) > 1 else 0.5
    return {
        "metric": metric,
        "value": float(value),
        "median": stats["median"],
        "mad": stats["mad"],
        "modified_z": stats["modified_z"],
        "method": stats["method"],
        "percentile_rank": float(pct),
        "cohort_n": int(cohort_n),
        "cohort_id": cohort_id,
        "is_cohort_relative": bool(is_relative),
        "cohort_too_small": bool(too_small),
        "confidence_penalty": float(used_penalty),
    }
