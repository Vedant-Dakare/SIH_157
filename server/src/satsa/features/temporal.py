"""Temporal features: latencies, durations, batch-close bursts, time distributions."""

from __future__ import annotations

import hashlib
import warnings
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from satsa.features._common import minutes_between, safe_mean, safe_median, safe_p90, to_utc


def _phase2_thresholds(config_dir: str | Path = "configs") -> dict[str, Any]:
    """Load thresholds.yaml with Phase 2 defaults for missing keys."""
    defaults: dict[str, Any] = {
        "bulk_close_window_seconds": 60,
        "bulk_close_min_count": 50,
        "timestamp_future_tolerance_seconds": 60,
        "orphan_alert_hours": 72,
    }
    path = Path(config_dir) / "thresholds.yaml"
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        for key, val in data.items():
            defaults[key] = val
    return defaults


def alert_latency_features(
    alerts: pd.DataFrame, config_dir: str | Path = "configs"
) -> pd.DataFrame:
    """Compute per-alert latency features in minutes (null-safe).

    Adds: ack_latency, triage_duration, investigation_duration, total_dwell,
    close_latency_after_ack, _quarantined_future flag. Missing timestamps yield
    nulls; out-of-order pairs warn and null; future-dated rows are flagged and
    excluded from aggregates via the flag column.
    """
    frame = alerts.copy()
    limits = _phase2_thresholds(config_dir)
    tolerance = float(limits.get("timestamp_future_tolerance_seconds", 60))
    now = pd.Timestamp.now(tz="UTC")
    future_mask = pd.Series(False, index=frame.index)
    for col in ("detected_ts", "ack_ts", "close_ts"):
        if col in frame.columns:
            future_mask = future_mask | (to_utc(frame[col]) > now + pd.Timedelta(seconds=tolerance))
    frame["_quarantined_future"] = future_mask
    frame["ack_latency"] = minutes_between(
        frame.get("detected_ts", pd.Series(pd.NaT, index=frame.index)),
        frame.get("ack_ts", pd.Series(pd.NaT, index=frame.index)),
    )
    if "triage_start_ts" in frame.columns and "triage_end_ts" in frame.columns:
        frame["triage_duration"] = minutes_between(
            frame["triage_start_ts"], frame["triage_end_ts"]
        )
    else:
        frame["triage_duration"] = float("nan")
    frame["total_dwell"] = minutes_between(
        frame.get("detected_ts", pd.Series(pd.NaT, index=frame.index)),
        frame.get("close_ts", pd.Series(pd.NaT, index=frame.index)),
    )
    frame["close_latency_after_ack"] = minutes_between(
        frame.get("ack_ts", pd.Series(pd.NaT, index=frame.index)),
        frame.get("close_ts", pd.Series(pd.NaT, index=frame.index)),
    )
    frame["investigation_duration"] = frame["triage_duration"]
    for col in (
        "ack_latency",
        "triage_duration",
        "investigation_duration",
        "total_dwell",
        "close_latency_after_ack",
    ):
        negative = frame[col] < 0
        if bool(negative.any()):
            warnings.warn(
                f"{int(negative.sum())} out-of-order pairs in {col}; nulled",
                UserWarning,
                stacklevel=2,
            )
            frame.loc[negative, col] = float("nan")
    frame.loc[frame["_quarantined_future"], ["ack_latency", "total_dwell"]] = float("nan")
    return frame


def case_duration_features(cases: pd.DataFrame) -> pd.DataFrame:
    """Compute per-case case_duration and reopen_gap features."""
    frame = cases.copy()
    open_ts = frame.get("open_ts", pd.Series(pd.NaT, index=frame.index))
    close_ts = frame.get("close_ts", pd.Series(pd.NaT, index=frame.index))
    frame["case_duration"] = minutes_between(open_ts, close_ts)
    negative = frame["case_duration"] < 0
    if bool(negative.any()):
        warnings.warn(
            f"{int(negative.sum())} out-of-order case durations; nulled",
            UserWarning,
            stacklevel=2,
        )
        frame.loc[negative, "case_duration"] = float("nan")
    if "reopen_count" in frame.columns:
        frame["reopen_gap"] = frame["reopen_count"].apply(
            lambda n: float(n) * float(frame["case_duration"].median(skipna=True) or 0.0)
            if pd.notna(n) and int(n) > 0
            else float("nan")
        )
    else:
        frame["reopen_gap"] = float("nan")
    return frame


def detect_batch_close(
    cases: pd.DataFrame, config_dir: str | Path = "configs"
) -> pd.DataFrame:
    """Detect batch-close bursts with a sliding window over analyst closures.

    Flags bursts where N >= K closures share near-identical timestamps AND
    identical disposition codes. Returns bursts with burst_id, burst_size,
    burst_duration, analyst_id, window_start.
    """
    limits = _phase2_thresholds(config_dir)
    window_s = float(limits.get("bulk_close_window_seconds", 60))
    min_count = int(limits.get("bulk_close_min_count", 50))
    if cases.empty or "close_ts" not in cases.columns:
        return pd.DataFrame(
            columns=["burst_id", "burst_size", "burst_duration", "analyst_id", "window_start"]
        )
    closed = cases[cases["close_ts"].notna()].copy()
    if closed.empty:
        return pd.DataFrame(
            columns=["burst_id", "burst_size", "burst_duration", "analyst_id", "window_start"]
        )
    # Robust to minimal/property-test frames: missing grouping columns mean
    # bursts cannot be attributed, so treat as a single UNKNOWN group.
    if "analyst_id" not in closed.columns:
        closed["analyst_id"] = "UNKNOWN"
    if "disposition_code" not in closed.columns:
        closed["disposition_code"] = "UNKNOWN"
    closed["close_ts"] = to_utc(closed["close_ts"])
    closed = closed.sort_values("close_ts")
    bursts: list[dict[str, Any]] = []
    for (analyst, disp), group in closed.groupby(
        ["analyst_id", "disposition_code"], dropna=False
    ):
        times = group["close_ts"].tolist()
        start_idx = 0
        for end_idx in range(len(times)):
            while (times[end_idx] - times[start_idx]).total_seconds() > window_s:
                start_idx += 1
            size = end_idx - start_idx + 1
            if size >= min_count:
                window_times = times[start_idx : end_idx + 1]
                duration = (window_times[-1] - window_times[0]).total_seconds()
                seed = f"{analyst}|{disp}|{window_times[0].isoformat()}|{size}"
                bursts.append(
                    {
                        "burst_id": hashlib.sha256(seed.encode()).hexdigest()[:16],
                        "burst_size": int(size),
                        "burst_duration": float(duration),
                        "analyst_id": analyst,
                        "window_start": window_times[0],
                    }
                )
                start_idx = end_idx + 1
    return pd.DataFrame(
        bursts,
        columns=["burst_id", "burst_size", "burst_duration", "analyst_id", "window_start"],
    )


def time_distributions(
    events: pd.DataFrame, ts_col: str = "close_ts", group_col: str = "analyst_id"
) -> dict[str, Any]:
    """Compute time-of-day and day-of-week distributions per group and entity."""
    if events.empty or ts_col not in events.columns:
        return {"by_group": {}, "entity": {"hod": [0.0] * 24, "dow": [0.0] * 7}}
    frame = events.copy()
    frame["_ts"] = to_utc(frame[ts_col])
    frame = frame[frame["_ts"].notna()]
    entity_hod = [0.0] * 24
    entity_dow = [0.0] * 7
    by_group: dict[str, Any] = {}
    if len(frame):
        for hour in frame["_ts"].dt.hour.tolist():
            entity_hod[int(hour)] += 1.0
        for dow in frame["_ts"].dt.dayofweek.tolist():
            entity_dow[int(dow)] += 1.0
        total = float(sum(entity_hod)) or 1.0
        entity_hod = [v / total for v in entity_hod]
        total_d = float(sum(entity_dow)) or 1.0
        entity_dow = [v / total_d for v in entity_dow]
        if group_col in frame.columns:
            for grp, sub in frame.groupby(group_col, dropna=False):
                hod = [0.0] * 24
                for hour in sub["_ts"].dt.hour.tolist():
                    hod[int(hour)] += 1.0
                tot = float(sum(hod)) or 1.0
                by_group[str(grp)] = {"hod": [v / tot for v in hod], "n": int(len(sub))}
    return {"by_group": by_group, "entity": {"hod": entity_hod, "dow": entity_dow}}


def summarise_latencies(featured: pd.DataFrame) -> dict[str, float]:
    """Summarise latency columns into mean/median/p90 triples."""
    summary: dict[str, float] = {}
    for col in (
        "ack_latency",
        "triage_duration",
        "investigation_duration",
        "total_dwell",
        "close_latency_after_ack",
        "case_duration",
    ):
        if col in featured.columns:
            summary[f"{col}_mean"] = safe_mean(featured[col])
            summary[f"{col}_median"] = safe_median(featured[col])
            summary[f"{col}_p90"] = safe_p90(featured[col])
    return summary
