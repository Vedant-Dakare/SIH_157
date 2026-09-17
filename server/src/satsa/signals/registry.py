"""Signal registry: auto-discovery, config gating, schema validation, catalogue."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from satsa.errors import SatsaSignalError
from satsa.signals._config import signal_enabled
from satsa.signals.anomaly import ensemble_scores  # noqa: F401  (documents anomaly backend)
from satsa.signals.base import Signal
from satsa.signals.composite import DEFAULT_COMPOSITES
from satsa.signals.execution_gaps import EG_SIGNALS
from satsa.signals.negative_space import NS_SIGNALS

_SIGNAL_MODULES = [
    "satsa.signals.execution_gaps",
    "satsa.signals.negative_space",
]


def _discover() -> list[type[Signal]]:
    """Import signal modules and collect Signal subclasses (deduped by id)."""
    for module_name in _SIGNAL_MODULES:
        importlib.import_module(module_name)
    seen: dict[str, Any] = {}
    for cls in Signal.__subclasses__():
        if cls.id in ("BASE", "COMP-BASE"):
            continue
        seen[cls.id] = cls
    for cls in list(seen.values()):
        for sub in cls.__subclasses__():
            if sub.id not in ("BASE", "COMP-BASE"):
                seen[sub.id] = sub
    ordered = [c for c in EG_SIGNALS + NS_SIGNALS if c.id in seen]
    ordered += [c for cid, c in seen.items() if c not in ordered]
    return ordered


def get_enabled_signals(config_dir: str | Path = "configs") -> list[Signal]:
    """Return instantiated signals gated by the signals.yaml enabled flag."""
    return [cls() for cls in _discover() if signal_enabled(cls.id, config_dir)]


def get_signal(signal_id: str, config_dir: str | Path = "configs") -> Signal | None:
    """Return one enabled signal by id, or None when unknown or disabled."""
    for signal in get_enabled_signals(config_dir):
        if signal.id == signal_id:
            return signal
    return None


def validate_schema(
    feature_schema: list[str], config_dir: str | Path = "configs"
) -> None:
    """Fail loudly when a signal's required_feature is missing from the schema."""
    missing: dict[str, list[str]] = {}
    for signal in get_enabled_signals(config_dir):
        absent = [f for f in signal.required_features if f not in feature_schema]
        if absent:
            missing[signal.id] = absent
    if missing:
        raise SatsaSignalError(f"signal/feature schema mismatch: {missing}")


def composite_rules(config_dir: str | Path = "configs") -> dict[str, Any]:
    """Return composite rules: code defaults extended by signals.yaml-only additions."""
    import yaml

    rules = dict(DEFAULT_COMPOSITES)
    path = Path(config_dir) / "signals.yaml"
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            extra = (data.get("composites", {}) or {})
            for comp_id, rule in extra.items():
                rules[comp_id] = rule
        except Exception:
            pass
    return rules


def generate_catalogue(output_path: str | Path = "docs/SIGNAL_CATALOGUE.md") -> Path:
    """Auto-generate the signal catalogue from registry metadata."""
    from satsa.features.entity_features import FEATURE_SCHEMA

    signals = get_enabled_signals()
    lines = [
        "# SATSA Signal Catalogue",
        "",
        "Auto-generated from the signal registry. Do not edit by hand.",
        "",
        f"Total enabled signals: {len(signals)}",
        f"Composite rules: {len(composite_rules())}",
        "",
        "| ID | Name | Family | Severity | Required features |",
        "|----|------|--------|----------|-------------------|",
    ]
    for signal in signals:
        lines.append(
            f"| {signal.id} | {signal.name} | {signal.family} | "
            f"{signal.default_severity} | {', '.join(signal.required_features)} |"
        )
    lines += [
        "",
        "## Composite rules",
        "",
    ]
    for comp_id, rule in composite_rules().items():
        lines.append(f"- **{comp_id}** ({rule.get('name', '')}): `{rule.get('render', '')}`")
    lines += ["", f"Feature schema columns: {len(FEATURE_SCHEMA)}", ""]
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target
