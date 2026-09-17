"""Adversarial edge-case extensions plus ground-truth labelling."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from satsa.synthetic.scenarios import ALL_SIGNAL_IDS, SCENARIOS


def _load_thresholds(config_dir: str | Path = "configs") -> dict[str, Any]:
    """Load numeric cutoffs from thresholds.yaml."""
    path = Path(config_dir) / "thresholds.yaml"
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def enforce_bulk_close(entity_dir: Path, seed: int, config_dir: str | Path = "configs") -> None:
    """Rewrite the first 150 cases to share one analyst and a tight time window."""
    thresholds = _load_thresholds(config_dir)
    window_seconds = float(thresholds.get("bulk_close_window_seconds", 60))
    tight_window = window_seconds / 3.0
    cases_path = entity_dir / "cases.parquet"
    frame = pd.read_parquet(cases_path)
    if len(frame) < 150:
        return
    import hashlib

    analyst = hashlib.sha256(f"ANON_A1-{seed}".encode()).hexdigest()
    center = pd.to_datetime(frame["open_ts"].iloc[0], utc=True)
    rng = np.random.default_rng(seed)
    raw_open: list[Any] = list(rng.uniform(0, tight_window * 0.75, size=150))
    raw_close: list[Any] = list(rng.uniform(0, tight_window * 0.25, size=150))
    open_jitters: list[float] = [float(v) for v in raw_open]
    close_deltas: list[float] = [float(v) for v in raw_close]
    frame.loc[frame.index[:150], "analyst_id"] = analyst
    frame.loc[frame.index[:150], "disposition_code"] = "BENIGN"
    for pos, idx in enumerate(frame.index[:150]):
        open_ts = center + timedelta(seconds=float(open_jitters[pos]))
        close_ts = open_ts + timedelta(seconds=float(close_deltas[pos]))
        frame.at[idx, "open_ts"] = open_ts
        frame.at[idx, "close_ts"] = close_ts
        frame.at[idx, "status"] = "CLOSED"
    frame.to_parquet(cases_path, index=False)


def enforce_escalation_bypass(entity_dir: Path) -> None:
    """Ensure the escalations table is empty for bypass scenarios."""
    esc_path = entity_dir / "escalations.parquet"
    if not esc_path.exists():
        pd.DataFrame({"_empty": pd.Series(dtype="object")}).to_parquet(esc_path, index=False)
        return
    frame = pd.read_parquet(esc_path)
    if len(frame) == 0:
        return
    empty = pd.DataFrame({col: pd.Series(dtype=frame[col].dtype) for col in frame.columns})
    empty.to_parquet(esc_path, index=False)


def corrupt_partial_feed(entity_dir: Path, seed: int, config_dir: str | Path = "configs") -> None:
    """Null 30% of rows and inject monotonicity plus unknown-severity faults."""
    thresholds = _load_thresholds(config_dir)
    null_rate = float(thresholds.get("partial_feed_null_rate", 0.3))
    mono_rate = float(thresholds.get("partial_feed_monotonicity_violation_rate", 0.05))
    unknown_rate = float(thresholds.get("partial_feed_unknown_severity_rate", 0.05))
    rng = np.random.default_rng(seed)
    for table, null_col in [
        ("alerts", "severity_norm"),
        ("cases", "severity_norm"),
        ("investigations", "case_id"),
    ]:
        path = entity_dir / f"{table}.parquet"
        if not path.exists():
            continue
        frame = pd.read_parquet(path)
        if len(frame) == 0:
            continue
        raw_order: list[Any] = list(rng.permutation(len(frame)))
        order: list[int] = [int(v) for v in raw_order]
        n_null = int(len(frame) * null_rate)
        for idx in order[:n_null]:
            row_idx = frame.index[idx]
            if null_col in frame.columns:
                frame.at[row_idx, null_col] = None
        n_mono = max(1, int(len(frame) * mono_rate))
        if "close_ts" in frame.columns and "detected_ts" in frame.columns:
            for idx in order[n_null : n_null + n_mono]:
                row_idx = frame.index[idx]
                detected = pd.to_datetime(frame.at[row_idx, "detected_ts"], utc=True)
                try:
                    frame.at[row_idx, "close_ts"] = detected - timedelta(hours=1)
                except Exception:
                    continue
        n_unknown = max(1, int(len(frame) * unknown_rate))
        if "severity_norm" in frame.columns:
            for idx in order[n_null + n_mono : n_null + n_mono + n_unknown]:
                row_idx = frame.index[idx]
                frame.at[row_idx, "severity_norm"] = "BANANA"
        frame.to_parquet(path, index=False)


def write_ground_truth(
    output_root: str | Path = "data/synthetic", config_dir: str | Path = "configs"
) -> Path:
    """Write ground_truth.parquet labelling every (entity_id, signal_id) pair."""
    thresholds = _load_thresholds(config_dir)
    default_conf = float(thresholds.get("ground_truth_default_confidence", 1.0))
    partial_conf = float(thresholds.get("ground_truth_partial_feed_confidence", 0.7))
    rows: list[dict[str, Any]] = []
    for entity_id, scenario in SCENARIOS.items():
        for signal_id in ALL_SIGNAL_IDS:
            expected = signal_id in scenario.planted_signals
            confidence = float(partial_conf if entity_id == "cse_juliet" else default_conf)
            rationale = (
                f"{scenario.scenario_id} planted {signal_id}"
                if expected
                else f"{scenario.scenario_id} baseline; {signal_id} not planted"
            )
            rows.append(
                {
                    "entity_id": entity_id,
                    "signal_id": signal_id,
                    "scenario_id": scenario.scenario_id,
                    "expected_flag": bool(expected),
                    "confidence": float(confidence),
                    "rationale": rationale,
                }
            )
    frame = pd.DataFrame(rows)
    output_path = Path(output_root) / "ground_truth.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_path, index=False)
    return output_path


def apply_adversarial(
    output_root: str | Path = "data/synthetic", config_dir: str | Path = "configs"
) -> Path:
    """Enforce S7/S8/S10 edge cases then write ground truth.

    Args:
        output_root: Synthetic data root.
        config_dir: Config directory with thresholds.yaml.

    Returns:
        Path to the written ground_truth.parquet.
    """
    root = Path(output_root)
    golf = SCENARIOS.get("cse_golf")
    if golf is not None and (root / "cse_golf").exists():
        enforce_bulk_close(root / "cse_golf", golf.seed, config_dir)
    if (root / "cse_hotel").exists():
        enforce_escalation_bypass(root / "cse_hotel")
    juliet = SCENARIOS.get("cse_juliet")
    if juliet is not None and (root / "cse_juliet").exists():
        corrupt_partial_feed(root / "cse_juliet", juliet.seed, config_dir)
    return write_ground_truth(output_root, config_dir)
