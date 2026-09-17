"""Deterministic synthetic multi-CSE corpora generator (numpy-seeded only)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from satsa.synthetic.scenarios import SCENARIOS, ScenarioConfig

_TABLES = ["alerts", "cases", "investigations", "escalations", "assets", "telemetry"]

_SYNONYM_SLOTS: list[list[str]] = [
    ["verified", "checked"],
    ["closed", "resolved"],
]

_TEMPLATE_BASE = (
    "Standard triage playbook followed for this alert per soc runbook section four. "
    "Collected edr firewall ids auth sysmon telemetry and preserved chain of custody. "
    "Reviewed process tree network connections registry persistence and scheduled tasks. "
    "Correlated with threat intel and historical cases with no lateral movement observed. "
    "Documented timeline of events and {verb2} the alert evidence for audit purposes. "
    "Peer reviewed the findings and case {verb3} as benign per procedure."
)


def _load_thresholds(config_dir: str | Path = "configs") -> dict[str, Any]:
    """Load numeric cutoffs from thresholds.yaml to avoid hardcoded values."""
    path = Path(config_dir) / "thresholds.yaml"
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _hashed_analyst(label: str, salt: str = "satsa-synthetic") -> str:
    """Return a deterministic 64-char hex analyst identifier."""
    return hashlib.sha256(f"{label}{salt}".encode()).hexdigest()


def _record_hash(payload: str) -> str:
    """Return a deterministic record hash."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _utc(base: datetime, days: float = 0.0, minutes: float = 0.0, seconds: float = 0.0) -> datetime:
    """Shift a UTC datetime by the given offsets."""
    return base + timedelta(days=float(days), minutes=float(minutes), seconds=float(seconds))


def _template_note(host: str, rng: np.random.Generator) -> str:
    """Build boilerplate notes with minor word swaps for high TF-IDF overlap."""
    second = str(rng.choice(_SYNONYM_SLOTS[0]))
    third = str(rng.choice(_SYNONYM_SLOTS[1]))
    _ = host
    return _TEMPLATE_BASE.format(verb2=second, verb3=third)


def generate_entity(
    scenario: ScenarioConfig,
    output_root: str | Path = "data/synthetic",
    config_dir: str | Path = "configs",
    base_time: datetime | None = None,
) -> dict[str, Path]:
    """Generate six parquet files for one scenario entity.

    Zero-record behaviour: when alert_volume is zero, empty parquets with the
    canonical columns are still written so downstream stages see a valid,
    zero-row CSE instead of a missing directory.

    Args:
        scenario: ScenarioConfig describing volumes and planted signals.
        output_root: Root directory for data/synthetic/{entity_id}/ outputs.
        config_dir: Directory containing thresholds.yaml.
        base_time: Reference UTC time (defaults to now, truncated to seconds).

    Returns:
        Mapping of table name to written parquet path.
    """
    thresholds = _load_thresholds(config_dir)
    premature_minutes = float(thresholds.get("premature_close_minutes", 5))
    bulk_window_seconds = float(thresholds.get("bulk_close_window_seconds", 60))
    sla_hours = float(thresholds.get("sla_breach_hours", 72))
    rng = np.random.default_rng(scenario.seed)
    now = base_time or datetime.now(UTC).replace(microsecond=0)
    entity_dir = Path(output_root) / scenario.entity_id
    entity_dir.mkdir(parents=True, exist_ok=True)
    ingest_ts = now
    source_hash = _record_hash(scenario.entity_id)[:16]

    num_assets = int(max(8, scenario.alert_volume // 10))
    severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    severity_probs = np.array([0.15, 0.25, 0.30, 0.20, 0.10], dtype=float)
    severity_probs = severity_probs / float(np.sum(severity_probs))
    asset_ids = [f"{scenario.entity_id}-asset-{i:03d}" for i in range(num_assets)]
    critical_count = max(2, num_assets // 4)
    critical_assets = set(asset_ids[:critical_count])

    assets_rows: list[dict[str, Any]] = []
    for idx, asset_id in enumerate(asset_ids):
        is_critical = asset_id in critical_assets
        gap = False
        if "SIG_COVERAGE_GAP" in scenario.planted_signals and is_critical:
            gap = True
        assets_rows.append(
            {
                "asset_id": asset_id,
                "hostname": f"host-{idx:03d}.example",
                "criticality": "high" if is_critical else "medium",
                "environment": "production",
                "os_family": "linux",
                "internet_facing": bool(idx % 2 == 0),
                "gap_flag": bool(gap),
                "ingest_ts": ingest_ts,
                "source_file_hash": source_hash,
                "record_hash": _record_hash(f"{asset_id}{scenario.seed}"),
            }
        )

    n_alerts = int(scenario.alert_volume)
    alert_asset_choices: Any = (
        rng.integers(0, max(1, num_assets - 2), size=n_alerts) if n_alerts else []
    )
    alerts_rows: list[dict[str, Any]] = []
    for i in range(n_alerts):
        asset_idx = int(alert_asset_choices[i]) if n_alerts else 0
        asset_id = asset_ids[asset_idx]
        sev = str(rng.choice(severities, p=severity_probs))
        if scenario.scenario_id == "S6" and i % 5 == 0:
            sev = "HIGH"
        detected = _utc(now, days=-float(rng.uniform(0, 29)), minutes=-float(rng.uniform(0, 1400)))
        ack = _utc(detected, minutes=float(rng.uniform(5, 120)))
        alerts_rows.append(
            {
                "alert_id": f"{scenario.entity_id}-alert-{i:05d}",
                "asset_id": asset_id,
                "title": f"Suspicious activity {i} on {asset_id}",
                "severity_raw": sev,
                "severity_norm": sev,
                "status": "CLOSED" if i % 3 == 0 else "OPEN",
                "category": str(rng.choice(["MALWARE", "PHISHING", "INTRUSION", "OTHER"])),
                "analyst_id": _hashed_analyst(f"analyst-{i % 5}-{scenario.seed}"),
                "detected_ts": detected,
                "ack_ts": ack,
                "source": "edr",
                "ingest_ts": ingest_ts,
                "source_file_hash": source_hash,
                "record_hash": _record_hash(f"{scenario.entity_id}-alert-{i}"),
            }
        )

    n_cases = max(n_alerts // 2, 10) if n_alerts else 0
    if scenario.scenario_id == "S7":
        n_cases = max(n_cases, 150)
    cases_rows: list[dict[str, Any]] = []
    bulk_analyst = _hashed_analyst(f"ANON_A1-{scenario.seed}")
    bulk_center = _utc(now, days=-2)
    for i in range(n_cases):
        sev = str(rng.choice(severities, p=severity_probs))
        tier: str = str(rng.choice(["T1", "T2", "T3"], p=[0.5, 0.3, 0.2]))
        analyst = _hashed_analyst(f"analyst-{i % 5}-{scenario.seed}")
        open_ts = _utc(now, days=-float(rng.uniform(0, 29)), minutes=-float(rng.uniform(0, 1400)))
        close_ts: datetime | None = None
        status = "OPEN"
        if scenario.scenario_id == "S2" and sev == "CRITICAL":
            close_ts = _utc(open_ts, minutes=float(premature_minutes - 1.0))
            status = "CLOSED"
        elif scenario.scenario_id == "S5":
            open_ts = _utc(now, days=-float(rng.uniform(4, 10)))
            close_ts = _utc(open_ts, minutes=float(sla_hours * 60 + rng.uniform(60, 600)))
            status = "CLOSED"
        elif scenario.scenario_id == "S7" and i < 150:
            # Keep all bulk timestamps inside tight_window = bulk_window/3 by construction.
            open_jitter = float(rng.uniform(0, (bulk_window_seconds / 3.0) * 0.75))
            close_delta = float(rng.uniform(0, (bulk_window_seconds / 3.0) * 0.25))
            open_ts = _utc(bulk_center, seconds=open_jitter)
            close_ts = _utc(open_ts, seconds=close_delta)
            analyst = bulk_analyst
            status = "CLOSED"
            sev = "MEDIUM"
        elif scenario.scenario_id == "S8":
            sev = "CRITICAL"
            tier = "T1"
            status = "OPEN"
            close_ts = None
        elif scenario.scenario_id == "S9":
            open_ts = _utc(now, days=-float(rng.integers(0, 29))) + timedelta(
                hours=int(rng.integers(0, 5))
            )
            if i % 2 == 0:
                close_ts = _utc(open_ts, minutes=float(rng.uniform(30, 600)))
                status = "CLOSED"
        else:
            if i % 2 == 0:
                close_ts = _utc(open_ts, minutes=float(rng.uniform(60, 3000)))
                status = "CLOSED"
        detected_ts = _utc(open_ts, minutes=-10.0)
        ack_ts = _utc(open_ts, minutes=-5.0)
        disposition = None
        if status == "CLOSED":
            disposition = str(rng.choice(["TRUE_POSITIVE", "FALSE_POSITIVE", "BENIGN"]))
        if scenario.scenario_id == "S6" and i % 4 == 0:
            disposition = "TRUE_POSITIVE"
        cases_rows.append(
            {
                "case_id": f"{scenario.entity_id}-case-{i:05d}",
                "asset_id": asset_ids[i % num_assets] if num_assets else None,
                "alert_ids": [f"{scenario.entity_id}-alert-{(2 * i) % max(1, n_alerts):05d}"]
                if n_alerts
                else [],
                "severity_norm": sev,
                "status": status,
                "disposition_code": disposition,
                "analyst_id": analyst,
                "tier": tier,
                "detected_ts": detected_ts,
                "ack_ts": ack_ts,
                "open_ts": open_ts,
                "close_ts": close_ts,
                "reopen_count": int(
                    3
                    if (scenario.scenario_id == "S6" and i % 4 == 0)
                    else (1 if i % 9 == 0 else 0)
                ),
                "ingest_ts": ingest_ts,
                "source_file_hash": source_hash,
                "record_hash": _record_hash(f"{scenario.entity_id}-case-{i}"),
            }
        )

    investigations_rows: list[dict[str, Any]] = []
    for i, case in enumerate(cases_rows):
        host = str(case.get("asset_id", "unknown"))
        if scenario.scenario_id == "S4":
            notes = _template_note(host, rng)
        else:
            notes = (
                f"Review of {host} case {case['case_id']}: "
                f"checked telemetry and documented findings {i}."
            )
        triage_start = _utc(case["open_ts"], minutes=5.0)
        triage_end = _utc(triage_start, minutes=float(rng.uniform(15, 180)))
        investigations_rows.append(
            {
                "investigation_id": f"{scenario.entity_id}-inv-{i:05d}",
                "case_id": case["case_id"],
                "analyst_id": case["analyst_id"],
                "detected_ts": case["detected_ts"],
                "ack_ts": case["ack_ts"],
                "triage_start_ts": triage_start,
                "triage_end_ts": triage_end,
                "close_ts": case["close_ts"],
                "notes": notes,
                "steps": [],
                "ingest_ts": ingest_ts,
                "source_file_hash": source_hash,
                "record_hash": _record_hash(f"{scenario.entity_id}-inv-{i}"),
            }
        )

    escalations_rows: list[dict[str, Any]] = []
    if scenario.scenario_id != "S8":
        for i, case in enumerate(cases_rows):
            if case["severity_norm"] == "CRITICAL" and i % 3 == 0:
                escalations_rows.append(
                    {
                        "escalation_id": f"{scenario.entity_id}-esc-{i:05d}",
                        "case_id": case["case_id"],
                        "from_tier": "T1",
                        "to_tier": "T2",
                        "escalated_ts": _utc(case["open_ts"], minutes=30.0),
                        "ingest_ts": ingest_ts,
                        "source_file_hash": source_hash,
                        "record_hash": _record_hash(f"{scenario.entity_id}-esc-{i}"),
                    }
                )

    telemetry_rows: list[dict[str, Any]] = []
    sources = ["edr", "firewall", "ids", "auth"]
    for asset in assets_rows:
        asset_sources = list(sources)
        if asset["gap_flag"]:
            asset_sources = ["edr"]
        for src in asset_sources:
            telemetry_rows.append(
                {
                    "telemetry_id": f"{asset['asset_id']}-{src}",
                    "asset_id": asset["asset_id"],
                    "source": src,
                    "observed_ts": _utc(now, days=-1.0),
                    "ingest_ts": ingest_ts,
                    "source_file_hash": source_hash,
                    "record_hash": _record_hash(f"{asset['asset_id']}-{src}"),
                }
            )

    frames = {
        "alerts": pd.DataFrame(alerts_rows),
        "cases": pd.DataFrame(cases_rows),
        "investigations": pd.DataFrame(investigations_rows),
        "escalations": pd.DataFrame(escalations_rows),
        "assets": pd.DataFrame(assets_rows),
        "telemetry": pd.DataFrame(telemetry_rows),
    }
    written: dict[str, Path] = {}
    for table in _TABLES:
        path = entity_dir / f"{table}.parquet"
        frame = frames[table]
        if frame.empty:
            frame = pd.DataFrame({"_empty": pd.Series(dtype="object")})
        frame.to_parquet(path, index=False)
        written[table] = path
    return written


def generate_all(
    output_root: str | Path = "data/synthetic",
    config_dir: str | Path = "configs",
    base_time: datetime | None = None,
) -> dict[str, dict[str, Path]]:
    """Generate corpora for all ten scenarios.

    Args:
        output_root: Root directory for synthetic outputs.
        config_dir: Directory containing thresholds.yaml.
        base_time: Optional fixed reference time for reproducibility.

    Returns:
        Mapping of entity_id to per-table parquet paths.
    """
    results: dict[str, dict[str, Path]] = {}
    for entity_id, scenario in SCENARIOS.items():
        results[entity_id] = generate_entity(scenario, output_root, config_dir, base_time)
    return results
