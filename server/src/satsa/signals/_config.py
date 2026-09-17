"""Phase 2 shared configuration: thresholds.yaml with documented defaults.

New files only — Phase 0+1 config files are never modified. When a key is
absent from configs/thresholds.yaml or configs/signals.yaml, the documented
Phase 2 default below applies.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PHASE2_DEFAULTS: dict[str, Any] = {
    # Batch-close / premature closure
    "bulk_close_window_seconds": 60,
    "bulk_close_min_count": 50,
    "premature_close_minutes": 5,
    "premature_rate_threshold": 0.20,
    # Escalation / bypass / mismatch
    "escalation_bypass_rate_threshold": 0.90,
    "severity_mismatch_rate_threshold": 0.25,
    "escalation_nowhere_rate_threshold": 0.50,
    # SLA / backlog
    "sla_breach_hours": 72,
    "sla_breach_rate_threshold": 0.30,
    # Churn / orphans / backfill
    "reopen_churn_min_reopens": 2,
    "reopen_rate_threshold": 0.15,
    "orphan_case_rate_threshold": 0.30,
    "orphan_alert_hours": 72,
    "backfill_threshold_days": 30,
    "backfill_rate_threshold": 0.10,
    "duplicate_rate_threshold": 0.10,
    # Text
    "template_tfidf_threshold": 0.85,
    "template_min_notes": 5,
    "placeholder_rate_threshold": 0.20,
    # After-hours
    "after_hours_start": 22,
    "after_hours_end": 6,
    "after_hours_min_fraction": 0.50,
    "eg008_min_fraction": 0.50,
    "ns011_max_after_hours_fraction": 0.05,
    # EG-013 perfect-SLA
    "eg013_sla_met_pct": 0.99,
    "eg013_cv_epsilon": 0.05,
    "eg013_min_cases": 10,
    # Coverage / negative space
    "coverage_gap_min_unmonitored_assets": 1,
    "telemetry_gap_ratio_threshold": 0.10,
    "silence_streak_days_threshold": 7,
    "category_absence_z_threshold": 2.0,
    "ns012_drop_pct": 0.50,
    "ns012_trailing_windows": 4,
    # Peer benchmarking
    "peer_min_cohort_n": 5,
    "peer_z_threshold": 2.0,
    "peer_confidence_penalty": 0.20,
    "peer_max_confidence_penalty": 0.40,
    # Signal plumbing
    "signal_min_n": 5,
    "anomaly_min_entities": 4,
    "anomaly_score_threshold": 0.75,
}


def load_thresholds(config_dir: str | Path = "configs") -> dict[str, Any]:
    """Merge thresholds.yaml over Phase 2 defaults (never crashes on absence)."""
    merged = dict(PHASE2_DEFAULTS)
    path = Path(config_dir) / "thresholds.yaml"
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            for key, val in data.items():
                merged[key] = val
        except Exception:
            pass
    return merged


def signal_enabled(signal_id: str, config_dir: str | Path = "configs") -> bool:
    """Return the signals.yaml enabled flag; unknown signals default to enabled."""
    path = Path(config_dir) / "signals.yaml"
    if not path.exists():
        return True
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        signals = data.get("signals", {}) or {}
        entry = signals.get(signal_id)
        if entry is None:
            return True
        if isinstance(entry, dict):
            return bool(entry.get("enabled", True))
        return bool(entry)
    except Exception:
        return True
