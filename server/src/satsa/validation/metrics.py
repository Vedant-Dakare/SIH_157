"""Validation metrics over (entity, signal) finding sets.

All functions are pure over flagged/expected sets so unit tests share one
signal collection. Rater framing (R2): synthetic labels are rater A,
SAT-SA is rater B.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ValidationReport(BaseModel):
    """Every metric required for supervisory assessment."""

    run_id: str = ""
    generated_at: str = ""
    label_source: str = ""
    precision_at_k: dict[int, float] = Field(default_factory=dict)
    recall_by_scenario: dict[str, float] = Field(default_factory=dict)
    overall_recall: float = 0.0
    overall_precision: float = 0.0
    f1_by_family: dict[str, float] = Field(default_factory=dict)
    cohens_kappa: float = 0.0
    krippendorffs_alpha: float = 0.0
    false_positive_analysis: list[dict[str, Any]] = Field(default_factory=list)
    coverage_rate: float = 0.0
    efficiency_gain_hours_per_finding: float = 0.0
    time_to_finding: dict[str, float] = Field(default_factory=dict)
    n_expected: int = 0
    n_flagged: int = 0
    n_hits: int = 0


def rank_findings(
    flagged: set[tuple[str, str]], details: dict[tuple[str, str], tuple[str, float]]
) -> list[tuple[str, str]]:
    """Rank by severity weight desc, then score desc, then ids (deterministic)."""
    order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}
    return sorted(
        flagged,
        key=lambda item: (-order.get(str(details.get(item, ("INFO", 0.0))[0]), 0),
                          -float(details.get(item, ("INFO", 0.0))[1]),
                          item[0], item[1]),
    )


def precision_at_k(
    ranked: list[tuple[str, str]], expected: set[tuple[str, str]], ks: tuple[int, ...] = (5, 10, 20)
) -> dict[int, float]:
    """Precision within the top-k ranked findings per k."""
    out: dict[int, float] = {}
    for k in ks:
        top = ranked[:k]
        out[k] = float(sum(1 for item in top if item in expected) / max(1, len(top)))
    return out


def recall_by_scenario(
    expected_by_scenario: dict[str, set[tuple[str, str]]], flagged: set[tuple[str, str]]
) -> dict[str, float]:
    """Recall per scenario; scenarios with no positives score 1.0 (vacuous)."""
    out: dict[str, float] = {}
    for scenario, items in expected_by_scenario.items():
        if not items:
            out[scenario] = 1.0
            continue
        out[scenario] = float(sum(1 for item in items if item in flagged) / len(items))
    return out


def family_scores(
    flagged: set[tuple[str, str]],
    expected: set[tuple[str, str]],
    family_of: dict[str, str],
    default_family: str = "execution_gap",
) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    """Precision, recall and F1 per signal family."""
    families = {family_of.get(signal, default_family) for entity, signal in flagged | expected}
    precision: dict[str, float] = {}
    recall: dict[str, float] = {}
    f1: dict[str, float] = {}
    for family in sorted(families):
        pred = {item for item in flagged if family_of.get(item[1], default_family) == family}
        actual = {item for item in expected if family_of.get(item[1], default_family) == family}
        hits = len(pred & actual)
        precision[family] = float(hits / len(pred)) if pred else 1.0
        recall[family] = float(hits / len(actual)) if actual else 1.0
        denom = precision[family] + recall[family]
        f1[family] = float(2 * precision[family] * recall[family] / denom) if denom else 0.0
    return precision, recall, f1


def cohens_kappa(cells: list[tuple[bool, bool]]) -> float:
    """Cohen's kappa over paired rater decisions (clamped to [-1, 1])."""
    n = len(cells)
    if n == 0:
        return 0.0
    agree = sum(1 for a, b in cells if a == b)
    observed = agree / n
    p_true = sum(1 for a, _ in cells if a) / n
    q_true = sum(1 for _, b in cells if b) / n
    chance = p_true * q_true + (1 - p_true) * (1 - q_true)
    if chance >= 1.0:
        return 1.0 if observed >= 1.0 else 0.0
    return float(max(-1.0, min(1.0, (observed - chance) / (1 - chance))))


def krippendorffs_alpha(cells: list[tuple[bool, bool]]) -> float:
    """Krippendorff's nominal alpha for two raters (0 when undefined)."""
    from collections import Counter

    pairable = [(a, b) for a, b in cells]
    total = 2 * len(pairable)
    if total == 0:
        return 0.0
    coincidences: Counter[tuple[bool, bool]] = Counter()
    for a, b in pairable:
        coincidences[(a, b)] += 1
        coincidences[(b, a)] += 1
    ordered = 2 * len(pairable)
    observed = float(coincidences[(True, False)] + coincidences[(False, True)]) / ordered
    marginals: Counter[bool] = Counter()
    for a, b in pairable:
        marginals[a] += 1
        marginals[b] += 1
    chance = 2 * float(marginals[True] / total) * float(marginals[False] / total)
    if chance <= 0:
        return 1.0 if observed <= 0 else 0.0
    return float(max(-1.0, min(1.0, 1 - observed / chance)))
