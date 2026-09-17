#!/usr/bin/env python3
"""Deterministic 2-minute demo dataset (TASK 8.5).

Five CSEs (seed 42): CSE_HEALTHY, CSE_FASTCLOSE, CSE_SILENT, CSE_BULKCLOSE,
CSE_BYPASS. Timestamps span ~12 months via whole-week offsets that preserve
sub-day patterns (bulk-close windows, dwell times, time-of-day).
CSE_FASTCLOSE and CSE_BULKCLOSE are clearly compromised.

Usage: python scripts/seed_demo_data.py  (or .venv python on Windows)
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")

from satsa.signals.runner import run_entity  # noqa: E402
from satsa.synthetic.adversarial import enforce_escalation_bypass  # noqa: E402
from satsa.synthetic.generator import generate_entity  # noqa: E402
from satsa.synthetic.scenarios import ScenarioConfig  # noqa: E402

SEED = 42
WEEKS = 52
DEMO_SPECS = [
    ("CSE_HEALTHY", "D1", 200, 4201, [], "healthy baseline"),
    ("CSE_FASTCLOSE", "S2", 200, 4202, ["SIG_PREMATURE_CLOSE"], "rushed critical closures"),
    ("CSE_SILENT", "D3", 200, 4203, ["SIG_COVERAGE_GAP"], "dark critical assets"),
    ("CSE_BULKCLOSE", "S7", 200, 4204, ["SIG_BULK_CLOSE"], "analyst batch closures"),
    ("CSE_BYPASS", "D5", 200, 4205, ["SIG_ESCALATION_BYPASS"], "critical cases skip escalation"),
]

_TS_COLUMNS = {
    "alerts": ["detected_ts", "ack_ts", "ingest_ts"],
    "cases": ["detected_ts", "ack_ts", "open_ts", "close_ts", "ingest_ts"],
    "investigations": ["detected_ts", "ack_ts", "triage_start_ts", "triage_end_ts", "close_ts", "ingest_ts"],
    "escalations": ["escalated_ts", "ingest_ts"],
    "assets": ["ingest_ts"],
    "telemetry": ["observed_ts", "ingest_ts"],
}


def _spread_weeks(entity_dir: Path, seed: int) -> None:
    """Shift timestamps back by whole weeks (0-51) across ~12 months.

    Offsets are constant per analyst (burst patterns stay clustered in
    absolute time) and whole weeks (time-of-day and dwell patterns intact).
    Tables without analyst_id share one entity-wide offset.
    """
    rng = np.random.default_rng(seed)
    analysts: set[str] = set()
    cached: dict[str, pd.DataFrame] = {}
    for table in _TS_COLUMNS:
        path = entity_dir / f"{table}.parquet"
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        cached[table] = frame
        if not frame.empty and "analyst_id" in frame.columns:
            analysts.update(frame["analyst_id"].fillna("unknown").astype(str).unique().tolist())
    offset_weeks = {analyst: int(rng.integers(0, WEEKS)) for analyst in sorted(analysts)}
    fallback_weeks = int(rng.integers(0, WEEKS))
    for table, columns in _TS_COLUMNS.items():
        if table not in cached:
            continue
        frame = cached[table]
        if frame.empty:
            continue
        if "analyst_id" in frame.columns:
            groups = frame["analyst_id"].fillna("unknown").astype(str)
            offsets = pd.to_timedelta(groups.map(offset_weeks).to_numpy() * 7, unit="D")
        else:
            offsets = pd.to_timedelta(np.full(len(frame), fallback_weeks * 7), unit="D")
        for column in columns:
            if column not in frame.columns:
                continue
            stamps = pd.to_datetime(frame[column], utc=True, errors="coerce")
            frame[column] = (stamps - offsets).astype(str)
        frame.to_parquet(path)


def main() -> int:
    """Generate the demo corpora, verify signatures, print the demo CLI."""
    base = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    for entity_id, scenario_id, volume, seed, planted, description in DEMO_SPECS:
        scenario = ScenarioConfig(
            entity_id=entity_id, scenario_id=scenario_id, alert_volume=volume,
            seed=seed, planted_signals=planted, description=description,
            alert_volume_range=(180, 220),
        )
        generate_entity(scenario, base_time=base)
        if entity_id == "CSE_BYPASS":
            enforce_escalation_bypass(Path("data/synthetic") / entity_id)
        _spread_weeks(Path("data/synthetic") / entity_id, SEED + seed)
        print(f"generated {entity_id} ({description})")
    fast = run_entity("CSE_FASTCLOSE")
    bulk = run_entity("CSE_BULKCLOSE")
    fast_ids = sorted(k for k, v in fast.items() if v.is_flagged)
    bulk_ids = sorted(k for k, v in bulk.items() if v.is_flagged)
    assert "EG-001" in fast_ids, f"demo compromised entity must fire EG-001: {fast_ids}"
    assert "EG-006" in bulk_ids, f"demo compromised entity must fire EG-006: {bulk_ids}"
    first = fast["EG-001"].finding_id
    print("demo signatures verified: CSE_FASTCLOSE -> EG-001, CSE_BULKCLOSE -> EG-006")
    print("")
    print("Demo CLI sequence:")
    print("  satsa ingest --cse-id CSE_FASTCLOSE --input-path data/synthetic/CSE_FASTCLOSE/")
    print("  satsa run --config configs/default.yaml")
    print("  satsa audit verify")
    print(f"  satsa explain --finding-id {first}")
    print("  satsa validate --labels data/synthetic/ground_truth.parquet")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
