"""Risk-score calibration: isotonic (n>=50) or Platt/logistic (n<50).

Training labels come from data/synthetic/ground_truth.parquet. Artefacts
persist to models/artifacts/risk_calibrator.joblib with Brier score,
reliability curve data and training-data hash. Missing labels emit
calibrated:false (never silently uncalibrated). Feature-list drift logs
ERROR and emits calibrated:false (never crashes).
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CALIBRATOR_PATH = Path("models/artifacts/risk_calibrator.joblib")


def training_data_hash(frame: pd.DataFrame) -> str:
    """Return SHA-256 over the sorted CSV rendering of the training frame."""
    rendered = frame.sort_values(list(frame.columns)).to_csv(index=False)
    return hashlib.sha256(rendered.encode("utf-8", errors="replace")).hexdigest()


def brier_score(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Return the mean squared error between labels and probabilities."""
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    if len(y_true) == 0:
        return 0.0
    return float(np.mean((y_prob - y_true) ** 2))


def _reliability_curve(
    y_true: list[float] | list[int] | Any, y_prob: list[float] | Any, n_bins: int = 10
) -> list[dict[str, float]]:
    """Return reliability-curve bins (bin_center, frac_positive, count)."""
    bins: list[dict[str, float]] = []
    edges: list[float] = [i / n_bins for i in range(n_bins + 1)]
    yt: list[float] = [float(v) for v in list(y_true)]
    yp: list[float] = [float(v) for v in list(y_prob)]

    def _inside(p: float, lo: float, hi: float, last: bool) -> bool:
        if last:
            return p >= lo and p <= hi
        return p >= lo and p < hi

    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        last = i == n_bins - 1
        idx = [j for j, p in enumerate(yp) if _inside(p, lo, hi, last)]
        count = len(idx)
        frac = float(sum(yt[j] for j in idx) / count) if count else 0.0
        bins.append(
            {
                "bin_center": float((lo + hi) / 2.0),
                "frac_positive": float(frac),
                "count": float(count),
            }
        )
    return bins


def load_labels(
    ground_truth_path: str | Path = "data/synthetic/ground_truth.parquet",
) -> pd.DataFrame | None:
    """Load training labels, or None when unavailable (never crashes)."""
    path = Path(ground_truth_path)
    if not path.exists():
        return None
    try:
        frame = pd.read_parquet(path)
    except Exception:
        return None
    if frame.empty or "expected_flag" not in frame.columns:
        return None
    return frame


def train_calibrator(
    scores: list[float] | np.ndarray,
    labels: list[int] | np.ndarray,
    feature_list: list[str],
    training_frame: pd.DataFrame | None = None,
    output_path: str | Path = CALIBRATOR_PATH,
    registry_path: str | Path | None = None,
) -> dict[str, Any]:
    """Fit isotonic (n>=50) or Platt (n<50) calibrator and persist it.

    Records Brier score, reliability curve, training-data hash and registers
    the artefact in models/registry.json. Returns the artefact metadata.
    """
    from sklearn.isotonic import IsotonicRegression
    from sklearn.linear_model import LogisticRegression

    x_list: list[float] = [float(s) for s in list(scores)]
    y_list: list[int] = [int(v) for v in list(labels)]
    n = len(y_list)
    method = "isotonic" if n >= 50 else "platt"
    x_matrix = np.asarray([[v] for v in x_list], dtype=float)
    y_arr = np.asarray(y_list, dtype=int)
    if method == "isotonic":
        iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        iso.fit(x_list, y_arr)
        cal_list: list[float] = [float(v) for v in iso.predict(x_list)]
        calibrated = np.asarray(cal_list, dtype=float)
        model = iso
    else:
        logreg = LogisticRegression()
        logreg.fit(x_matrix, y_arr)
        proba: list[float] = [float(v) for v in logreg.predict_proba(x_matrix)[:, 1]]
        calibrated = np.asarray(proba, dtype=float)
        model = logreg
    brier = brier_score(y_arr, calibrated)
    data_hash = training_data_hash(training_frame) if training_frame is not None else ""
    artefact = {
        "method": method,
        "model": model,
        "feature_list": list(feature_list),
        "training_data_hash": data_hash,
        "brier_score": float(brier),
        "reliability_curve": _reliability_curve(y_arr, calibrated),
        "n_train": int(n),
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artefact, target)
    try:
        from satsa.ml.registry import ModelRegistry

        registry = ModelRegistry(path=registry_path) if registry_path else ModelRegistry()
        registry.register(
            name="risk_calibrator",
            feature_list=list(feature_list),
            hyperparams={"method": method, "n_train": n},
            seed=42,
            metrics={"brier_score": float(brier)},
            file_path=str(target),
            calibrated=True,
            training_data_hash=data_hash,
        )
    except Exception as exc:
        logger.warning("calibrator registry update failed: %s", exc)
    return {
        "method": method,
        "brier_score": float(brier),
        "training_data_hash": data_hash,
        "file_path": str(target),
        "calibrated": True,
    }


def _load_artefact(path: Path) -> dict[str, Any] | None:
    """Load a persisted artefact, or None when missing/corrupt."""
    if not path.exists():
        return None
    try:
        artefact = joblib.load(path)
    except Exception:
        return None
    return artefact if isinstance(artefact, dict) else None


def calibrate_scores(
    scores: list[float] | np.ndarray,
    feature_list: list[str],
    calibrator_path: str | Path = CALIBRATOR_PATH,
) -> dict[str, Any]:
    """Map raw 0-1 scores to 0-100 supervisory risk.

    Returns calibrated_scores, calibrated flag and method. Missing artefact
    or feature-list drift logs ERROR and returns raw*100 with
    calibrated:false (never crashes, never silently calibrated).
    """
    raw = [float(max(0.0, min(1.0, s))) for s in list(scores)]
    artefact = _load_artefact(Path(calibrator_path))
    if artefact is None:
        return {
            "calibrated_scores": [float(v * 100.0) for v in raw],
            "calibrated": False,
            "method": "none",
            "reason": "no calibrator artefact",
        }
    trained_features = [str(f) for f in artefact.get("feature_list", [])]
    if trained_features != [str(f) for f in feature_list]:
        logger.error(
            "calibrator feature drift: trained=%s inference=%s",
            trained_features,
            list(feature_list),
        )
        return {
            "calibrated_scores": [float(v * 100.0) for v in raw],
            "calibrated": False,
            "method": str(artefact.get("method", "unknown")),
            "reason": "feature_list mismatch",
        }
    model = artefact.get("model")
    if model is None:
        logger.error("calibrator artefact has no model")
        return {
            "calibrated_scores": [float(v * 100.0) for v in raw],
            "calibrated": False,
            "method": str(artefact.get("method", "unknown")),
            "reason": "missing model in artefact",
        }
    try:
        x_list: list[float] = [float(v) for v in raw]
        if artefact.get("method") == "isotonic":
            probs_list: list[float] = [float(v) for v in model.predict(x_list)]
            probs = np.asarray(probs_list, dtype=float)
        else:
            matrix = np.asarray([[v] for v in x_list], dtype=float)
            raw_proba: Any = model.predict_proba(matrix)
            col: list[float] = [float(v) for v in list(raw_proba[:, 1])]
            probs = np.asarray(col, dtype=float)
    except Exception as exc:
        logger.error("calibration inference failed: %s", exc)
        return {
            "calibrated_scores": [float(v * 100.0) for v in raw],
            "calibrated": False,
            "method": str(artefact.get("method", "unknown")),
            "reason": str(exc)[:200],
        }
    raw_probs: list[Any] = list(probs)
    scores_out: list[float] = [float(item) for item in raw_probs]
    return {
        "calibrated_scores": [float(max(0.0, min(100.0, p * 100.0))) for p in scores_out],
        "calibrated": True,
        "method": str(artefact.get("method", "unknown")),
        "brier_score": float(artefact.get("brier_score", 0.0)),
    }
