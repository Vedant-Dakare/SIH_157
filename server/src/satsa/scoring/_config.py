"""Phase 4 scoring configuration: thresholds.yaml with documented defaults.

New files only — prior-phase config files are never modified. Every key
falls back to the documented default below when absent from
configs/thresholds.yaml or configs/signals.yaml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    # Risk aggregation (ADR-004)
    "risk_breadth_k": 0.8,
    "risk_band_low": 25.0,
    "risk_band_moderate": 50.0,
    "risk_band_elevated": 75.0,
    # Prioritisation
    "novelty_prior_runs": 2,
    "novelty_downweight": 0.4,
    "coverage_gap_days": 30,
    "coverage_gap_weight": 1.25,
    "sample_top_k": 5,
    "avg_review_minutes": 10,
    # Confidence / sampling plumbing
    "signal_min_n": 5,
    "peer_min_cohort_n": 5,
    "completeness_low_cap": 0.6,
    "completeness_high": 0.9,
    "completeness_medium": 0.7,
}

DEFAULT_DOMAIN_WEIGHTS: dict[str, float] = {
    "detection_coverage": 0.20,
    "investigation_quality": 0.20,
    "escalation_integrity": 0.15,
    "operational_discipline": 0.15,
    "governance": 0.10,
    "peer_divergence": 0.10,
    "negative_space": 0.10,
}

SEVERITY_WEIGHTS: dict[str, float] = {
    "CRITICAL": 1.0,
    "HIGH": 0.85,
    "MEDIUM": 0.60,
    "LOW": 0.35,
    "INFO": 0.15,
    "UNKNOWN": 0.30,
}

# Every rule + composite signal belongs to exactly one domain.
SIGNAL_DOMAINS: dict[str, str] = {
    "EG-001": "operational_discipline",
    "EG-002": "investigation_quality",
    "EG-003": "escalation_integrity",
    "EG-004": "escalation_integrity",
    "EG-005": "detection_coverage",
    "EG-006": "operational_discipline",
    "EG-007": "governance",
    "EG-008": "operational_discipline",
    "EG-009": "investigation_quality",
    "EG-010": "investigation_quality",
    "EG-011": "investigation_quality",
    "EG-012": "investigation_quality",
    "EG-013": "operational_discipline",
    "EG-014": "escalation_integrity",
    "NS-001": "detection_coverage",
    "NS-002": "detection_coverage",
    "NS-003": "peer_divergence",
    "NS-004": "peer_divergence",
    "NS-005": "detection_coverage",
    "NS-006": "negative_space",
    "NS-007": "negative_space",
    "NS-008": "negative_space",
    "NS-009": "detection_coverage",
    "NS-010": "negative_space",
    "NS-011": "negative_space",
    "NS-012": "negative_space",
    "COMP-001": "governance",
    "COMP-002": "governance",
    "COMP-003": "governance",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning {} when absent or unreadable."""
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    except Exception:
        return {}


def load_scoring_config(config_dir: str | Path = "configs") -> dict[str, Any]:
    """Merge thresholds.yaml over Phase 4 defaults (never crashes)."""
    merged = dict(DEFAULTS)
    data = _load_yaml(Path(config_dir) / "thresholds.yaml")
    for key, val in data.items():
        merged[key] = val
    return merged


def domain_weights(config_dir: str | Path = "configs") -> dict[str, float]:
    """Read risk weights from signals.yaml, defaulting to ADR-004 weights."""
    weights = dict(DEFAULT_DOMAIN_WEIGHTS)
    data = _load_yaml(Path(config_dir) / "signals.yaml")
    custom = data.get("risk_weights")
    if isinstance(custom, dict):
        for domain, weight in custom.items():
            if domain in weights:
                try:
                    weights[domain] = float(weight)
                except (TypeError, ValueError):
                    continue
    total = sum(weights.values())
    if total <= 0:
        return dict(DEFAULT_DOMAIN_WEIGHTS)
    return {domain: weight / total for domain, weight in weights.items()}


def domain_of(signal_id: str) -> str:
    """Return the domain for a signal id (unknown ids map to governance)."""
    return SIGNAL_DOMAINS.get(signal_id, "governance")


def severity_weight(severity: str) -> float:
    """Return the 0-1 severity weight (unknown severities map to 0.30)."""
    return SEVERITY_WEIGHTS.get(str(severity).upper(), 0.30)
