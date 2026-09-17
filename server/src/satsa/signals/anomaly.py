"""Multivariate anomaly ensemble (5 PyOD models + robust Mahalanobis)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.covariance import MinCovDet
from sklearn.preprocessing import StandardScaler


def _pyod_scores(matrix: np.ndarray, seed: int = 42) -> dict[str, np.ndarray]:
    """Fit IsolationForest, ECOD, COPOD, HBOS and LOF; return raw outlier scores.

    Each model is fault-tolerant: a model that cannot fit degenerate input
    contributes a zero vector so the ensemble never crashes.
    """
    from pyod.models.copod import COPOD
    from pyod.models.ecod import ECOD
    from pyod.models.hbos import HBOS
    from pyod.models.iforest import IForest
    from pyod.models.lof import LOF

    zeros = np.zeros(matrix.shape[0], dtype=float)
    scores: dict[str, np.ndarray] = {}
    try:
        scores["iforest"] = np.asarray(IForest(random_state=seed).fit(matrix).decision_scores_)
    except Exception:
        scores["iforest"] = zeros.copy()
    try:
        scores["ecod"] = np.asarray(ECOD().fit(matrix).decision_scores_)
    except Exception:
        scores["ecod"] = zeros.copy()
    try:
        scores["copod"] = np.asarray(COPOD().fit(matrix).decision_scores_)
    except Exception:
        scores["copod"] = zeros.copy()
    try:
        scores["hbos"] = np.asarray(HBOS().fit(matrix).decision_scores_)
    except Exception:
        scores["hbos"] = zeros.copy()
    try:
        raw_lof: np.ndarray = np.asarray(LOF().fit_predict(matrix), dtype=float)
        scores["lof"] = np.asarray(-raw_lof, dtype=float)
    except Exception:
        scores["lof"] = zeros.copy()
    return scores


def _mahalanobis_scores(matrix: np.ndarray) -> np.ndarray:
    """Robust Mahalanobis distances (MCD), falling back to median distance."""
    try:
        scaler = StandardScaler()
        scaled = scaler.fit_transform(matrix)
        fitted = MinCovDet(random_state=42).fit(scaled)
        distances: np.ndarray = np.asarray(fitted.dist_, dtype=float)
        return distances
    except Exception:
        median = np.median(matrix, axis=0)
        norms: np.ndarray = np.asarray(np.linalg.norm(matrix - median, axis=1), dtype=float)
        return norms


def _ranks(scores: np.ndarray) -> np.ndarray:
    """Return 0-1 ranks (1 = most anomalous) for a score vector."""
    order = np.argsort(np.argsort(scores))
    if len(scores) <= 1:
        return np.zeros(len(scores), dtype=float)
    ranked: np.ndarray = order.astype(float) / float(len(scores) - 1)
    return ranked


def _minmax(values: np.ndarray) -> np.ndarray:
    """Min-max normalise to [0, 1]; constant vectors become zeros."""
    lo, hi = float(np.min(values)), float(np.max(values))
    if hi <= lo:
        return np.zeros(len(values), dtype=float)
    return np.asarray((values - lo) / (hi - lo), dtype=float)


def ensemble_scores(
    feature_frame: pd.DataFrame, seed: int = 42
) -> dict[str, Any]:
    """Run the full ensemble; return per-entity scores, ranks and model detail.

    Requires >= 2 entities (PyOD constraint); raises ValueError otherwise so
    callers fall back to peer benchmarking only.
    """
    if len(feature_frame) < 2:
        raise ValueError("anomaly ensemble requires at least 2 entities")
    numeric = feature_frame.select_dtypes(include=[np.number]).fillna(0.0)
    variances = numeric.var()
    kept = [c for c in numeric.columns if float(variances[c]) > 0.0]
    if len(kept) < 2:
        raise ValueError("anomaly ensemble requires at least 2 varying features")
    numeric = numeric[kept]
    cleaned: np.ndarray = np.nan_to_num(
        numeric.to_numpy(dtype=float), nan=0.0, posinf=0.0, neginf=0.0
    )
    matrix: np.ndarray = np.asarray(cleaned, dtype=float)
    model_scores = _pyod_scores(matrix, seed)
    model_scores["mahalanobis"] = _mahalanobis_scores(matrix)
    stacked = np.vstack([_ranks(_minmax(s)) for s in model_scores.values()])
    rank_matrix: np.ndarray = np.asarray(stacked, dtype=float)
    means: np.ndarray = np.asarray(rank_matrix.mean(axis=0), dtype=float)
    ensemble_rank = means
    order = np.argsort(-means)
    ranks = np.empty_like(order)
    ranks[order] = np.arange(1, len(order) + 1)
    return {
        "anomaly_score": [float(v) for v in ensemble_rank],
        "anomaly_rank": [int(v) for v in ranks],
        "model_scores": {k: [float(v) for v in vals] for k, vals in model_scores.items()},
        "columns": numeric.columns.tolist(),
    }


def feature_contributions(
    feature_frame: pd.DataFrame, seed: int = 42
) -> list[dict[str, float]]:
    """Ablation contributions: score drop when each feature takes its median.

    Contribution = original_score - ablated_score per entity per feature.
    """
    base = ensemble_scores(feature_frame, seed)
    numeric = feature_frame.select_dtypes(include=[np.number]).fillna(0.0)
    medians = numeric.median()
    contributions: list[dict[str, float]] = [{} for _ in range(len(numeric))]
    for column in numeric.columns:
        ablated = numeric.copy()
        ablated[column] = float(medians[column])
        try:
            alt = ensemble_scores(
                pd.DataFrame(ablated.values, columns=numeric.columns, index=numeric.index), seed
            )
        except Exception:
            continue
        for i, (orig, new) in enumerate(zip(base["anomaly_score"], alt["anomaly_score"])):
            contributions[i][str(column)] = float(orig - new)
    return contributions


def top_contributors(contributions: dict[str, float], top_n: int = 5) -> list[str]:
    """Return the top-N contributing feature names by absolute contribution."""
    ranked = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)
    return [name for name, _ in ranked[:top_n]]
