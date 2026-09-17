"""Entity feature vector assembly (120-200 features, polars output, BH-FDR)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl

from satsa.features import asset as asset_mod
from satsa.features import coverage as coverage_mod
from satsa.features import text as text_mod
from satsa.features import workflow as workflow_mod
from satsa.features._common import to_utc
from satsa.features.temporal import (
    alert_latency_features,
    case_duration_features,
    summarise_latencies,
    time_distributions,
)

SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO", "UNKNOWN"]
CATEGORIES = ["MALWARE", "PHISHING", "INTRUSION", "OTHER"]
PEER_Z_METRICS = [
    "alert_count",
    "bypass_rate",
    "reopen_rate",
    "sla_breach_rate",
    "premature_rate",
    "template_similarity",
    "placeholder_ratio",
    "telemetry_gap_ratio",
    "escalation_rate",
    "case_duration_median",
    "ack_latency_median",
    "orphan_case_rate",
]

FEATURE_DOC: dict[str, tuple[str, str, str]] = {}


def _doc(name: str, definition: str, unit: str, direction: str) -> str:
    """Register feature documentation and return the feature name."""
    FEATURE_DOC[name] = (definition, unit, direction)
    return name


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    """Apply Benjamini-Hochberg FDR control; returns adjusted p-values in order."""
    n = len(p_values)
    if n == 0:
        return []
    order = sorted(range(n), key=lambda i: p_values[i])
    adjusted = [0.0] * n
    prev = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        raw = p_values[idx] * n / (n - rank + 1)
        prev = min(prev, min(1.0, raw))
        adjusted[idx] = prev
    return [float(max(0.0, min(1.0, v))) for v in adjusted]


def _normal_pvalue(z: float) -> float:
    """Return a two-sided normal p-value for a z-score."""
    return float(math.erfc(abs(z) / math.sqrt(2.0)))


def _robust_z(value: float, peers: list[float]) -> float:
    """Return the modified z-score (0.6745*(x-median)/MAD) with fallbacks."""
    if not peers:
        return 0.0
    series = pd.Series(peers, dtype=float)
    median = float(series.median())
    mad = float((series - median).abs().median())
    if mad > 0:
        return float(0.6745 * (value - median) / mad)
    iqr = float(series.quantile(0.75) - series.quantile(0.25))
    if iqr > 0:
        return float(0.7413 * (value - median) / iqr)
    span = float(series.max() - series.min())
    if span > 0:
        return float((value - median) / span)
    return 0.0


def _sla_breach_rate(cases: pd.DataFrame, sla_hours: float = 72.0) -> float:
    """Return the fraction of closed cases breaching the SLA window."""
    if cases.empty or "open_ts" not in cases.columns:
        return 0.0
    closed = cases[cases["close_ts"].notna()] if "close_ts" in cases.columns else cases.iloc[0:0]
    if closed.empty:
        return 0.0
    hours = (
        to_utc(closed["close_ts"]) - to_utc(closed["open_ts"])
    ).dt.total_seconds() / 3600.0
    return float((hours > sla_hours).mean())


def _premature_rate(cases: pd.DataFrame, premature_minutes: float = 5.0) -> float:
    """Return the fraction of CRITICAL cases closed within premature minutes."""
    if cases.empty:
        return 0.0
    crit = cases.iloc[0:0]
    if "severity_norm" in cases.columns:
        crit = cases[cases["severity_norm"] == "CRITICAL"]
    closed = crit.iloc[0:0]
    if "close_ts" in crit.columns:
        closed = crit[crit["close_ts"].notna()]
    if closed.empty:
        return 0.0
    minutes = (
        to_utc(closed["close_ts"]) - to_utc(closed["open_ts"])
    ).dt.total_seconds() / 60.0
    return float(((minutes >= 0) & (minutes < premature_minutes)).mean())


def _night_weekend_fractions(cases: pd.DataFrame) -> dict[str, float]:
    """Return night-closure and weekend-event fractions for trend features."""
    if cases.empty or "close_ts" not in cases.columns:
        return {"night_fraction": 0.0, "weekend_fraction": 0.0}
    closed = to_utc(cases["close_ts"]).dropna()
    night = 0.0
    if len(closed):
        hours = closed.dt.hour
        night = float((((hours >= 22) | (hours < 6))).mean())
    weekend = 0.0
    if "detected_ts" in cases.columns:
        detected = to_utc(cases["detected_ts"]).dropna()
        if len(detected):
            weekend = float((detected.dt.dayofweek >= 5).mean())
    return {"night_fraction": float(night), "weekend_fraction": float(weekend)}


def build_entity_features(
    entity_id: str,
    alerts: pd.DataFrame,
    cases: pd.DataFrame,
    investigations: pd.DataFrame,
    escalations: pd.DataFrame,
    assets: pd.DataFrame,
    telemetry: pd.DataFrame,
    enrollment_days: float | None = None,
    backend: str = "lite",
    cohort_peers: dict[str, list[float]] | None = None,
    config_dir: str | Path = "configs",
) -> dict[str, float]:
    """Assemble the entity feature vector as a flat dict.

    Missing-data policy: unwitnessed metrics default to 0.0 (rates) with
    sample-size-aware signals downstream; survivorship normalises volume by
    enrollment days rather than raw totals.
    """
    days = float(enrollment_days) if enrollment_days and enrollment_days > 0 else 30.0
    feats: dict[str, float] = {}
    feats["alert_count"] = float(len(alerts) / days)
    feats["case_count"] = float(len(cases) / days)
    feats["investigation_count"] = float(len(investigations) / days)
    feats["escalation_count"] = float(len(escalations) / days)
    feats["asset_count"] = float(len(assets))
    feats["telemetry_count"] = float(len(telemetry) / days)
    feats["alerts_per_day"] = float(len(alerts) / days)
    feats["cases_per_day"] = float(len(cases) / days)
    feats["alerts_per_case"] = float(len(alerts) / max(1, len(cases)))
    feats["escalations_per_case"] = float(len(escalations) / max(1, len(cases)))
    lat_alerts = alert_latency_features(alerts, config_dir)
    lat_cases = case_duration_features(cases)
    for key, val in summarise_latencies(lat_alerts).items():
        feats[f"lat_{key}"] = float(val)
    for key, val in summarise_latencies(lat_cases).items():
        feats[f"lat_{key}"] = float(val)
    for sev in SEVERITIES:
        share = 0.0
        if not alerts.empty and "severity_norm" in alerts.columns:
            share = float((alerts["severity_norm"] == sev).mean())
        feats[f"alert_share_{sev}"] = float(share)
        cshare = 0.0
        if not cases.empty and "severity_norm" in cases.columns:
            cshare = float((cases["severity_norm"] == sev).mean())
        feats[f"case_share_{sev}"] = float(cshare)
    for cat in CATEGORIES:
        share = 0.0
        if not alerts.empty and "category" in alerts.columns:
            share = float((alerts["category"] == cat).mean())
        feats[f"cat_share_{cat}"] = float(share)
    summary = workflow_mod.workflow_summary(cases, escalations, alerts, config_dir)
    by_sev = summary["escalation_rate_by_severity"]
    feats["escalation_rate"] = float(sum(by_sev.values()) / max(1, len(by_sev)))
    feats["bypass_rate"] = float(summary["bypass_rate"])
    feats["reopen_rate"] = float(summary["reopen_rate"])
    feats["duplicate_chain_depth"] = float(summary["duplicate_chain_depth"])
    feats["orphan_case_rate"] = float(summary["orphan_case_rate"])
    feats["orphan_alert_rate"] = float(summary["orphan_alert_rate"])
    feats["backfill_rate"] = float(summary["backfill_rate"])
    feats["tier_dwell_T1"] = float(summary["tier_dwell_time"].get("T1", 0.0))
    feats["tier_dwell_T2"] = float(summary["tier_dwell_time"].get("T2", 0.0))
    feats["tier_dwell_T3"] = float(summary["tier_dwell_time"].get("T3", 0.0))
    cov = coverage_mod.coverage_summary(entity_id, assets, telemetry, alerts, config_dir)
    feats["telemetry_gap_ratio"] = float(cov["telemetry_gap_ratio"])
    feats["silence_max"] = float(cov["silence_streak_days_max"])
    feats["category_coverage"] = float(cov["category_coverage_score"])
    feats["mitre_coverage"] = float(cov["mitre_coverage_score"])
    feats["expected_absent_count"] = float(cov["expected_absent_count"])
    ast = asset_mod.asset_features(alerts, cases, assets)
    feats["alert_density_mean"] = float(ast["alert_density_mean"])
    feats["critical_asset_coverage"] = float(ast["critical_asset_coverage_rate"])
    feats["internet_facing_alert_rate"] = float(ast["internet_facing_alert_rate"])
    feats["case_asset_coverage"] = float(ast["case_asset_coverage_rate"])
    feats["shadow_asset_count"] = float(ast["shadow_asset_count"])
    text = text_mod.text_features(investigations, backend=backend)
    feats["template_similarity"] = float(text["template_similarity_score"])
    feats["vocabulary_richness"] = float(text["vocabulary_richness"])
    feats["copy_paste_ratio"] = float(text["copy_paste_ratio"])
    feats["placeholder_ratio"] = float(text["placeholder_ratio"])
    tod = _night_weekend_fractions(cases)
    empty_frame = pd.DataFrame()
    _ = time_distributions(cases if not cases.empty else empty_frame, "close_ts", "analyst_id")
    feats["night_fraction"] = float(tod["night_fraction"])
    feats["weekend_fraction"] = float(tod["weekend_fraction"])
    feats["sla_breach_rate"] = float(_sla_breach_rate(cases))
    feats["premature_rate"] = float(_premature_rate(cases))
    feats["ack_latency_median"] = float(feats.get("lat_ack_latency_median", 0.0))
    feats["case_duration_median"] = float(feats.get("lat_case_duration_median", 0.0))
    peers = cohort_peers or {}
    raw_p: list[float] = []
    for metric in PEER_Z_METRICS:
        peer_vals = [float(v) for v in peers.get(metric, [])]
        z = _robust_z(float(feats.get(metric, 0.0)), peer_vals)
        feats[f"peer_z_{metric}"] = float(z)
        raw_p.append(_normal_pvalue(z))
    adjusted = benjamini_hochberg(raw_p)
    for metric, p_raw, p_adj in zip(PEER_Z_METRICS, raw_p, adjusted):
        feats[f"p_{metric}"] = float(p_raw)
        feats[f"padj_{metric}"] = float(p_adj)
    for metric in PEER_Z_METRICS:
        feats[f"trend_{metric}"] = 0.0
    return {k: float(v) if v == v else 0.0 for k, v in feats.items()}


def _empty_frames() -> tuple[pd.DataFrame, ...]:
    """Return empty canonical frames for schema construction."""

    def _cols(names: list[str]) -> pd.DataFrame:
        """Build an empty frame with the given columns."""
        return pd.DataFrame({name: pd.Series(dtype="object") for name in names})

    alert_cols = ["severity_norm", "category", "asset_id", "detected_ts"]
    alert_cols += ["ack_ts", "close_ts", "alert_id"]
    case_cols = ["severity_norm", "case_id", "asset_id", "open_ts", "close_ts"]
    case_cols += ["reopen_count", "tier", "status", "alert_ids", "detected_ts"]
    asset_cols = ["asset_id", "criticality", "environment", "os_family"]
    asset_cols += ["internet_facing"]
    return (
        _cols(alert_cols),
        _cols(case_cols),
        _cols(["notes", "analyst_id"]),
        _cols(["case_id", "from_tier"]),
        _cols(asset_cols),
        _cols(["asset_id", "source"]),
    )


FEATURE_SCHEMA: list[str] = sorted(
    build_entity_features("schema_probe", *_empty_frames()).keys()
)


def features_to_polars(rows: dict[str, dict[str, float]]) -> pl.DataFrame:
    """Convert {entity_id: features} to a polars DataFrame with schema columns."""
    records = []
    for entity, vals in rows.items():
        record: dict[str, Any] = {"entity_id": entity}
        record.update({c: float(vals.get(c, 0.0)) for c in FEATURE_SCHEMA})
        records.append(record)
    schema: dict[str, Any] = {"entity_id": pl.String}
    schema.update({c: pl.Float64 for c in FEATURE_SCHEMA})
    return pl.DataFrame(records, schema=schema)


def document_schema() -> dict[str, tuple[str, str, str]]:
    """Return feature documentation (definition, unit, risk direction)."""
    for name in FEATURE_SCHEMA:
        if name not in FEATURE_DOC:
            if name.startswith("peer_z_"):
                _doc(name, "Robust z-score vs peer cohort", "z", "high=anomalous")
            elif name.startswith("padj_") or name.startswith("p_"):
                _doc(name, "BH-FDR adjusted/raw peer p-value", "p", "low=anomalous")
            elif name.startswith("trend_"):
                _doc(name, "Window delta feature", "delta", "varies")
            elif name.startswith(("alert_share_", "case_share_", "cat_share_")):
                _doc(name, "Severity/category share of volume", "fraction", "varies")
            else:
                _doc(name, "Entity risk feature", "mixed", "varies")
    return dict(FEATURE_DOC)
