"""Abstract Signal framework: context, results, evidence, reason codes."""

from __future__ import annotations

import hashlib
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal

Family = Literal["execution_gap", "negative_space", "peer", "anomaly", "composite"]


@dataclass
class SignalContext:
    """Inputs available to every signal computation."""

    entity_id: str
    run_id: str
    window_start: str
    window_end: str
    features: dict[str, float]
    alerts: Any = None
    cases: Any = None
    investigations: Any = None
    escalations: Any = None
    assets: Any = None
    telemetry: Any = None
    cohort_stats: dict[str, Any] = field(default_factory=dict)
    cohort_features: dict[str, list[float]] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    seed: int = 42


@dataclass
class SignalResult:
    """Outcome of one signal computation for one entity."""

    finding_id: str
    entity_id: str
    signal_id: str
    value: float
    threshold: float
    score: float
    severity: str
    confidence: str
    sample_size: int
    window_start: str
    window_end: str
    is_flagged: bool
    contributing_rows_ref: list[str] = field(default_factory=list)
    insufficient_data: bool = False
    cohort_too_small: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceBundle:
    """Row-level supporting and counter evidence for a finding."""

    finding_id: str
    supporting_rows: list[dict[str, Any]] = field(default_factory=list)
    counter_rows: list[dict[str, Any]] = field(default_factory=list)
    counter_none_reason: str = ""
    cohort_comparison: dict[str, Any] = field(default_factory=dict)
    evidence_id: str = ""


@dataclass
class ReasonCode:
    """Human-readable explanation of a signal result."""

    code: str
    label: str
    observed: float
    threshold: float
    comparator: str
    peer_baseline: dict[str, Any]
    window: str
    severity: str
    confidence: str
    plain_language: str


def _clean_float(value: Any, default: float = 0.0) -> float:
    """Coerce to finite float; NaN/inf become the default (never leaks NaN)."""
    try:
        result = float(value)
    except Exception:
        return float(default)
    if result != result or result in (float("inf"), float("-inf")):
        return float(default)
    return float(result)


def _finding_id(signal_id: str, entity_id: str, window: str, seed: int) -> str:
    """Deterministic finding UUID (uuid5) so identical inputs give identical results."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{signal_id}|{entity_id}|{window}|{seed}"))


def _evidence_id(signal_id: str, entity_id: str, window: str, row_ids: list[str]) -> str:
    """Hash of signal_id + entity_id + window + row ids."""
    payload = "|".join([signal_id, entity_id, window, *sorted(row_ids)])
    return hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest()


class Signal(ABC):
    """Abstract base class for all SATSA signals."""

    id: ClassVar[str] = "BASE"
    name: ClassVar[str] = "Base signal"
    family: ClassVar[Family] = "execution_gap"
    required_features: ClassVar[list[str]] = []
    default_severity: ClassVar[str] = "MEDIUM"

    def min_n(self, ctx: SignalContext) -> int:
        """Return the minimum sample size from config (default signal_min_n)."""
        try:
            return int(ctx.config.get("signal_min_n", 5))
        except Exception:
            return 5

    def insufficient(self, ctx: SignalContext, sample_size: int, threshold: float) -> SignalResult:
        """Build the canonical insufficient-data result (never flagged, never NaN)."""
        return SignalResult(
            finding_id=_finding_id(self.id, ctx.entity_id, ctx.window_start, ctx.seed),
            entity_id=ctx.entity_id,
            signal_id=self.id,
            value=0.0,
            threshold=_clean_float(threshold),
            score=0.0,
            severity="INFO",
            confidence="LOW",
            sample_size=int(sample_size),
            window_start=ctx.window_start,
            window_end=ctx.window_end,
            is_flagged=False,
            insufficient_data=True,
        )

    def build_result(
        self,
        ctx: SignalContext,
        value: float,
        threshold: float,
        sample_size: int,
        comparator: str = ">=",
        severity: str | None = None,
        confidence: str = "MEDIUM",
        row_refs: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SignalResult:
        """Build a sanitised result with normalised score in [0, 1]."""
        clean_value = _clean_float(value)
        clean_threshold = _clean_float(threshold)
        if comparator == ">=":
            flagged = bool(clean_value >= clean_threshold)
        else:
            flagged = bool(clean_value <= clean_threshold)
        if clean_threshold > 0:
            score = clean_value / clean_threshold
        else:
            score = 1.0 if flagged else 0.0
        score = _clean_float(max(0.0, min(1.0, score)))
        return SignalResult(
            finding_id=_finding_id(self.id, ctx.entity_id, ctx.window_start, ctx.seed),
            entity_id=ctx.entity_id,
            signal_id=self.id,
            value=clean_value,
            threshold=clean_threshold,
            score=score,
            severity=severity or self.default_severity,
            confidence=confidence,
            sample_size=int(sample_size),
            window_start=ctx.window_start,
            window_end=ctx.window_end,
            is_flagged=flagged,
            contributing_rows_ref=list(row_refs or []),
            insufficient_data=False,
            metadata=dict(metadata or {}),
        )

    @abstractmethod
    def compute(self, ctx: SignalContext) -> SignalResult:
        """Compute the signal for one entity in one window."""
        raise NotImplementedError

    @abstractmethod
    def evidence(self, result: SignalResult) -> EvidenceBundle:
        """Return row-level evidence for a computed result."""
        raise NotImplementedError

    def explain(self, result: SignalResult) -> ReasonCode:
        """Render a one-sentence non-technical reason code for a result."""
        comparator = ">=" if result.is_flagged else "<"
        return ReasonCode(
            code=self.id,
            label=self.name,
            observed=result.value,
            threshold=result.threshold,
            comparator=comparator,
            peer_baseline={},
            window=f"{result.window_start}..{result.window_end}",
            severity=result.severity,
            confidence=result.confidence,
            plain_language=(
                f"{self.name} was {'observed' if result.is_flagged else 'not observed'} "
                f"for {result.entity_id} in this window."
            ),
        )
