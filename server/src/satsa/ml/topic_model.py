"""Lightweight topic mining over investigation notes.

FULL pipeline (when umap-learn + hdbscan installed):
  UMAP(n_components=5) -> HDBSCAN -> c-TF-IDF topic labels.
LITE fallback (always available):
  NMF(n_components=10, random_state=seed) over TF-IDF.

Deterministic given seed. Flags topics concentrated in one entity/analyst.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def _thresholds(config_dir: str | Path = "configs") -> dict[str, Any]:
    """Load thresholds with Phase 3 defaults for missing keys (never crashes)."""
    defaults: dict[str, Any] = {
        "topic_concentration_threshold": 0.60,
        "topic_min_notes": 5,
    }
    path = Path(config_dir) / "thresholds.yaml"
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            for key, val in data.items():
                defaults[key] = val
        except Exception:
            pass
    return defaults


def _tokens(text: str) -> list[str]:
    """Tokenise a note for c-TF-IDF labelling."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _ctfidf_labels(
    clusters: np.ndarray, texts: list[str], top_k: int = 8
) -> dict[int, list[str]]:
    """Compute c-TF-IDF top terms per cluster (deterministic)."""
    from collections import Counter

    from sklearn.feature_extraction.text import TfidfVectorizer

    labels: dict[int, list[str]] = {}
    for topic in sorted(set(int(c) for c in clusters if int(c) >= 0)):
        docs = [texts[i] for i in range(len(texts)) if int(clusters[i]) == topic]
        if not docs:
            labels[topic] = []
            continue
        try:
            vec = TfidfVectorizer(token_pattern=r"[a-z0-9]+", max_features=500)
            matrix = vec.fit_transform(docs + [" ".join(texts)])
            terms = vec.get_feature_names_out().tolist()
            centroid = np.asarray(matrix[:-1].mean(axis=0)).ravel()
            top = np.argsort(-centroid)[:top_k]
            labels[topic] = [terms[i] for i in top if centroid[i] > 0]
        except ValueError:
            counts: Counter[str] = Counter()
            for doc in docs:
                counts.update(_tokens(doc))
            labels[topic] = [w for w, _ in counts.most_common(top_k)]
    return labels


def _lite_nmf(texts: list[str], seed: int, n_components: int = 10) -> np.ndarray:
    """Assign clusters via NMF (deterministic). Returns topic index per doc."""
    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import TfidfVectorizer

    cleaned = [t if t.strip() else "empty note placeholder" for t in texts]
    if len(cleaned) < 2:
        return np.zeros(len(cleaned), dtype=int)
    vec = TfidfVectorizer(token_pattern=r"[a-z0-9]+", max_features=2000, min_df=1)
    try:
        matrix = vec.fit_transform(cleaned)
    except ValueError:
        return np.zeros(len(cleaned), dtype=int)
    k = int(max(2, min(n_components, len(cleaned) - 1, matrix.shape[1])))
    model = NMF(n_components=k, random_state=seed, init="nndsvda", max_iter=300)
    doc_topics = model.fit_transform(matrix)
    return np.asarray(np.argmax(doc_topics, axis=1), dtype=int)


def discover_topics(
    notes: pd.DataFrame,
    seed: int = 42,
    config_dir: str | Path = "configs",
    text_col: str = "notes",
) -> dict[str, Any]:
    """Mine topics over investigation notes.

    notes columns used when present: text_col, note_id/investigation_id,
    entity_id, analyst_id. Returns topics list + backend name + concentration
    flags. Deterministic for same input + seed.
    """
    limits = _thresholds(config_dir)
    concentration_threshold = float(limits.get("topic_concentration_threshold", 0.60))
    texts: list[str] = []
    note_ids: list[str] = []
    entity_ids: list[str] = []
    analyst_ids: list[str] = []
    if notes.empty:
        return {"topics": [], "backend": "lite", "topic_count": 0}
    for idx, row in notes.reset_index(drop=True).iterrows():
        texts.append(str(row.get(text_col, row.get("notes", "")) or ""))
        note_ids.append(str(row.get("note_id", row.get("investigation_id", f"n{idx}"))))
        entity_ids.append(str(row.get("entity_id", "unknown")))
        analyst_ids.append(str(row.get("analyst_id", "unknown")))
    backend = "lite"
    try:
        from hdbscan import HDBSCAN
        from umap import UMAP

        from satsa.ml.embeddings import encode as _encode

        matrix = _encode(texts)
        reducer = UMAP(n_components=5, random_state=seed)
        reduced = reducer.fit_transform(matrix)
        clusters: np.ndarray = np.asarray(
            HDBSCAN(min_cluster_size=5).fit_predict(reduced), dtype=int
        )
        backend = "full"
    except Exception:
        clusters = _lite_nmf(texts, seed)
        backend = "lite"
    labels = _ctfidf_labels(clusters, texts)
    topics: list[dict[str, Any]] = []
    for topic in sorted(set(int(c) for c in clusters if int(c) >= 0)):
        members = [i for i in range(len(texts)) if int(clusters[i]) == topic]
        ent_counts: dict[str, int] = {}
        ana_counts: dict[str, int] = {}
        for i in members:
            ent_counts[entity_ids[i]] = ent_counts.get(entity_ids[i], 0) + 1
            ana_counts[analyst_ids[i]] = ana_counts.get(analyst_ids[i], 0) + 1
        size = len(members)
        top_ent = max(ent_counts.values()) / max(1, size) if ent_counts else 0.0
        top_ana = max(ana_counts.values()) / max(1, size) if ana_counts else 0.0
        concentration = float(max(top_ent, top_ana))
        topics.append(
            {
                "topic_id": int(topic),
                "size": int(size),
                "top_terms": labels.get(topic, []),
                "example_note_ids": [note_ids[i] for i in members[:5]],
                "entity_distribution": dict(ent_counts),
                "analyst_distribution": dict(ana_counts),
                "concentration_ratio": float(concentration),
                "concentrated": bool(concentration > concentration_threshold),
            }
        )
    topics.sort(key=lambda t: t["size"], reverse=True)
    return {"topics": topics, "backend": backend, "topic_count": len(topics)}
