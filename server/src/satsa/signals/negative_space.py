"""Negative-space signals NS-001..NS-012 (concrete Signal subclasses)."""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar

import pandas as pd
import yaml

from satsa.features import coverage as coverage_mod
from satsa.features._common import closed_only, column_ids, to_utc
from satsa.features.coverage import detrend_low_activity
from satsa.signals._evidence import frame_rows, matching_rows
from satsa.signals.base import EvidenceBundle, Family, Signal, SignalContext, SignalResult
from satsa.signals.execution_gaps import _alerts, _cases, _EvidenceMixin


def _assets(ctx: SignalContext) -> pd.DataFrame:
    """Return assets as a DataFrame (empty when absent)."""
    if isinstance(ctx.assets, pd.DataFrame):
        return ctx.assets
    return pd.DataFrame()


def _telemetry(ctx: SignalContext) -> pd.DataFrame:
    """Return telemetry as a DataFrame (empty when absent)."""
    if isinstance(ctx.telemetry, pd.DataFrame):
        return ctx.telemetry
    return pd.DataFrame()


def _registry_explanation(entity_id: str, config_dir: str | Path = "configs") -> str:
    """Return a manual feed explanation from entity_registry.yaml, if any."""
    path = Path(config_dir) / "entity_registry.yaml"
    if not path.exists():
        return ""
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        entities = data.get("entities", {}) or {}
        entry = entities.get(entity_id, {}) or {}
        return str(entry.get("feed_explanation", "") or "")
    except Exception:
        return ""


def _facing_assets(assets: pd.DataFrame) -> pd.DataFrame:
    """Return internet-facing assets (empty-safe)."""
    if assets.empty or "internet_facing" not in assets.columns:
        return assets.iloc[0:0]
    mask = assets["internet_facing"].astype(str).str.lower().isin(["true", "1"])
    return assets[mask].copy()


def _observed_pairs(telemetry: pd.DataFrame) -> set[tuple[str, str]]:
    """Return observed (asset_id, source) pairs (empty-safe)."""
    if telemetry.empty:
        return set()
    if "asset_id" not in telemetry.columns or "source" not in telemetry.columns:
        return set()
    return set(zip(telemetry["asset_id"].astype(str), telemetry["source"].astype(str)))


def _lacks_perimeter(asset_id: str, observed: set[tuple[str, str]]) -> bool:
    """Check whether an asset lacks both firewall and IDS sources."""
    present = {source for (aid, source) in observed if aid == asset_id}
    return not ({"firewall", "ids"} & present)


class NS001CoverageGap(_EvidenceMixin, Signal):
    """NS-001 Critical-asset telemetry coverage gap."""

    id = "NS-001"
    name = "Critical coverage gap"
    family: ClassVar[Family] = "negative_space"
    required_features = ["telemetry_gap_ratio", "asset_count"]
    default_severity = "HIGH"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when critical assets lack expected telemetry."""
        assets = _assets(ctx)
        telemetry = _telemetry(ctx)
        threshold = float(ctx.config.get("telemetry_gap_ratio_threshold", 0.10))
        alerts = _alerts(ctx)
        summary = coverage_mod.coverage_summary(ctx.entity_id, assets, telemetry, alerts)
        value = float(summary["telemetry_gap_ratio"])
        sample = int(len(assets))
        if sample < self.min_n(ctx):
            return self._store(self.insufficient(ctx, sample, threshold), [], [])
        absent = summary["expected_but_absent"]
        refs = sorted({str(r.get("asset_id", "")) for r in absent})[:5]
        result = self.build_result(
            ctx, value, threshold, sample, row_refs=refs, severity="HIGH"
        )
        supporting = matching_rows(assets, "asset_id", refs)
        counter = frame_rows(assets, "asset_id", [])
        return self._store(result, supporting, counter)

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-001."""
        return self._bundle(result, self.id)


class NS002SilenceStreak(_EvidenceMixin, Signal):
    """NS-002 Assets with long telemetry silence streaks."""

    id = "NS-002"
    name = "Telemetry silence streak"
    family: ClassVar[Family] = "negative_space"
    required_features = ["silence_max", "asset_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when the max silence streak exceeds the day threshold."""
        assets = _assets(ctx)
        telemetry = _telemetry(ctx)
        threshold = float(ctx.config.get("silence_streak_days_threshold", 7))
        try:
            window_days = float(
                (pd.to_datetime(ctx.window_end) - pd.to_datetime(ctx.window_start)).days
            )
        except Exception:
            window_days = 30.0
        window_days = window_days if window_days > 0 else 30.0
        space = coverage_mod.negative_space_map(
            ctx.entity_id, assets, telemetry, window_days=window_days
        )
        if space.empty or len(space) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(space), threshold), [], [])
        value = float(space["silence_days"].max())
        streaked = space[space["silence_days"] >= threshold]
        refs = sorted(streaked["asset_id"].astype(str).tolist())[:5]
        result = self.build_result(ctx, value, threshold, len(space), row_refs=refs)
        return self._store(
            result,
            matching_rows(assets, "asset_id", refs),
            frame_rows(assets, "asset_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-002."""
        return self._bundle(result, self.id)


class NS003CategoryAbsence(_EvidenceMixin, Signal):
    """NS-003 Alert-category absence vs peer cohort."""

    id = "NS-003"
    name = "Category absence vs peers"
    family: ClassVar[Family] = "negative_space"
    required_features = ["category_coverage", "alert_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when missing-category count exceeds peers by z-threshold."""
        alerts = _alerts(ctx)
        threshold = float(ctx.config.get("category_absence_z_threshold", 2.0))
        assets = _assets(ctx)
        telemetry = _telemetry(ctx)
        summary = coverage_mod.coverage_summary(ctx.entity_id, assets, telemetry, alerts)
        missing = len(summary["category_missing"])
        peers = [float(v) for v in (ctx.cohort_features or {}).get("category_missing_count", [])]
        if not alerts.empty and len(alerts) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(alerts), threshold), [], [])
        if not peers:
            return self._store(self.insufficient(ctx, len(alerts), threshold), [], [])
        from satsa.signals.peer_benchmark import modified_z

        stats = modified_z(float(missing), peers)
        median = float(stats["median"])
        value = float(stats["modified_z"])
        result = self.build_result(
            ctx, value, threshold, len(alerts), metadata={"missing": summary["category_missing"]}
        )
        return self._store(
            result,
            frame_rows(alerts, "alert_id", []),
            frame_rows(alerts, "alert_id", []),
            {"peer_median_missing": median},
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-003."""
        return self._bundle(result, self.id)


class NS004MitreAbsence(_EvidenceMixin, Signal):
    """NS-004 MITRE-tactic absence relative to asset profile."""

    id = "NS-004"
    name = "MITRE coverage absence"
    family: ClassVar[Family] = "negative_space"
    required_features = ["mitre_coverage", "alert_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when MITRE coverage falls at or below the low-coverage bound."""
        alerts = _alerts(ctx)
        threshold = 0.34
        assets = _assets(ctx)
        telemetry = _telemetry(ctx)
        summary = coverage_mod.coverage_summary(ctx.entity_id, assets, telemetry, alerts)
        value = 1.0 - float(summary["mitre_coverage_score"])
        if not alerts.empty and len(alerts) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(alerts), threshold), [], [])
        result = self.build_result(ctx, value, threshold, len(alerts))
        return self._store(
            result, frame_rows(alerts, "alert_id", []), frame_rows(alerts, "alert_id", [])
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-004."""
        return self._bundle(result, self.id)


class NS005ExpectedSourceAbsent(_EvidenceMixin, Signal):
    """NS-005 Expected core sources absent (EDR-class)."""

    id = "NS-005"
    name = "Expected core source absent"
    family: ClassVar[Family] = "negative_space"
    required_features = ["expected_absent_count", "asset_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when any expected asset-source pair has zero evidence."""
        assets = _assets(ctx)
        threshold = float(ctx.config.get("coverage_gap_min_unmonitored_assets", 1))
        telemetry = _telemetry(ctx)
        alerts = _alerts(ctx)
        summary = coverage_mod.coverage_summary(ctx.entity_id, assets, telemetry, alerts)
        value = float(summary["expected_absent_count"])
        if len(assets) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(assets), threshold), [], [])
        absent = summary["expected_but_absent"]
        refs = sorted({str(r.get("asset_id", "")) for r in absent})[:5]
        result = self.build_result(ctx, value, threshold, len(assets), row_refs=refs)
        return self._store(
            result,
            matching_rows(assets, "asset_id", refs),
            frame_rows(assets, "asset_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-005."""
        return self._bundle(result, self.id)


class NS006PerimeterBlind(_EvidenceMixin, Signal):
    """NS-006 Internet-facing assets missing perimeter telemetry."""

    id = "NS-006"
    name = "Perimeter blind spot"
    family: ClassVar[Family] = "negative_space"
    required_features = ["internet_facing_alert_rate", "asset_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag internet-facing assets lacking firewall/IDS sources."""
        assets = _assets(ctx)
        telemetry = _telemetry(ctx)
        threshold = float(ctx.config.get("coverage_gap_min_unmonitored_assets", 1))
        if assets.empty:
            return self._store(self.insufficient(ctx, 0, threshold), [], [])
        facing = _facing_assets(assets)
        observed = _observed_pairs(telemetry)
        blind = [a for a in column_ids(facing, "asset_id") if _lacks_perimeter(a, observed)]
        value = float(len(blind))
        if len(facing) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(facing), threshold), [], [])
        result = self.build_result(ctx, value, threshold, len(facing), row_refs=blind[:5])
        return self._store(
            result,
            matching_rows(facing, "asset_id", blind[:5]),
            frame_rows(facing, "asset_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-006."""
        return self._bundle(result, self.id)


class NS007LowActivityDetrended(_EvidenceMixin, Signal):
    """NS-007 Low activity after 12-week seasonal detrending."""

    id = "NS-007"
    name = "Detrended low activity"
    family: ClassVar[Family] = "negative_space"
    required_features = ["alerts_per_day", "alert_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag residual activity below the detrended low bound."""
        alerts = _alerts(ctx)
        threshold = 0.0
        if alerts.empty or "detected_ts" not in alerts.columns:
            return self._store(self.insufficient(ctx, 0, threshold), [], [])
        days = to_utc(alerts["detected_ts"]).dt.floor("D")
        counts = days.value_counts().sort_index()
        if len(counts) < 14:
            return self._store(self.insufficient(ctx, len(alerts), threshold), [], [])
        residual = detrend_low_activity(counts)
        value = float(residual.tail(7).mean())
        spread = float(residual.std()) or 1.0
        flagged_value = float(-value / spread)
        result = self.build_result(
            ctx, flagged_value, 2.0, len(alerts), metadata={"residual_mean_7d": value}
        )
        return self._store(
            result,
            frame_rows(alerts.tail(5), "alert_id", []),
            frame_rows(alerts.head(5), "alert_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-007."""
        return self._bundle(result, self.id)


class NS008InternetBlindspot(_EvidenceMixin, Signal):
    """NS-008 Internet-facing assets with zero alerts."""

    id = "NS-008"
    name = "Internet-facing blind spot"
    family: ClassVar[Family] = "negative_space"
    required_features = ["internet_facing_alert_rate", "asset_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when internet-facing assets draw no alerts."""
        assets = _assets(ctx)
        alerts = _alerts(ctx)
        threshold = 2.0
        if assets.empty:
            return self._store(self.insufficient(ctx, 0, threshold), [], [])
        facing = _facing_assets(assets)
        alerted: set[str] = set()
        if not alerts.empty and "asset_id" in alerts.columns:
            alerted = set(alerts["asset_id"].dropna().astype(str).tolist())
        blind = [a for a in column_ids(facing, "asset_id") if a not in alerted]
        value = float(len(blind))
        if len(facing) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(facing), threshold), [], [])
        result = self.build_result(ctx, value, threshold, len(facing), row_refs=blind[:5])
        return self._store(
            result,
            matching_rows(facing, "asset_id", blind[:5]),
            frame_rows(facing, "asset_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-008."""
        return self._bundle(result, self.id)


class NS009TelemetryGapSpike(_EvidenceMixin, Signal):
    """NS-009 Spike in telemetry gap ratio."""

    id = "NS-009"
    name = "Telemetry gap spike"
    family: ClassVar[Family] = "negative_space"
    required_features = ["telemetry_gap_ratio", "asset_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when the telemetry gap ratio meets or exceeds the threshold."""
        assets = _assets(ctx)
        threshold = float(ctx.config.get("telemetry_gap_ratio_threshold", 0.10))
        telemetry = _telemetry(ctx)
        alerts = _alerts(ctx)
        summary = coverage_mod.coverage_summary(ctx.entity_id, assets, telemetry, alerts)
        value = float(summary["telemetry_gap_ratio"])
        if len(assets) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(assets), threshold), [], [])
        absent = summary["expected_but_absent"]
        refs = sorted({str(r.get("asset_id", "")) for r in absent})[:5]
        result = self.build_result(ctx, value, threshold, len(assets), row_refs=refs)
        return self._store(
            result,
            matching_rows(assets, "asset_id", refs),
            frame_rows(assets, "asset_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-009."""
        return self._bundle(result, self.id)


class NS010SilentCriticalEstate(_EvidenceMixin, Signal):
    """NS-010 Critical assets silent (zero alerts)."""

    id = "NS-010"
    name = "Silent critical estate"
    family: ClassVar[Family] = "negative_space"
    required_features = ["critical_asset_coverage", "asset_count"]
    default_severity = "HIGH"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when the silent-critical fraction meets or exceeds the threshold."""
        assets = _assets(ctx)
        alerts = _alerts(ctx)
        threshold = 0.20
        if assets.empty:
            return self._store(self.insufficient(ctx, 0, threshold), [], [])
        crit = assets.iloc[0:0]
        if "criticality" in assets.columns:
            crit = assets[assets["criticality"].astype(str).str.upper().isin(["HIGH", "CRITICAL"])]
        if len(crit) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(crit), threshold), [], [])
        alerted = set()
        if not alerts.empty and "asset_id" in alerts.columns:
            alerted = set(alerts["asset_id"].dropna().astype(str).tolist())
        silent = [a for a in column_ids(crit, "asset_id") if a not in alerted]
        value = float(len(silent) / max(1, len(crit)))
        result = self.build_result(
            ctx, value, threshold, len(crit), row_refs=silent[:5], severity="HIGH"
        )
        return self._store(
            result,
            matching_rows(crit, "asset_id", silent[:5]),
            frame_rows(crit, "asset_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-010."""
        return self._bundle(result, self.id)


class NS011NoAfterHours(_EvidenceMixin, Signal):
    """NS-011 Absence of out-of-hours activity (observation only, LOW confidence)."""

    id = "NS-011"
    name = "Absence of out-of-hours activity"
    family: ClassVar[Family] = "negative_space"
    required_features = ["night_fraction", "case_count"]
    default_severity = "LOW"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag near-zero out-of-hours share; always LOW confidence, peer-contextualised."""
        cases = _cases(ctx)
        max_allowed = float(ctx.config.get("ns011_max_after_hours_fraction", 0.05))
        closed = closed_only(cases)
        if len(closed) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(closed), max_allowed), [], [])
        hours = to_utc(closed["close_ts"]).dt.hour
        share = float((((hours >= 22) | (hours < 6))).mean())
        value = 1.0 - share
        threshold = 1.0 - max_allowed
        refs = column_ids(closed, "case_id")[:5]
        result = self.build_result(
            ctx, value, threshold, len(closed), severity="LOW", confidence="LOW", row_refs=refs
        )
        peers = (ctx.cohort_features or {}).get("night_fraction", [])
        peer_median = float(pd.Series(peers).median()) if peers else share
        result.metadata["peer_median_night_fraction"] = peer_median
        note = "observation only, never an accusation"
        return self._store(
            result,
            frame_rows(closed.head(5), "case_id", refs),
            frame_rows(closed, "case_id", []),
            {"peer_median_night_fraction": peer_median, "note": note},
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-011."""
        return self._bundle(result, self.id)


class NS012FeedTruncation(_EvidenceMixin, Signal):
    """NS-012 Sudden feed truncation vs trailing baseline."""

    id = "NS-012"
    name = "Feed truncation"
    family: ClassVar[Family] = "negative_space"
    required_features = ["alert_count", "alerts_per_day"]
    default_severity = "HIGH"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag current-window drops beyond threshold_pct with no registry note."""
        alerts = _alerts(ctx)
        drop_pct = float(ctx.config.get("ns012_drop_pct", 0.50))
        trailing = int(ctx.config.get("ns012_trailing_windows", 4))
        windows = (ctx.cohort_stats or {}).get("window_counts", [])
        if len(windows) < trailing:
            return self._store(self.insufficient(ctx, len(alerts), drop_pct), [], [])
        baseline = float(pd.Series(windows[-trailing:]).mean())
        current = float(windows[-1])
        if baseline <= 0:
            return self._store(self.insufficient(ctx, len(alerts), drop_pct), [], [])
        drop = (baseline - current) / baseline
        explanation = _registry_explanation(ctx.entity_id)
        value = float(drop)
        result = self.build_result(
            ctx,
            value,
            drop_pct,
            len(alerts),
            severity="HIGH",
            metadata={
                "baseline": baseline,
                "current": current,
                "registry_explanation": explanation,
            },
        )
        if explanation:
            result.is_flagged = False
            result.metadata["suppressed_by_registry"] = True
        refs = column_ids(alerts, "alert_id")[:5]
        return self._store(
            result,
            frame_rows(alerts.head(5), "alert_id", refs),
            frame_rows(alerts.tail(5), "alert_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for NS-012."""
        return self._bundle(result, self.id)


NS_SIGNALS: list[type[Signal]] = [
    NS001CoverageGap,
    NS002SilenceStreak,
    NS003CategoryAbsence,
    NS004MitreAbsence,
    NS005ExpectedSourceAbsent,
    NS006PerimeterBlind,
    NS007LowActivityDetrended,
    NS008InternetBlindspot,
    NS009TelemetryGapSpike,
    NS010SilentCriticalEstate,
    NS011NoAfterHours,
    NS012FeedTruncation,
]
