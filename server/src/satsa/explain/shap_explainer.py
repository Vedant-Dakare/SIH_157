"""Unified feature contributions: SHAP when available, ablation otherwise.

Guard: n_features * n_entities above the size limit samples entities and
sets approximate=True (INFO log). SHAP computation never blocks a run:
any failure falls back to the Phase-2-style median ablation.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_SIZE_LIMIT = 25000


class FeatureContribution(BaseModel):
    """One feature's contribution to one entity's finding."""

    finding_id: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    feature_name: str = Field(min_length=1)
    contribution: float = 0.0
    direction: str = Field(default="increases_risk")
    method: str = Field(default="ablation")
    approximate: bool = False


def _as_frame(features: pd.DataFrame | dict[str, dict[str, float]]) -> pd.DataFrame:
    """Coerce entity features to a numeric DataFrame (entities as index)."""
    if isinstance(features, pd.DataFrame):
        return features.select_dtypes(include=[np.number]).fillna(0.0)
    frame = pd.DataFrame.from_dict(features, orient="index")
    return frame.select_dtypes(include=[np.number]).fillna(0.0)


def _fit_isolation_forest(matrix: np.ndarray, seed: int = 42) -> Any:
    """Fit an IsolationForest anomaly model (deterministic)."""
    from sklearn.ensemble import IsolationForest

    model = IsolationForest(random_state=seed)
    model.fit(matrix)
    return model


def _shap_contributions(
    model: Any, matrix: np.ndarray, columns: list[str]
) -> np.ndarray | None:
    """SHAP TreeExplainer contributions, or None when shap is unavailable."""
    try:
        import shap
    except Exception:
        return None
    try:
        explainer = shap.TreeExplainer(model)
        values: Any = explainer.shap_values(matrix)
        table: np.ndarray = np.asarray(values, dtype=float)
        return table
    except Exception as exc:
        logger.info("SHAP explainer failed, falling back to ablation: %s", exc)
        return None


def _ablation_contributions(
    model: Any, matrix: np.ndarray, medians: np.ndarray
) -> np.ndarray:
    """Median-ablation contributions: score drop per feature (Phase-2 method)."""
    base_scores: Any = None
    try:
        base_scores = model.score_samples(matrix)
    except Exception:
        base_scores = None
    base: list[float] = (
        [float(v) for v in list(base_scores)]
        if base_scores is not None
        else [0.0] * matrix.shape[0]
    )
    out: list[list[float]] = [[0.0] * matrix.shape[1] for _ in range(matrix.shape[0])]
    med_list: list[float] = [float(v) for v in list(medians)]
    for j in range(matrix.shape[1]):
        ablated = matrix.copy()
        col: Any = ablated[:, j]
        col[:] = med_list[j]
        try:
            alt_scores: Any = model.score_samples(ablated)
            alt: list[float] = [float(v) for v in list(alt_scores)]
        except Exception:
            alt = list(base)
        for i in range(matrix.shape[0]):
            out[i][j] = base[i] - alt[i]
    return np.asarray(out, dtype=float)


def explain_anomaly(
    features: pd.DataFrame | dict[str, dict[str, float]],
    finding_id: str,
    entity_id: str = "",
    seed: int = 42,
    size_limit: int = DEFAULT_SIZE_LIMIT,
) -> list[FeatureContribution]:
    """Explain one entity's anomaly finding with unified contributions."""
    frame = _as_frame(features)
    if frame.empty:
        return []
    approximate = False
    if frame.shape[0] * frame.shape[1] > size_limit:
        logger.info(
            "SHAP input %dx%d exceeds limit %d; sampling entities",
            frame.shape[0],
            frame.shape[1],
            size_limit,
        )
        frame = frame.sample(n=max(1, size_limit // max(1, frame.shape[1])), random_state=seed)
        approximate = True
    matrix = np.asarray(frame.to_numpy(dtype=float), dtype=float)
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    columns = [str(c) for c in frame.columns.tolist()]
    try:
        model = _fit_isolation_forest(matrix, seed)
    except Exception as exc:
        logger.info("anomaly model fit failed, cannot explain: %s", exc)
        return []
    shap_values = _shap_contributions(model, matrix, columns)
    if shap_values is not None and shap_values.shape == matrix.shape:
        method = "shap"
        table = shap_values
    else:
        method = "ablation"
        medians = np.median(matrix, axis=0)
        table = _ablation_contributions(model, matrix, medians)
    entities = [str(i) for i in frame.index.tolist()]
    target = str(entity_id) if entity_id else (entities[0] if entities else "")
    try:
        row = entities.index(target)
    except ValueError:
        row = 0
    contributions: list[FeatureContribution] = []
    for j, name in enumerate(columns):
        value = float(table[row, j])
        contributions.append(
            FeatureContribution(
                finding_id=finding_id,
                entity_id=target,
                feature_name=name,
                contribution=value,
                direction="increases_risk" if value >= 0 else "decreases_risk",
                method=method,
                approximate=bool(approximate),
            )
        )
    return contributions
