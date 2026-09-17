"""Asset features: DuckDB join of alerts/cases to inventory criticality."""

from __future__ import annotations

import warnings
from typing import Any

import duckdb
import pandas as pd


def _register_pair(
    connection: duckdb.DuckDBPyConnection, alerts: pd.DataFrame, assets: pd.DataFrame
) -> None:
    """Register alerts/assets frames as DuckDB views with normalised columns."""
    if alerts.empty:
        alert_view = pd.DataFrame({"asset_id": [], "alert_id": []})
    else:
        alert_view = alerts.copy()
    if assets.empty:
        asset_view = pd.DataFrame({"asset_id": []})
    else:
        asset_view = assets.copy()
    if "asset_id" not in alert_view.columns:
        alert_view["asset_id"] = pd.Series(dtype=str)
    if "asset_id" not in asset_view.columns:
        asset_view["asset_id"] = pd.Series(dtype=str)
    connection.register("alerts_v", alert_view)
    connection.register("assets_v", asset_view)


def resolve_shadow_assets(alerts: pd.DataFrame, assets: pd.DataFrame) -> pd.DataFrame:
    """Append shadow records (criticality=UNKNOWN + WARNING) for unknown assets."""
    known: set[str] = set()
    if not assets.empty and "asset_id" in assets.columns:
        known = set(assets["asset_id"].dropna().astype(str).tolist())
    referenced: set[str] = set()
    if not alerts.empty and "asset_id" in alerts.columns:
        referenced = set(alerts["asset_id"].dropna().astype(str).tolist())
    missing = sorted(referenced - known)
    if missing:
        warnings.warn(
            f"{len(missing)} alert assets missing from inventory; shadow UNKNOWN created",
            UserWarning,
            stacklevel=2,
        )
        shadows = pd.DataFrame(
            [
                {
                    "asset_id": asset_id,
                    "hostname": "",
                    "criticality": "UNKNOWN",
                    "environment": "unknown",
                    "os_family": "unknown",
                    "internet_facing": False,
                    "gap_flag": False,
                }
                for asset_id in missing
            ]
        )
        return pd.concat([assets, shadows], ignore_index=True)
    return assets.copy()


def asset_features(
    alerts: pd.DataFrame, cases: pd.DataFrame, assets: pd.DataFrame, window_days: float = 30.0
) -> dict[str, Any]:
    """Compute alert density, critical coverage and internet-facing rates via DuckDB."""
    resolved = resolve_shadow_assets(alerts, assets)
    connection = duckdb.connect()
    try:
        _register_pair(connection, alerts, resolved)
        density = connection.execute(
            """
            SELECT a.asset_id AS asset_id, COUNT(l.alert_id) AS n
            FROM assets_v a LEFT JOIN alerts_v l USING (asset_id)
            GROUP BY a.asset_id
            """
        ).fetchdf()
    finally:
        connection.close()
    span = max(1.0, float(window_days))
    per_asset = (density["n"] / span).tolist() if not density.empty else []
    alert_density_mean = float(sum(per_asset) / max(1, len(per_asset)))
    critical_mask = pd.Series([], dtype=bool)
    if not resolved.empty and "criticality" in resolved.columns:
        critical_mask = resolved["criticality"].astype(str).str.upper().isin(["HIGH", "CRITICAL"])
    critical_ids: set[str] = set()
    if not resolved.empty:
        critical_ids = set(resolved[critical_mask]["asset_id"].astype(str).tolist())
    alerted_ids: set[str] = set()
    if not alerts.empty and "asset_id" in alerts.columns:
        alerted_ids = set(alerts["asset_id"].dropna().astype(str).tolist())
    critical_asset_coverage_rate = float(
        len(critical_ids & alerted_ids) / max(1, len(critical_ids))
    )
    facing_ids: set[str] = set()
    if not resolved.empty and "internet_facing" in resolved.columns:
        mask = resolved["internet_facing"].astype(str).str.lower().isin(["true", "1"])
        facing_ids = set(resolved[mask]["asset_id"].astype(str).tolist())
    internet_facing_alert_rate = float(len(facing_ids & alerted_ids) / max(1, len(facing_ids)))
    cased_ids = (
        set(cases["asset_id"].dropna().astype(str).tolist())
        if not cases.empty and "asset_id" in cases.columns
        else set()
    )
    case_asset_coverage_rate = float(len(cased_ids) / max(1, len(resolved)))
    shadow_count = 0
    if not resolved.empty and "criticality" in resolved.columns:
        shadow_count = int((resolved["criticality"] == "UNKNOWN").sum())
    return {
        "alert_density_mean": float(alert_density_mean),
        "critical_asset_coverage_rate": float(critical_asset_coverage_rate),
        "internet_facing_alert_rate": float(internet_facing_alert_rate),
        "case_asset_coverage_rate": float(case_asset_coverage_rate),
        "shadow_asset_count": int(shadow_count),
        "asset_count_resolved": int(len(resolved)),
    }
