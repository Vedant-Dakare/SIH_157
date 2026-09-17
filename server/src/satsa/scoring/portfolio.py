"""Portfolio views: summary bands, sector aggregates, trends, drill-down."""

from __future__ import annotations

import statistics
from pathlib import Path
from typing import Any

import yaml


def _sector_of(entity_id: str, registry_path: str | Path = "configs/entity_registry.yaml") -> str:
    """Return the sector for an entity (unknown when unregistered)."""
    try:
        with Path(registry_path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return str(data.get("entities", {}).get(entity_id, {}).get("sector", "unknown"))
    except OSError:
        return "unknown"


def portfolio_summary(
    records: dict[str, dict[str, Any]],
    prior_records: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Aggregate bands, top-5, sector medians and portfolio trend."""
    bands: dict[str, int] = {"LOW": 0, "MODERATE": 0, "ELEVATED": 0, "HIGH": 0}
    for record in records.values():
        bands[record.get("band", "LOW")] = bands.get(record.get("band", "LOW"), 0) + 1
    ranked = sorted(
        records.values(), key=lambda r: float(r.get("overall_score", 0.0)), reverse=True
    )
    by_sector: dict[str, list[float]] = {}
    for entity_id, record in records.items():
        by_sector.setdefault(_sector_of(entity_id), []).append(
            float(record.get("overall_score", 0.0))
        )
    sectors = {s: float(statistics.median(v)) for s, v in by_sector.items()}
    trend = "STABLE"
    if prior_records:
        cur_vals = [float(r.get("overall_score", 0.0)) for r in records.values()] or [0.0]
        prev_vals = [float(r.get("overall_score", 0.0)) for r in prior_records.values()] or [0.0]
        cur = statistics.median(cur_vals)
        prev = statistics.median(prev_vals)
        if cur - prev > 2.0:
            trend = "DETERIORATING"
        elif prev - cur > 2.0:
            trend = "IMPROVING"
    return {
        "entity_count_by_band": bands,
        "top_5_entities_by_risk": [r["entity_id"] for r in ranked[:5]],
        "sector_aggregates": sectors,
        "portfolio_trend": trend,
    }


def trend_analysis(
    entity_id: str,
    history: list[dict[str, Any]],
    persistent_windows: int = 2,
) -> dict[str, Any]:
    """Classify findings over current + trailing windows.

    history: oldest-first list of {window, overall_score, findings: [signal_ids]}.
    Returns per-signal NEW | PERSISTENT | RESOLVED plus entity direction and
    INSUFFICIENT_HISTORY when fewer than 2 windows are available.
    """
    if len(history) < 2:
        return {
            "entity_id": entity_id,
            "trend": "INSUFFICIENT_HISTORY",
            "signals": {},
            "direction": "UNKNOWN",
        }
    current = history[-1]
    prior = history[-2]
    cur_set = set(current.get("findings", []))
    prior_set = set(prior.get("findings", []))
    ever_set: set[str] = set()
    for w in history[:-1]:
        ever_set |= set(w.get("findings", []))
    window_back = [set(w.get("findings", [])) for w in history[-(persistent_windows + 1) : -1]]
    signals: dict[str, str] = {}
    for signal_id in sorted(cur_set | ever_set):
        if signal_id in cur_set and signal_id not in prior_set:
            signals[signal_id] = "NEW"
        elif signal_id not in cur_set:
            signals[signal_id] = "RESOLVED"
        elif all(signal_id in w for w in window_back) and signal_id in cur_set:
            signals[signal_id] = "PERSISTENT"
        else:
            signals[signal_id] = "PERSISTENT"
    scores = [float(w.get("overall_score", 0.0)) for w in history]
    direction = "STABLE"
    if len(scores) >= 2:
        if all(b < a for a, b in zip(scores, scores[1:])):
            direction = "IMPROVING"
        elif all(b > a for a, b in zip(scores, scores[1:])):
            direction = "DETERIORATING"
    return {
        "entity_id": entity_id,
        "trend": direction,
        "signals": signals,
        "direction": direction,
        "windows": len(history),
    }


def drill_down(
    entity_id: str,
    score_record: dict[str, Any],
    results: dict[str, Any],
    evidence_of: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve portfolio → entity → domain → signal → evidence rows.

    evidence_of maps signal_id to an EvidenceBundle (or None entries, which
    resolve to empty row lists rather than broken links).
    """
    evidence_of = evidence_of or {}
    domains: dict[str, Any] = {}
    for domain, members in score_record.get("domain_members", {}).items():
        signals: dict[str, Any] = {}
        for signal_id in members:
            result = results.get(signal_id)
            bundle = evidence_of.get(signal_id)
            rows = list(getattr(bundle, "supporting_rows", []) or []) if bundle else []
            signals[signal_id] = {
                "value": getattr(result, "value", None) if result else None,
                "severity": getattr(result, "severity", None) if result else None,
                "is_flagged": bool(getattr(result, "is_flagged", False)) if result else False,
                "evidence_rows": len(rows),
                "evidence_id": getattr(bundle, "evidence_id", "") if bundle else "",
            }
        domains[domain] = {
            "score": score_record.get("domain_scores", {}).get(domain, 0.0),
            "contribution": score_record.get("domain_contributions", {}).get(domain, 0.0),
            "signals": signals,
        }
    return {
        "entity_id": entity_id,
        "overall_score": score_record.get("overall_score"),
        "band": score_record.get("band"),
        "domains": domains,
    }
