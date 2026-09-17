"""Workflow features: state transitions, escalation, reopen, orphan, backfill."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from satsa.features._common import minutes_between, to_utc


def _phase2_thresholds(config_dir: str | Path = "configs") -> dict[str, Any]:
    """Load thresholds.yaml with Phase 2 defaults for missing keys."""
    defaults: dict[str, Any] = {
        "orphan_alert_hours": 72,
        "backfill_threshold_days": 30,
        "reopen_churn_min_reopens": 2,
    }
    path = Path(config_dir) / "thresholds.yaml"
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        for key, val in data.items():
            defaults[key] = val
    return defaults


def escalation_rate_by_severity(
    cases: pd.DataFrame, escalations: pd.DataFrame
) -> dict[str, float]:
    """Return escalated-case fraction per severity (per-entity, per-window)."""
    if cases.empty:
        return {}
    esc_ids: set[str] = set()
    if not escalations.empty and "case_id" in escalations.columns:
        if "case_id" in cases.columns or True:
            esc_ids = set(escalations["case_id"].dropna().astype(str).tolist())
    rates: dict[str, float] = {}
    for severity, group in cases.groupby("severity_norm", dropna=False):
        ids = set(group["case_id"].astype(str).tolist()) if "case_id" in group.columns else set()
        if not ids:
            rates[str(severity)] = 0.0
            continue
        rates[str(severity)] = float(len(ids & esc_ids) / max(1, len(ids)))
    return rates


def bypass_rate(cases: pd.DataFrame, escalations: pd.DataFrame) -> float:
    """Return critical cases closed with no escalation over total critical."""
    if cases.empty or "severity_norm" not in cases.columns:
        return 0.0
    critical = cases[cases["severity_norm"] == "CRITICAL"]
    if critical.empty:
        return 0.0
    esc_ids: set[str] = set()
    if not escalations.empty and "case_id" in escalations.columns:
        esc_ids = set(escalations["case_id"].dropna().astype(str).tolist())
    bypassed = critical[~critical["case_id"].astype(str).isin(esc_ids)]
    return float(len(bypassed) / max(1, len(critical)))


def tier_dwell_time(cases: pd.DataFrame, escalations: pd.DataFrame) -> dict[str, float]:
    """Return mean minutes spent at each tier before transition or closure."""
    if cases.empty:
        return {}
    frame = cases.copy()
    frame["dwell"] = minutes_between(
        frame.get("open_ts", pd.Series(pd.NaT, index=frame.index)),
        frame.get("close_ts", pd.Series(pd.NaT, index=frame.index)),
    )
    result: dict[str, float] = {}
    if "tier" in frame.columns:
        for tier, group in frame.groupby("tier", dropna=False):
            vals = pd.to_numeric(group["dwell"], errors="coerce").dropna()
            result[str(tier)] = float(vals.mean()) if len(vals) else 0.0
    return result


def reopen_rate(cases: pd.DataFrame, config_dir: str | Path = "configs") -> float:
    """Return reopened-case fraction (reopen_count >= configured minimum)."""
    if cases.empty or "reopen_count" not in cases.columns:
        return 0.0
    minimum = int(_phase2_thresholds(config_dir).get("reopen_churn_min_reopens", 2))
    return float((cases["reopen_count"] >= minimum).mean())


def duplicate_chain_depth(cases: pd.DataFrame) -> int:
    """Return max depth of is_duplicate_of chains (0 when the column is absent)."""
    if cases.empty or "is_duplicate_of" not in cases.columns:
        return 0
    parent = dict(
        zip(
            cases["case_id"].astype(str).tolist(),
            cases["is_duplicate_of"].astype(str).tolist(),
        )
    )
    max_depth = 0
    for case_id in parent:
        depth = 0
        cursor: str | None = case_id
        seen: set[str] = set()
        while cursor and parent.get(cursor, "") not in ("", "None", "nan") and cursor not in seen:
            seen.add(cursor)
            cursor = parent.get(cursor)
            depth += 1
            if depth > len(parent):
                break
        max_depth = max(max_depth, depth)
    return int(max_depth)


def orphan_cases(cases: pd.DataFrame) -> pd.DataFrame:
    """Return cases with no linked alerts."""
    if cases.empty:
        return cases.copy()

    def _linked(value: Any) -> bool:
        """Check whether an alert_ids cell links at least one alert."""
        try:
            return len(list(value or [])) > 0
        except Exception:
            return False

    mask = ~cases["alert_ids"].apply(_linked) if "alert_ids" in cases.columns else True
    return cases[mask].copy()


def orphan_alerts(
    alerts: pd.DataFrame, cases: pd.DataFrame, config_dir: str | Path = "configs"
) -> pd.DataFrame:
    """Return alerts with no linked case older than the configured X hours."""
    window_hours = float(_phase2_thresholds(config_dir).get("orphan_alert_hours", 72))
    if alerts.empty:
        return alerts.copy()
    linked: set[str] = set()
    if not cases.empty and "alert_ids" in cases.columns:
        for value in cases["alert_ids"].tolist():
            try:
                for item in value or []:
                    linked.add(str(item))
            except Exception:
                continue
    frame = alerts.copy()
    frame["_age_hours"] = minutes_between(
        frame.get("detected_ts", pd.Series(pd.NaT, index=frame.index)),
        pd.Series(pd.Timestamp.now(tz="UTC"), index=frame.index),
    ) / 60.0
    old_enough = frame["_age_hours"].isna() | (frame["_age_hours"] > window_hours)
    unlinked = ~frame["alert_id"].astype(str).isin(linked) if "alert_id" in frame.columns else True
    return frame[unlinked & old_enough].copy()


def backfill_detection(
    records: pd.DataFrame,
    event_col: str = "detected_ts",
    config_dir: str | Path = "configs",
) -> pd.DataFrame:
    """Return records where (ingest_ts - event_ts) exceeds threshold_days."""
    threshold_days = float(_phase2_thresholds(config_dir).get("backfill_threshold_days", 30))
    if records.empty or event_col not in records.columns or "ingest_ts" not in records.columns:
        return records.copy().iloc[0:0]
    frame = records.copy()
    gap_days = (
        to_utc(frame["ingest_ts"]) - to_utc(frame[event_col])
    ).dt.total_seconds() / 86400.0
    frame["_backfill_days"] = gap_days
    return frame[gap_days > threshold_days].copy()


def workflow_summary(
    cases: pd.DataFrame,
    escalations: pd.DataFrame,
    alerts: pd.DataFrame,
    config_dir: str | Path = "configs",
) -> dict[str, Any]:
    """Assemble the per-entity workflow feature summary."""
    orph_c = orphan_cases(cases)
    orph_a = orphan_alerts(alerts, cases, config_dir)
    backfilled = backfill_detection(alerts, "detected_ts", config_dir)
    total_cases = max(1, len(cases))
    return {
        "escalation_rate_by_severity": escalation_rate_by_severity(cases, escalations),
        "bypass_rate": bypass_rate(cases, escalations),
        "tier_dwell_time": tier_dwell_time(cases, escalations),
        "reopen_rate": reopen_rate(cases, config_dir),
        "duplicate_chain_depth": duplicate_chain_depth(cases),
        "orphan_case_count": int(len(orph_c)),
        "orphan_case_rate": float(len(orph_c) / total_cases),
        "orphan_alert_count": int(len(orph_a)),
        "orphan_alert_rate": float(len(orph_a) / max(1, len(alerts))),
        "backfill_count": int(len(backfilled)),
        "backfill_rate": float(len(backfilled) / max(1, len(alerts))),
    }
