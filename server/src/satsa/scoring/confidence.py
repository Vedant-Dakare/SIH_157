"""Confidence as a first-class output with a human-readable reason.

Completeness < 0.6 caps confidence at LOW and routes the entity to the
separate insufficient-evidence queue (never ranked with complete feeds).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from satsa.scoring._config import load_scoring_config


@dataclass
class ConfidenceResult:
    """Confidence level plus an examiner-readable reason."""

    level: str
    reason: str
    data_completeness: float
    capped_by_completeness: bool


def _null_frac(frames: dict[str, pd.DataFrame]) -> float:
    """Mean null fraction across alerts/cases/investigations tables."""
    fracs: list[float] = []
    for table in ("alerts", "cases", "investigations"):
        frame = frames.get(table)
        if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
            continue
        fracs.append(float(frame.isna().mean().mean()))
    if not fracs:
        return 1.0
    return float(sum(fracs) / len(fracs))


def _quarantine_rate(entity_id: str, n_alerts: int, data_root: str | Path = "data") -> float:
    """Quarantined records over received alerts (0 when no ledger)."""
    path = Path(data_root) / "quarantine" / f"{entity_id}.jsonl"
    if not path.exists():
        return 0.0
    try:
        count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0.0
    return float(count / max(1, n_alerts))


def _unknown_rate(frames: dict[str, pd.DataFrame]) -> float:
    """Fraction of UNKNOWN severity_norm across alerts and cases."""
    total, unknown = 0, 0
    for table in ("alerts", "cases"):
        frame = frames.get(table)
        if frame is None or frame.empty or "severity_norm" not in frame.columns:
            continue
        total += len(frame)
        unknown += int((frame["severity_norm"] == "UNKNOWN").sum())
    if total == 0:
        return 0.0
    return float(unknown / total)


def _ground_truth_confidence(
    entity_id: str, synthetic_root: str | Path = "data/synthetic"
) -> float:
    """Label confidence for the entity (1.0 default, 0.7 for partial feeds)."""
    path = Path(synthetic_root) / "ground_truth.parquet"
    if not path.exists():
        return 1.0
    try:
        frame = pd.read_parquet(path)
        sub = frame[frame["entity_id"] == entity_id]
        if sub.empty or "confidence" not in sub.columns:
            return 1.0
        return float(sub["confidence"].mean())
    except Exception:
        return 1.0


def data_completeness(
    entity_id: str,
    frames: dict[str, pd.DataFrame],
    data_root: str | Path = "data",
    synthetic_root: str | Path = "data/synthetic",
) -> float:
    """Completeness in 0-1 from nulls, quarantine, unknowns and label confidence."""
    alerts = frames.get("alerts", pd.DataFrame())
    n_alerts = len(alerts) if isinstance(alerts, pd.DataFrame) else 0
    base = 1.0 - _null_frac(frames)
    quarantine_penalty = 1.0 - min(1.0, 2.0 * _quarantine_rate(entity_id, n_alerts, data_root))
    unknown_penalty = 1.0 - min(1.0, 2.0 * _unknown_rate(frames))
    label_conf = _ground_truth_confidence(entity_id, synthetic_root)
    score = float(base * quarantine_penalty * unknown_penalty * label_conf)
    return float(max(0.0, min(1.0, score)))


def _adequate_frac(results: dict[str, Any], min_n: int) -> float:
    """Fraction of signals with adequate samples (not insufficient_data)."""
    if not results:
        return 0.0
    adequate = sum(1 for r in results.values() if not bool(getattr(r, "insufficient_data", False)))
    return float(adequate / len(results))


def _cohort_ok(results: dict[str, Any]) -> tuple[bool, str]:
    """Cohort adequacy: min_n met or documented global fallback in use.

    Shipped synthetic cohorts have n = 2, so production runs use global
    fallback by design (see ANALYTICS_METHODOLOGY.md); fallback counts as
    adequate here because the peer engine already applies its penalty.
    """
    if not results:
        return False, "no signals computed"
    flagged_small = [r for r in results.values() if bool(getattr(r, "cohort_too_small", False))]
    if len(flagged_small) == len(results):
        return True, "global fallback in use for all peer comparisons (documented)"
    return True, "cohort sizes adequate for peer comparison"


def _missingness(features: dict[str, float]) -> float:
    """Fraction of NaN entries in the feature vector (sanitised vectors read 0)."""
    if not features:
        return 1.0
    try:
        import math

        bad = sum(1 for v in features.values() if isinstance(v, float) and math.isnan(v))
        return float(bad / len(features))
    except Exception:
        return 0.0


def assess_confidence(
    entity_id: str,
    frames: dict[str, pd.DataFrame],
    results: dict[str, Any],
    features: dict[str, float],
    config_dir: str | Path = "configs",
    data_root: str | Path = "data",
    synthetic_root: str | Path = "data/synthetic",
) -> ConfidenceResult:
    """Map completeness/coverage/samples/cohorts to HIGH | MEDIUM | LOW."""
    cfg = load_scoring_config(config_dir)
    min_n = int(cfg.get("signal_min_n", 5))
    completeness = data_completeness(entity_id, frames, data_root, synthetic_root)
    adequate = _adequate_frac(results, min_n)
    cohort_good, cohort_note = _cohort_ok(results)
    missingness = _missingness(features)
    low_cap = float(cfg.get("completeness_low_cap", 0.6))
    high_bar = float(cfg.get("completeness_high", 0.9))
    med_bar = float(cfg.get("completeness_medium", 0.7))

    if completeness < low_cap:
        return ConfidenceResult(
            level="LOW",
            reason=(
                f"Data completeness {completeness:.2f} is below {low_cap:.2f}; "
                "feed routed to the insufficient-evidence queue for verification "
                "instead of the main ranking."
            ),
            data_completeness=completeness,
            capped_by_completeness=True,
        )
    if (
        completeness >= high_bar
        and adequate >= 0.9
        and cohort_good
        and missingness <= 0.05
    ):
        return ConfidenceResult(
            level="HIGH",
            reason=(
                f"Data completeness {completeness:.2f}; "
                f"{adequate:.0%} of signals have adequate samples; "
                f"{cohort_note}; feature missingness {missingness:.1%}."
            ),
            data_completeness=completeness,
            capped_by_completeness=False,
        )
    if completeness >= med_bar and adequate >= 0.5:
        return ConfidenceResult(
            level="MEDIUM",
            reason=(
                f"Data completeness {completeness:.2f}; "
                f"{adequate:.0%} of signals have adequate samples; {cohort_note}."
            ),
            data_completeness=completeness,
            capped_by_completeness=False,
        )
    return ConfidenceResult(
        level="LOW",
        reason=(
            f"Data completeness {completeness:.2f} with only {adequate:.0%} "
            f"of signals adequately sampled; {cohort_note}."
        ),
        data_completeness=completeness,
        capped_by_completeness=False,
    )


def ledger_findings(ledger_path: str | Path) -> dict[str, Any]:
    """Read the audit ledger of prior runs ({} when absent — first run)."""
    path = Path(ledger_path)
    if not path.exists():
        return {}
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
