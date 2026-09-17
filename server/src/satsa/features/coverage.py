"""Coverage / negative-space engine: gaps, silence streaks, absent categories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def load_expectations(config_dir: str | Path = "configs") -> dict[str, Any]:
    """Load the expectation model mapping asset profile to expected sources."""
    path = Path(config_dir) / "coverage_expectations.yaml"
    if not path.exists():
        return {"expectations": {}, "defaults": {"expected_sources": ["edr"]}}
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def expected_sources_for(asset: dict[str, Any], expectations: dict[str, Any]) -> list[str]:
    """Return expected telemetry sources for one asset profile."""
    key = "|".join(
        [
            str(asset.get("criticality", "")).lower(),
            str(asset.get("environment", "")).lower(),
            str(asset.get("os_family", "")).lower(),
            str(bool(asset.get("internet_facing", False))).lower(),
        ]
    )
    table = expectations.get("expectations", {}) or {}
    if key in table:
        return [str(s) for s in table[key]]
    defaults = expectations.get("defaults", {}) or {}
    return [str(s) for s in defaults.get("expected_sources", ["edr"])]


def negative_space_map(
    entity_id: str,
    assets: pd.DataFrame,
    telemetry: pd.DataFrame,
    config_dir: str | Path = "configs",
    window_days: float = 30.0,
) -> pd.DataFrame:
    """Emit (entity_id, asset_id, expected_source, observed, gap_flag, silence_days).

    Silence semantics: days since last observation within the window; an asset
    with zero telemetry rows is silent for the full window length, an observed
    pair has silence 0. Seasonality note: the 12-week rolling-median
    detrending in detrend_low_activity applies in long-history mode; with
    single-window synthetic telemetry the map is a point-in-time snapshot.
    """
    expectations = load_expectations(config_dir)
    observed: set[tuple[str, str]] = set()
    if not telemetry.empty and "asset_id" in telemetry.columns and "source" in telemetry.columns:
        observed = set(
            zip(
                telemetry["asset_id"].astype(str).tolist(),
                telemetry["source"].astype(str).tolist(),
            )
        )
    rows: list[dict[str, Any]] = []
    for _, asset in assets.iterrows():
        profile = asset.to_dict()
        asset_id = str(profile.get("asset_id", ""))
        for source in expected_sources_for(profile, expectations):
            seen = (asset_id, source) in observed
            rows.append(
                {
                    "entity_id": entity_id,
                    "asset_id": asset_id,
                    "expected_source": source,
                    "observed": bool(seen),
                    "gap_flag": bool(not seen),
                    "silence_days": 0 if seen else int(window_days),
                }
            )
    columns = ["entity_id", "asset_id", "expected_source"]
    columns += ["observed", "gap_flag", "silence_days"]
    return pd.DataFrame(rows, columns=columns)


def detrend_low_activity(
    daily_counts: pd.Series, window_weeks: int = 12
) -> pd.Series:
    """Detrend daily activity with a rolling-median baseline (12-week default).

    Returns residuals (observed - baseline); short histories fall back to the
    expanding median so single-window inputs never crash flagging.
    """
    window = max(7, int(window_weeks * 7))
    series = pd.to_numeric(daily_counts, errors="coerce").fillna(0.0)
    if len(series) < window:
        baseline = series.expanding(min_periods=1).median()
    else:
        baseline = series.rolling(window=window, min_periods=1, center=False).median()
    return series - baseline


def coverage_summary(
    entity_id: str,
    assets: pd.DataFrame,
    telemetry: pd.DataFrame,
    alerts: pd.DataFrame,
    config_dir: str | Path = "configs",
) -> dict[str, Any]:
    """Compute telemetry gaps, silence streaks, category/MITRE coverage."""
    space = negative_space_map(entity_id, assets, telemetry, config_dir)
    critical_ids: set[str] = set()
    if not assets.empty and "asset_id" in assets.columns:
        crit = assets[assets["criticality"].astype(str).str.lower().isin(["high", "critical"])]
        critical_ids = set(crit["asset_id"].astype(str).tolist())
    if critical_ids and not space.empty:
        crit_space = space[space["asset_id"].isin(critical_ids)]
        gap_assets = set(crit_space[crit_space["gap_flag"]]["asset_id"].tolist())
        telemetry_gap_ratio = float(len(gap_assets) / max(1, len(critical_ids)))
    else:
        telemetry_gap_ratio = 0.0
    silence_max = float(space["silence_days"].max()) if not space.empty else 0.0
    categories: set[str] = set()
    if not alerts.empty and "category" in alerts.columns:
        categories = set(alerts["category"].dropna().astype(str).tolist())
    taxonomy = ["MALWARE", "PHISHING", "INTRUSION", "POLICY_VIOLATION"]
    taxonomy += ["VULNERABILITY", "DATA_EXFIL", "OTHER"]
    missing_cats = [c for c in taxonomy if c not in categories]
    category_coverage_score = float(1.0 - len(missing_cats) / max(1, len(taxonomy)))
    mitre_seen = {c for c in categories if c in ("MALWARE", "INTRUSION", "DATA_EXFIL")}
    mitre_coverage_score = float(len(mitre_seen) / 3.0)
    expected_absent = (
        space[space["gap_flag"]][["entity_id", "asset_id", "expected_source"]]
        .astype(str)
        .to_dict(orient="records")
        if not space.empty
        else []
    )
    return {
        "telemetry_gap_ratio": float(telemetry_gap_ratio),
        "silence_streak_days_max": float(silence_max),
        "category_coverage_score": float(category_coverage_score),
        "category_missing": missing_cats,
        "mitre_coverage_score": float(mitre_coverage_score),
        "expected_but_absent": expected_absent,
        "expected_absent_count": int(len(expected_absent)),
        "negative_space_rows": int(len(space)),
    }
