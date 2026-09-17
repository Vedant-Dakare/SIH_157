"""Expert-agreement analysis: disagreements with full evidence for adjudication.

Thresholds are NEVER auto-tuned: adjudication feedback is recorded for
human review and manual thresholds.yaml edits (ADR-009).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from satsa.validation.benchmark import ExpertLabel, expected_set

ADJUDICATIONS_PATH = Path("data/curated/validation/adjudications.jsonl")


class Disagreement(BaseModel):
    """One SAT-SA/expert disagreement with its evidence bundle."""

    disagreement_id: str = ""
    direction: Literal["sat_sa_only", "expert_only"] = "sat_sa_only"
    entity_id: str = ""
    signal_id: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)


class AdjudicationFeedback(BaseModel):
    """Human verdict on one disagreement (threshold edits stay manual)."""

    disagreement_id: str = Field(min_length=1)
    adjudicated_by: str = Field(min_length=1)
    adjudicated_at: str = ""
    verdict: Literal["SAT_SA_CORRECT", "EXPERT_CORRECT", "BOTH_WRONG", "INCONCLUSIVE"] = (
        "INCONCLUSIVE"
    )
    threshold_adjustment: float | None = None


def _bundle_for(
    entity_id: str, signal_id: str, results_by_entity: dict[str, Any]
) -> dict[str, Any]:
    """Full evidence bundle for a finding (flagged or not)."""
    from satsa.signals.registry import get_signal

    results = results_by_entity.get(entity_id, {})
    result = results.get(signal_id)
    if result is None:
        return {"supporting_rows": [], "counter_rows": [],
                "counter_rows_absent_reason": "signal did not compute for this entity",
                "evidence_id": "", "cohort_comparison": {}}
    signal = get_signal(signal_id)
    bundle = None
    if signal is not None:
        try:
            bundle = signal.evidence(result)
        except Exception:
            bundle = None
    if bundle is None:
        return {"supporting_rows": [], "counter_rows": [],
                "counter_rows_absent_reason": "no evidence available",
                "evidence_id": "", "cohort_comparison": {}}
    return {
        "supporting_rows": [dict(r) for r in (bundle.supporting_rows or [])],
        "counter_rows": [dict(r) for r in (bundle.counter_rows or [])],
        "counter_rows_absent_reason": str(bundle.counter_none_reason or ""),
        "evidence_id": str(bundle.evidence_id or ""),
        "cohort_comparison": dict(bundle.cohort_comparison or {}),
    }


def build_disagreements(
    flagged: set[tuple[str, str]],
    labels: list[ExpertLabel],
    results_by_entity: dict[str, Any],
) -> tuple[list[Disagreement], list[Disagreement]]:
    """Split disagreements into sat_sa_only and expert_only (disjoint)."""
    expected = expected_set(labels)
    sat_sa_only: list[Disagreement] = []
    expert_only: list[Disagreement] = []
    for entity_id, signal_id in sorted(flagged - expected):
        sat_sa_only.append(Disagreement(
            disagreement_id=f"sat_sa_only:{entity_id}:{signal_id}",
            direction="sat_sa_only", entity_id=entity_id, signal_id=signal_id,
            evidence=_bundle_for(entity_id, signal_id, results_by_entity)))
    for entity_id, signal_id in sorted(expected - flagged):
        expert_only.append(Disagreement(
            disagreement_id=f"expert_only:{entity_id}:{signal_id}",
            direction="expert_only", entity_id=entity_id, signal_id=signal_id,
            evidence=_bundle_for(entity_id, signal_id, results_by_entity)))
    return sat_sa_only, expert_only


def record_adjudication(
    feedback: AdjudicationFeedback, path: str | Path = ADJUDICATIONS_PATH
) -> Path:
    """Append one adjudication verdict (human-driven; never auto-tunes)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not feedback.adjudicated_at:
        feedback.adjudicated_at = datetime.now(UTC).isoformat()
    with target.open("a", encoding="utf-8") as handle:
        handle.write(feedback.model_dump_json() + "\n")
    return target


def read_adjudications(path: str | Path = ADJUDICATIONS_PATH) -> list[AdjudicationFeedback]:
    """Read recorded adjudications (empty when none)."""
    target = Path(path)
    if not target.exists():
        return []
    out: list[AdjudicationFeedback] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(AdjudicationFeedback(**json.loads(line)))
    return out
