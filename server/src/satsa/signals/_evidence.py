"""Shared evidence-bundle helpers for concrete signals."""

from __future__ import annotations

from typing import Any

import pandas as pd

from satsa.features._common import as_dict
from satsa.signals.base import EvidenceBundle, SignalResult, _evidence_id

_MAX_ROWS = 5


def frame_rows(
    frame: Any, id_col: str, ids: list[str], limit: int = _MAX_ROWS
) -> list[dict[str, Any]]:
    """Return up to `limit` evidence rows for the given ids (or head rows)."""
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
        return []
    sub = frame
    if id_col in frame.columns and ids:
        sub = frame[frame[id_col].astype(str).isin([str(i) for i in ids])]
        if sub.empty:
            sub = frame
    return [as_dict(r) for r in sub.head(limit).to_dict(orient="records")]


def matching_rows(frame: Any, id_col: str, ids: list[str]) -> list[dict[str, Any]]:
    """Return rows whose id column matches (empty when nothing matches)."""
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
        return []
    if id_col not in frame.columns:
        return []
    sub = frame[frame[id_col].astype(str).isin([str(i) for i in ids])]
    return [as_dict(r) for r in sub.head(_MAX_ROWS).to_dict(orient="records")]


def make_bundle(
    signal_id: str,
    result: SignalResult,
    supporting: list[dict[str, Any]],
    counter: list[dict[str, Any]],
    counter_none_reason: str = "",
    cohort_comparison: dict[str, Any] | None = None,
) -> EvidenceBundle:
    """Assemble an EvidenceBundle with a deterministic evidence_id."""
    row_ids = []
    for i, row in enumerate(supporting):
        fallback = row.get("asset_id", i)
        row_ids.append(str(row.get("case_id", row.get("alert_id", fallback))))
    reason = counter_none_reason
    if not counter and not reason:
        reason = "no counter-examples in window"
    window = f"{result.window_start}..{result.window_end}"
    return EvidenceBundle(
        finding_id=result.finding_id,
        supporting_rows=supporting,
        counter_rows=counter,
        counter_none_reason="" if counter else reason,
        cohort_comparison=dict(cohort_comparison or {}),
        evidence_id=_evidence_id(signal_id, result.entity_id, window, row_ids),
    )
