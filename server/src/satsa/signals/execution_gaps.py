"""Execution-gap signals EG-001..EG-014 (concrete Signal subclasses)."""

from __future__ import annotations

from typing import Any, ClassVar

import pandas as pd

from satsa.features import workflow as workflow_mod
from satsa.features._common import closed_only, column_ids, to_utc
from satsa.features.temporal import detect_batch_close
from satsa.features.text import lite_similarity
from satsa.signals._evidence import frame_rows, make_bundle, matching_rows
from satsa.signals.base import EvidenceBundle, Family, Signal, SignalContext, SignalResult

_SEV_RANK = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0, "UNKNOWN": -1}


def _cases(ctx: SignalContext) -> pd.DataFrame:
    """Return cases as a DataFrame (empty when absent)."""
    if isinstance(ctx.cases, pd.DataFrame):
        return ctx.cases
    return pd.DataFrame()


def _alerts(ctx: SignalContext) -> pd.DataFrame:
    """Return alerts as a DataFrame (empty when absent)."""
    if isinstance(ctx.alerts, pd.DataFrame):
        return ctx.alerts
    return pd.DataFrame()


def _escalations(ctx: SignalContext) -> pd.DataFrame:
    """Return escalations as a DataFrame (empty when absent)."""
    if isinstance(ctx.escalations, pd.DataFrame):
        return ctx.escalations
    return pd.DataFrame()


def _investigations(ctx: SignalContext) -> pd.DataFrame:
    """Return investigations as a DataFrame (empty when absent)."""
    if isinstance(ctx.investigations, pd.DataFrame):
        return ctx.investigations
    return pd.DataFrame()


class _EvidenceMixin:
    """Cache supporting/counter rows during compute for later evidence()."""

    _cache: dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]] = {}

    def _store(
        self,
        result: SignalResult,
        supporting: list[dict[str, Any]],
        counter: list[dict[str, Any]],
        cohort_comparison: dict[str, Any] | None = None,
    ) -> SignalResult:
        """Cache evidence rows against the finding id."""
        self._cache[result.finding_id] = (supporting, counter, dict(cohort_comparison or {}))
        return result

    def _bundle(self, result: SignalResult, signal_id: str) -> EvidenceBundle:
        """Build the cached evidence bundle for a result."""
        supporting, counter, cohort = self._cache.get(result.finding_id, ([], [], {}))
        return make_bundle(signal_id, result, supporting, counter, cohort_comparison=cohort)


class EG001PrematureClosure(_EvidenceMixin, Signal):
    """EG-001 Premature closure of CRITICAL cases."""

    id = "EG-001"
    name = "Premature closure"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["premature_rate", "case_count"]
    default_severity = "HIGH"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when premature CRITICAL closures meet or exceed the threshold."""
        cases = _cases(ctx)
        threshold = float(ctx.config.get("premature_rate_threshold", 0.20))
        prem_min = float(ctx.config.get("premature_close_minutes", 5))
        crit = cases
        if not cases.empty and "severity_norm" in cases.columns:
            crit = cases[cases["severity_norm"] == "CRITICAL"]
        closed = closed_only(crit)
        if len(closed) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(closed), threshold), [], [])
        minutes = (to_utc(closed["close_ts"]) - to_utc(closed["open_ts"])).dt.total_seconds() / 60.0
        mask = (minutes >= 0) & (minutes < prem_min)
        value = float(mask.mean())
        refs = column_ids(closed[mask], "case_id")
        result = self.build_result(
            ctx, value, threshold, len(closed), row_refs=refs, severity="HIGH"
        )
        supporting = frame_rows(closed[mask], "case_id", refs)
        counter = frame_rows(closed[~mask], "case_id", [])
        return self._store(result, supporting, counter)

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-001."""
        return self._bundle(result, self.id)


class EG002ReopenChurn(_EvidenceMixin, Signal):
    """EG-002 Repeated case reopens."""

    id = "EG-002"
    name = "Reopen churn"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["reopen_rate", "case_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when the reopen rate meets or exceeds the threshold."""
        cases = _cases(ctx)
        threshold = float(ctx.config.get("reopen_rate_threshold", 0.15))
        minimum = int(ctx.config.get("reopen_churn_min_reopens", 2))
        if cases.empty or "reopen_count" not in cases.columns:
            return self._store(self.insufficient(ctx, 0, threshold), [], [])
        if len(cases) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(cases), threshold), [], [])
        mask = cases["reopen_count"] >= minimum
        value = float(mask.mean())
        refs = column_ids(cases[mask], "case_id")
        result = self.build_result(ctx, value, threshold, len(cases), row_refs=refs)
        return self._store(
            result,
            frame_rows(cases[mask], "case_id", refs),
            frame_rows(cases[~mask], "case_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-002."""
        return self._bundle(result, self.id)


class EG003EscalationBypass(_EvidenceMixin, Signal):
    """EG-003 CRITICAL cases handled without escalation."""

    id = "EG-003"
    name = "Escalation bypass"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["bypass_rate", "case_count"]
    default_severity = "HIGH"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when the critical-case bypass rate meets or exceeds the threshold."""
        cases = _cases(ctx)
        esc = _escalations(ctx)
        threshold = float(ctx.config.get("escalation_bypass_rate_threshold", 0.90))
        value = workflow_mod.bypass_rate(cases, esc)
        crit_n = 0
        if not cases.empty and "severity_norm" in cases.columns:
            crit_n = int((cases["severity_norm"] == "CRITICAL").sum())
        if crit_n < self.min_n(ctx):
            return self._store(self.insufficient(ctx, crit_n, threshold), [], [])
        esc_ids: set[str] = set()
        if not esc.empty and "case_id" in esc.columns:
            esc_ids = set(column_ids(esc.dropna(subset=["case_id"]), "case_id"))
        crit = cases[cases["severity_norm"] == "CRITICAL"]
        mask = ~crit["case_id"].astype(str).isin(esc_ids)
        refs = column_ids(crit[mask], "case_id")
        result = self.build_result(
            ctx, value, threshold, crit_n, row_refs=refs, severity="HIGH"
        )
        return self._store(
            result,
            frame_rows(crit[mask], "case_id", refs),
            frame_rows(crit[~mask], "case_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-003."""
        return self._bundle(result, self.id)


class EG004SeverityDowngrade(_EvidenceMixin, Signal):
    """EG-004 Systematic severity downgrade from alert to case."""

    id = "EG-004"
    name = "Severity downgrade bias"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["alert_share_HIGH", "case_share_HIGH"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when mean alert rank exceeds mean case rank beyond the threshold."""
        alerts = _alerts(ctx)
        cases = _cases(ctx)
        threshold = float(ctx.config.get("severity_mismatch_rate_threshold", 0.25))
        if alerts.empty or cases.empty:
            return self._store(self.insufficient(ctx, 0, threshold), [], [])
        alert_ranks = pd.to_numeric(
            alerts["severity_norm"].map(_SEV_RANK), errors="coerce"
        ).dropna()
        case_ranks = pd.to_numeric(
            cases["severity_norm"].map(_SEV_RANK), errors="coerce"
        ).dropna()
        if len(alert_ranks) < self.min_n(ctx) or len(case_ranks) < self.min_n(ctx):
            return self._store(
                self.insufficient(ctx, min(len(alert_ranks), len(case_ranks)), threshold),
                [],
                [],
            )
        value = float(alert_ranks.mean() - case_ranks.mean())
        low = cases[cases["severity_norm"].isin(["LOW", "INFO"])]
        refs = column_ids(low, "case_id")
        result = self.build_result(ctx, value, threshold, len(case_ranks), row_refs=refs[:5])
        return self._store(
            result,
            frame_rows(alerts[alerts["severity_norm"] == "CRITICAL"], "alert_id", []),
            frame_rows(cases[cases["severity_norm"] == "CRITICAL"], "case_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-004."""
        return self._bundle(result, self.id)


class EG005SlaBreach(_EvidenceMixin, Signal):
    """EG-005 Cases breaching the response SLA."""

    id = "EG-005"
    name = "SLA breach backlog"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["sla_breach_rate", "case_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when the SLA breach rate meets or exceeds the threshold."""
        cases = _cases(ctx)
        threshold = float(ctx.config.get("sla_breach_rate_threshold", 0.30))
        sla_hours = float(ctx.config.get("sla_breach_hours", 72))
        closed = closed_only(cases)
        if len(closed) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(closed), threshold), [], [])
        hours = (to_utc(closed["close_ts"]) - to_utc(closed["open_ts"])).dt.total_seconds()
        hours = hours / 3600.0
        mask = hours > sla_hours
        value = float(mask.mean())
        refs = column_ids(closed[mask], "case_id")
        result = self.build_result(ctx, value, threshold, len(closed), row_refs=refs)
        return self._store(
            result,
            frame_rows(closed[mask], "case_id", refs),
            frame_rows(closed[~mask], "case_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-005."""
        return self._bundle(result, self.id)


class EG006BulkClose(_EvidenceMixin, Signal):
    """EG-006 Batch-close bursts by a single analyst."""

    id = "EG-006"
    name = "Bulk close burst"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["case_count", "alert_count"]
    default_severity = "HIGH"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when the largest burst meets or exceeds the minimum count."""
        cases = _cases(ctx)
        threshold = float(ctx.config.get("bulk_close_min_count", 50))
        closed_n = int(closed_only(cases).shape[0])
        if closed_n < self.min_n(ctx):
            return self._store(self.insufficient(ctx, closed_n, threshold), [], [])
        bursts = detect_batch_close(cases)
        value = float(bursts["burst_size"].max()) if not bursts.empty else 0.0
        refs: list[str] = []
        supporting: list[dict[str, Any]] = []
        if not bursts.empty:
            top = bursts.sort_values("burst_size", ascending=False).iloc[0]
            analyst = top["analyst_id"]
            start = pd.to_datetime(top["window_start"], utc=True)
            span = pd.to_timedelta(float(top["burst_duration"]) + 1.0, unit="s")
            closes = to_utc(cases["close_ts"]) if "close_ts" in cases.columns else pd.Series(
                pd.NaT, index=cases.index
            )
            if "analyst_id" in cases.columns:
                sub = cases[
                    (cases["analyst_id"] == analyst)
                    & (closes >= start)
                    & (closes <= start + span)
                ]
            else:
                sub = cases[(closes >= start) & (closes <= start + span)]
            refs = column_ids(sub, "case_id")
            supporting = frame_rows(sub, "case_id", refs)
        result = self.build_result(
            ctx, value, threshold, closed_n, row_refs=refs[:5], severity="HIGH"
        )
        counter = frame_rows(closed_only(cases), "case_id", [])
        return self._store(result, supporting, counter[:5] if not supporting else counter)

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-006."""
        return self._bundle(result, self.id)


class EG007MetricGaming(_EvidenceMixin, Signal):
    """EG-007 Metric gaming: high closure AND high recurrence AND low root-cause."""

    id = "EG-007"
    name = "Metric gaming composite pattern"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["case_count", "reopen_rate", "escalation_rate"]
    default_severity = "HIGH"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when closure/recurrence are top-quartile and root-cause is bottom."""
        cases = _cases(ctx)
        if cases.empty or len(cases) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(cases), 1.0), [], [])
        cohort = ctx.cohort_features or {}
        if "status" in cases.columns:
            closure = float((cases["status"] == "CLOSED").mean())
        else:
            closure = 0.0
        reopen_min = int(ctx.config.get("reopen_churn_min_reopens", 2))
        if "reopen_count" in cases.columns:
            recurrence = float((cases["reopen_count"] >= reopen_min).mean())
        else:
            recurrence = float(ctx.features.get("reopen_rate", 0.0))
        if "disposition_code" in cases.columns:
            disp = cases["disposition_code"].astype(str).tolist()
        else:
            disp = []
        root_total = max(1, len(disp))
        root_cause = float(sum(1 for d in disp if d == "TRUE_POSITIVE") / root_total)
        flags: dict[str, bool] = {}
        trio: tuple[tuple[str, float], ...] = (
            ("closure_rate", closure),
            ("reopen_rate", recurrence),
        )
        trio = trio + (("root_cause_rate", root_cause),)
        for key, val in trio:
            peers = [float(v) for v in cohort.get(key, [])]
            if len(peers) < 4:
                return self._store(self.insufficient(ctx, len(cases), 1.0), [], [])
            series = pd.Series(peers + [val])
            q75 = float(series.quantile(0.75))
            q25 = float(series.quantile(0.25))
            if key == "root_cause_rate":
                flags[key] = bool(val <= q25)
            else:
                flags[key] = bool(val >= q75)
        value = float(sum(1 for v in flags.values() if v) / 3.0)
        result = self.build_result(
            ctx,
            value,
            1.0,
            len(cases),
            severity="HIGH",
            metadata={
                "closure_rate": closure,
                "recurrence_rate": recurrence,
                "root_cause_rate": root_cause,
                "quartile_flags": flags,
            },
        )
        refs = column_ids(cases, "case_id")[:5]
        return self._store(
            result, frame_rows(cases, "case_id", refs), [], {"quartile_flags": flags}
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-007."""
        return self._bundle(result, self.id)


class EG008AfterHoursClosure(_EvidenceMixin, Signal):
    """EG-008 Closures concentrated outside business hours."""

    id = "EG-008"
    name = "After-hours closure rush"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["night_fraction", "case_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when the night-closure fraction meets or exceeds the threshold."""
        cases = _cases(ctx)
        threshold = float(ctx.config.get("eg008_min_fraction", 0.50))
        closed = closed_only(cases)
        if len(closed) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(closed), threshold), [], [])
        hours = to_utc(closed["close_ts"]).dt.hour
        mask = (hours >= 22) | (hours < 6)
        value = float(mask.mean())
        refs = column_ids(closed[mask], "case_id")
        result = self.build_result(ctx, value, threshold, len(closed), row_refs=refs)
        return self._store(
            result,
            frame_rows(closed[mask], "case_id", refs),
            frame_rows(closed[~mask], "case_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-008."""
        return self._bundle(result, self.id)


class EG009Backfill(_EvidenceMixin, Signal):
    """EG-009 Retroactive documentation (ingest far after event)."""

    id = "EG-009"
    name = "Backfill documentation"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["backfill_rate", "alert_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when the backfill rate meets or exceeds the threshold."""
        alerts = _alerts(ctx)
        threshold = float(ctx.config.get("backfill_rate_threshold", 0.10))
        if alerts.empty or len(alerts) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(alerts), threshold), [], [])
        backfilled = workflow_mod.backfill_detection(alerts, "detected_ts")
        value = float(len(backfilled) / max(1, len(alerts)))
        refs = column_ids(backfilled, "alert_id")[:5]
        result = self.build_result(ctx, value, threshold, len(alerts), row_refs=refs)
        return self._store(
            result,
            frame_rows(backfilled, "alert_id", refs),
            frame_rows(alerts, "alert_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-009."""
        return self._bundle(result, self.id)


class EG010TemplateNotes(_EvidenceMixin, Signal):
    """EG-010 Templated investigation notes."""

    id = "EG-010"
    name = "Templated investigation notes"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["template_similarity", "copy_paste_ratio"]
    default_severity = "HIGH"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when mean pairwise note similarity meets or exceeds the threshold."""
        investigations = _investigations(ctx)
        threshold = float(ctx.config.get("template_tfidf_threshold", 0.85))
        min_notes = int(ctx.config.get("template_min_notes", 5))
        notes: list[str] = []
        if not investigations.empty and "notes" in investigations.columns:
            notes = investigations["notes"].dropna().astype(str).tolist()
        if len(notes) < max(self.min_n(ctx), min_notes):
            return self._store(self.insufficient(ctx, len(notes), threshold), [], [])
        score = float(lite_similarity(notes)["mean_pairwise"])
        refs = column_ids(investigations, "investigation_id")[:5]
        result = self.build_result(
            ctx, score, threshold, len(notes), row_refs=refs, severity="HIGH"
        )
        return self._store(
            result,
            frame_rows(investigations, "investigation_id", refs),
            frame_rows(investigations.iloc[::-1], "investigation_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-010."""
        return self._bundle(result, self.id)


class EG011DuplicateChain(_EvidenceMixin, Signal):
    """EG-011 Deep duplicate-case chains."""

    id = "EG-011"
    name = "Duplicate chain depth"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["duplicate_chain_depth", "case_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when duplicate chains or DUPLICATE dispositions are material."""
        cases = _cases(ctx)
        threshold = float(ctx.config.get("duplicate_rate_threshold", 0.10))
        if cases.empty or len(cases) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(cases), threshold), [], [])
        depth = workflow_mod.duplicate_chain_depth(cases)
        if "disposition_code" in cases.columns:
            dup_rate = float((cases["disposition_code"] == "DUPLICATE").mean())
            dupes = cases[cases["disposition_code"] == "DUPLICATE"]
        else:
            dup_rate = 0.0
            dupes = cases.iloc[0:0]
        value = float(max(min(1.0, depth / 5.0), dup_rate))
        refs = column_ids(dupes, "case_id")[:5]
        result = self.build_result(
            ctx, value, threshold, len(cases), row_refs=refs,
            metadata={"depth": depth, "dup_rate": dup_rate},
        )
        dupe_support = matching_rows(cases, "case_id", refs) if dup_rate > 0 else []
        return self._store(result, dupe_support, frame_rows(cases, "case_id", []))

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-011."""
        return self._bundle(result, self.id)


class EG012OrphanRate(_EvidenceMixin, Signal):
    """EG-012 Cases with no linked alerts."""

    id = "EG-012"
    name = "Orphan case rate"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["orphan_case_rate", "case_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when the orphan-case rate meets or exceeds the threshold."""
        cases = _cases(ctx)
        threshold = float(ctx.config.get("orphan_case_rate_threshold", 0.30))
        if cases.empty or len(cases) < self.min_n(ctx):
            return self._store(self.insufficient(ctx, len(cases), threshold), [], [])
        orphans = workflow_mod.orphan_cases(cases)
        value = float(len(orphans) / max(1, len(cases)))
        refs = column_ids(orphans, "case_id")[:5]
        result = self.build_result(ctx, value, threshold, len(cases), row_refs=refs)
        return self._store(
            result,
            frame_rows(orphans, "case_id", refs),
            frame_rows(cases, "case_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-012."""
        return self._bundle(result, self.id)


class EG013PerfectSla(_EvidenceMixin, Signal):
    """EG-013 SLA met everywhere with near-zero dwell variance."""

    id = "EG-013"
    name = "Suspiciously perfect SLA"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["sla_breach_rate", "lat_case_duration_median"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when SLA-met exceeds X% AND dwell-time CV falls below epsilon."""
        cases = _cases(ctx)
        sla_pct = float(ctx.config.get("eg013_sla_met_pct", 0.99))
        epsilon = float(ctx.config.get("eg013_cv_epsilon", 0.05))
        min_cases = int(ctx.config.get("eg013_min_cases", 10))
        sla_hours = float(ctx.config.get("sla_breach_hours", 72))
        closed = closed_only(cases)
        if len(closed) < max(self.min_n(ctx), min_cases):
            return self._store(self.insufficient(ctx, len(closed), sla_pct), [], [])
        hours = (to_utc(closed["close_ts"]) - to_utc(closed["open_ts"])).dt.total_seconds()
        hours = hours / 3600.0
        hours = hours[hours >= 0]
        if hours.empty:
            return self._store(self.insufficient(ctx, len(closed), sla_pct), [], [])
        sla_met = float((hours <= sla_hours).mean())
        mean = float(hours.mean())
        cv = float(hours.std() / mean) if mean > 0 else 0.0
        flagged = bool(sla_met >= sla_pct and cv < epsilon)
        value = float(sla_met * (1.0 - min(1.0, cv / max(epsilon, 1e-9))))
        result = self.build_result(
            ctx,
            value,
            sla_pct,
            len(closed),
            metadata={"sla_met": sla_met, "cv": cv},
        )
        result.is_flagged = flagged
        result.score = float(max(0.0, min(1.0, value / sla_pct if sla_pct else 0.0)))
        refs = column_ids(closed, "case_id")[:5]
        return self._store(
            result, frame_rows(closed, "case_id", refs), [], {"cv": cv, "sla_met": sla_met}
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-013."""
        return self._bundle(result, self.id)


class EG014EscalationNowhere(_EvidenceMixin, Signal):
    """EG-014 Escalation raised but never accepted before closure."""

    id = "EG-014"
    name = "Escalation to nowhere"
    family: ClassVar[Family] = "execution_gap"
    required_features = ["escalation_rate", "case_count"]
    default_severity = "MEDIUM"

    def compute(self, ctx: SignalContext) -> SignalResult:
        """Flag when orphaned escalations meet or exceed the threshold."""
        cases = _cases(ctx)
        esc = _escalations(ctx)
        threshold = float(ctx.config.get("escalation_nowhere_rate_threshold", 0.50))
        if esc.empty or "case_id" not in esc.columns:
            return self._store(self.insufficient(ctx, 0, threshold), [], [])
        if not cases.empty and "case_id" in cases.columns:
            by_case = cases.set_index(cases["case_id"].astype(str))
        else:
            by_case = pd.DataFrame()
        nowhere = 0
        refs: list[str] = []
        for _, row in esc.iterrows():
            case_id = str(row.get("case_id", ""))
            accepted = row.get("accepted_ts", None)
            if by_case.empty or case_id not in by_case.index:
                continue
            case = by_case.loc[case_id]
            tier = str(case["tier"]) if "tier" in by_case.columns else ""
            status = str(case["status"]) if "status" in by_case.columns else ""
            if pd.isna(accepted) and tier == str(row.get("from_tier", "")) and status == "CLOSED":
                nowhere += 1
                refs.append(case_id)
        value = float(nowhere / max(1, len(esc)))
        result = self.build_result(ctx, value, threshold, len(esc), row_refs=refs[:5])
        return self._store(
            result,
            frame_rows(esc[esc["case_id"].astype(str).isin(refs)], "escalation_id", []),
            frame_rows(esc, "escalation_id", []),
        )

    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return cached row evidence for EG-014."""
        return self._bundle(result, self.id)


EG_SIGNALS: list[type[Signal]] = [
    EG001PrematureClosure,
    EG002ReopenChurn,
    EG003EscalationBypass,
    EG004SeverityDowngrade,
    EG005SlaBreach,
    EG006BulkClose,
    EG007MetricGaming,
    EG008AfterHoursClosure,
    EG009Backfill,
    EG010TemplateNotes,
    EG011DuplicateChain,
    EG012OrphanRate,
    EG013PerfectSla,
    EG014EscalationNowhere,
]
