"""Shared helpers for feature engineering (UTC-safe, null-safe)."""

from __future__ import annotations

import warnings
from datetime import UTC, datetime
from typing import Any

import pandas as pd


def to_utc(series: pd.Series) -> pd.Series:
    """Parse a column to UTC datetimes, coercing unparseable values to NaT."""
    parsed = pd.to_datetime(series, utc=True, errors="coerce")
    return parsed


def minutes_between(start: pd.Series, end: pd.Series) -> pd.Series:
    """Return (end - start) in minutes as float, NaN where either is missing."""
    first = to_utc(start)
    second = to_utc(end)
    return (second - first).dt.total_seconds() / 60.0


def safe_mean(values: pd.Series) -> float:
    """Return the mean of finite values, or 0.0 when none exist."""
    clean = pd.to_numeric(values, errors="coerce").replace(
        [float("inf"), float("-inf")], float("nan")
    )
    clean = clean[clean.notna()]
    if len(clean) == 0:
        return 0.0
    return float(clean.mean())


def safe_median(values: pd.Series) -> float:
    """Return the median of finite values, or 0.0 when none exist."""
    clean = pd.to_numeric(values, errors="coerce").replace(
        [float("inf"), float("-inf")], float("nan")
    )
    clean = clean[clean.notna()]
    if len(clean) == 0:
        return 0.0
    return float(clean.median())


def safe_p90(values: pd.Series) -> float:
    """Return the 90th percentile of finite values, or 0.0 when none exist."""
    clean = pd.to_numeric(values, errors="coerce").replace(
        [float("inf"), float("-inf")], float("nan")
    )
    clean = clean[clean.notna()]
    if len(clean) == 0:
        return 0.0
    return float(clean.quantile(0.9))


def warn_out_of_order(context: str, count: int) -> None:
    """Emit a WARNING for out-of-order timestamps without crashing."""
    if count > 0:
        warnings.warn(
            f"{count} out-of-order timestamp pairs in {context}; affected spans nulled",
            UserWarning,
            stacklevel=3,
        )


def now_utc() -> datetime:
    """Return the current UTC time as an aware datetime."""
    return datetime.now(UTC)


def closed_only(frame: pd.DataFrame, ts_col: str = "close_ts") -> pd.DataFrame:
    """Return rows with a non-null timestamp column (empty-safe)."""
    if not isinstance(frame, pd.DataFrame) or frame.empty or ts_col not in frame.columns:
        return pd.DataFrame()
    return frame[frame[ts_col].notna()].copy()


def column_ids(frame: pd.DataFrame, col: str) -> list[str]:
    """Return string ids from a column (empty-safe)."""
    if not isinstance(frame, pd.DataFrame) or frame.empty or col not in frame.columns:
        return []
    return [str(v) for v in frame[col].tolist()]


def as_dict(record: Any) -> dict[str, Any]:
    """Coerce a mapping-like row to a plain dict of JSON-safe scalars."""
    if isinstance(record, dict):
        return {str(k): _scalar(v) for k, v in record.items()}
    return {}


def _scalar(value: Any) -> Any:
    """Coerce a value to a JSON-safe scalar for evidence rows."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    return str(value)
