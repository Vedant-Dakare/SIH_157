"""Phase 3 calibration tests (new file, Phase 0+1+2 untouched)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pytest
from _pytest.logging import LogCaptureFixture


def test_no_labels_means_uncalibrated(tmp_path: Path) -> None:
    """Missing artefact emits calibrated:false without crashing."""
    from satsa.ml.calibration import calibrate_scores

    out = calibrate_scores(
        [0.2, 0.8],
        ["f1"],
        calibrator_path=tmp_path / "missing.joblib",
    )
    assert out["calibrated"] is False
    assert out["calibrated_scores"] == [20.0, 80.0]


def test_feature_mismatch_logs_error_not_silent(
    tmp_path: Path, caplog: LogCaptureFixture
) -> None:
    """Feature drift emits calibrated:false (calibration layer)."""
    from satsa.ml.calibration import calibrate_scores, train_calibrator

    artefact = tmp_path / "cal.joblib"
    train_calibrator(
        np.linspace(0.05, 0.95, 20),
        [0, 1] * 10,
        ["f1", "f2"],
        output_path=artefact,
        registry_path=tmp_path / "reg.json",
    )
    with caplog.at_level(logging.ERROR):
        out = calibrate_scores([0.5], ["f1", "WRONG"], calibrator_path=artefact)
    assert out["calibrated"] is False
    assert any("drift" in r.message for r in caplog.records)


def test_registry_mismatch_raises_and_brier_recorded(tmp_path: Path) -> None:
    """Registry load mismatch raises; training records Brier in registry."""
    from satsa.errors import SatsaSignalError
    from satsa.ml.calibration import train_calibrator
    from satsa.ml.registry import ModelRegistry

    reg_path = tmp_path / "registry.json"
    registry = ModelRegistry(path=reg_path)
    artefact = tmp_path / "cal2.joblib"
    rng = np.random.default_rng(0)
    scores = rng.random(60).tolist()
    labels = (np.asarray(scores) > 0.5).astype(int).tolist()
    meta = train_calibrator(scores, labels, ["f1"], output_path=artefact, registry_path=reg_path)
    with open(reg_path, encoding="utf-8") as handle:
        data = json.load(handle)
    assert any(r["name"] == "risk_calibrator" for r in data)
    assert "brier_score" in meta
    with pytest.raises(SatsaSignalError):
        registry.load("risk_calibrator", current_features=["other"])
