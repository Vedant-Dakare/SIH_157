"""Text features: LITE TF-IDF/SVD plus FULL local-embedding backends."""

from __future__ import annotations

import hashlib
import re
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_EMBEDDING_TRUNCATE = 4096
_SVD_COMPONENTS = 128

_PLACEHOLDER_RE = re.compile(
    r"^\s*(n/?a|none|-|done|checked|see above|as above|ok|tbd)\s*\.?\s*$"
    r"|\b(see above|as above)\b",
    re.IGNORECASE,
)


def _clean_notes(notes: pd.Series) -> list[str]:
    """Return notes as strings, truncating to 4096 chars for embedding use."""
    cleaned: list[str] = []
    for note in notes.tolist():
        text = "" if note is None else str(note)
        cleaned.append(text[:_EMBEDDING_TRUNCATE])
    return cleaned


def _pairwise_cosine(matrix: Any) -> np.ndarray:
    """Return the pairwise cosine similarity matrix for an embedding matrix."""
    sims: np.ndarray = np.asarray(cosine_similarity(matrix), dtype=float)
    cleaned: np.ndarray = np.nan_to_num(sims, nan=0.0, posinf=1.0, neginf=0.0)
    return cleaned


def lite_similarity(notes: list[str]) -> dict[str, Any]:
    """Compute TF-IDF (word + char 2-3 grams) and SVD(128) similarity.

    Returns mean pairwise cosine, the full matrix shape, and backend name.
    Scores are length-normalised by TF-IDF sublinear scaling by construction.
    """
    texts = [t if t.strip() else "empty note placeholder" for t in notes]
    if len(texts) < 2:
        return {"mean_pairwise": 0.0, "matrix_shape": (len(texts), len(texts)), "backend": "lite"}
    vectorizer = TfidfVectorizer(
        analyzer="word", ngram_range=(1, 2), sublinear_tf=True, min_df=1
    )
    char_vectorizer = TfidfVectorizer(
        analyzer="char", ngram_range=(2, 3), sublinear_tf=True, min_df=1
    )
    try:
        word_matrix = vectorizer.fit_transform(texts)
        char_matrix = char_vectorizer.fit_transform(texts)
    except ValueError:
        return {"mean_pairwise": 0.0, "matrix_shape": (len(texts), len(texts)), "backend": "lite"}
    from scipy.sparse import hstack

    combined = hstack([word_matrix, char_matrix])
    n_components = int(min(_SVD_COMPONENTS, max(1, combined.shape[0] - 1), combined.shape[1]))
    reduced = TruncatedSVD(n_components=n_components, random_state=42).fit_transform(combined)
    sims = _pairwise_cosine(reduced)
    n = sims.shape[0]
    off_diag = [float(sims[i, j]) for i in range(n) for j in range(n) if i != j]
    mean_pairwise = float(sum(off_diag) / max(1, len(off_diag)))
    return {
        "mean_pairwise": float(max(0.0, min(1.0, mean_pairwise))),
        "matrix_shape": (n, n),
        "backend": "lite",
    }


def _model_cache_key(model_hash: str, text: str) -> str:
    """Return the disk-cache key for one (model, text) embedding."""
    text_hash = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    return f"{model_hash}_{text_hash}"


def full_similarity(
    notes: list[str],
    model_dir: str | Path = "models/embeddings",
    cache_dir: str | Path = "models/embeddings/.cache",
) -> dict[str, Any]:
    """Encode notes with a local sentence-transformers model (no network).

    Loads with local_files_only=True, batch encodes, and caches embeddings on
    disk keyed by (model_hash, text_hash). Raises if the model is unavailable
    so callers can fall back to the LITE backend.
    """
    import io
    from contextlib import redirect_stderr

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        raise RuntimeError("sentence-transformers not installed") from exc
    model_path = Path(model_dir)
    if not model_path.exists():
        raise RuntimeError(f"embedding model missing at {model_dir}")
    import socket as _socket

    real_create = _socket.socket.connect

    def _blocked_connect(sock: Any, address: Any, *args: Any, **kwargs: Any) -> Any:
        """Block non-loopback connections during local encoding."""
        host = address[0] if isinstance(address, tuple) else str(address)
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise RuntimeError(f"network call blocked during local encode: {host}")
        return real_create(sock, address, *args, **kwargs)

    _socket.socket.connect = _blocked_connect  # type: ignore[method-assign]
    try:
        with redirect_stderr(io.StringIO()):
            model = SentenceTransformer(str(model_path), local_files_only=True)
        try:
            model_hash = hashlib.sha256(str(model_path).encode()).hexdigest()[:16]
        except Exception:
            model_hash = "local"
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        vectors: list[np.ndarray] = []
        for text in notes:
            key = _model_cache_key(model_hash, text[:_EMBEDDING_TRUNCATE])
            cached = Path(cache_dir) / f"{key}.npy"
            if cached.exists():
                vectors.append(np.load(str(cached)))
                continue
            vec = np.asarray(model.encode([text[:_EMBEDDING_TRUNCATE]])[0], dtype=float)
            np.save(str(cached), vec)
            vectors.append(vec)
    finally:
        _socket.socket.connect = real_create  # type: ignore[method-assign]
    if len(vectors) < 2:
        return {"mean_pairwise": 0.0, "backend": "full"}
    matrix = np.vstack(vectors)
    sims = _pairwise_cosine(matrix)
    n = sims.shape[0]
    off_diag = [float(sims[i, j]) for i in range(n) for j in range(n) if i != j]
    return {"mean_pairwise": float(sum(off_diag) / max(1, len(off_diag))), "backend": "full"}


def vocabulary_richness(notes: list[str]) -> float:
    """Return length-normalised type-token ratio averaged over notes."""
    scores: list[float] = []
    for text in notes:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            continue
        ratio = len(set(tokens)) / max(1, len(tokens))
        length_norm = min(1.0, len(tokens) / 50.0) or 1.0
        scores.append(float(ratio * (0.5 + 0.5 * length_norm)))
    if not scores:
        return 0.0
    return float(sum(scores) / len(scores))


def copy_paste_ratio(notes: list[str], threshold: float = 0.9) -> float:
    """Return the fraction of near-duplicate note pairs (MinHash-style shingles)."""
    if len(notes) < 2:
        return 0.0

    def _shingles(text: str) -> set[str]:
        """Return word-3-shingles for a note."""
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        return {" ".join(tokens[i : i + 3]) for i in range(max(0, len(tokens) - 2))}

    sets = [_shingles(t) for t in notes]
    hits = 0
    total = 0
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            total += 1
            union = sets[i] | sets[j]
            if not union:
                continue
            if len(sets[i] & sets[j]) / len(union) >= threshold:
                hits += 1
    return float(hits / max(1, total))


def placeholder_ratio(notes: list[str]) -> float:
    """Return the fraction of placeholder/blank notes (length-normalised)."""
    if not notes:
        return 0.0
    hits = sum(1 for t in notes if not t.strip() or _PLACEHOLDER_RE.search(t))
    return float(hits / max(1, len(notes)))


def text_features(
    investigations: pd.DataFrame, backend: str = "lite", model_dir: str | Path = "models/embeddings"
) -> dict[str, Any]:
    """Compute template similarity, richness, copy-paste and placeholder scores."""
    notes: list[str] = []
    if "notes" in investigations.columns:
        notes = _clean_notes(investigations["notes"])
    per_analyst: dict[str, float] = {}
    if "analyst_id" in investigations.columns and len(investigations):
        frame = pd.DataFrame({"note": notes, "analyst": investigations["analyst_id"].tolist()})
        for analyst, group in frame.groupby("analyst", dropna=False):
            if len(group) >= 2:
                try:
                    if backend == "full":
                        sims = full_similarity(group["note"].tolist(), model_dir)
                        per_analyst[str(analyst)] = float(sims["mean_pairwise"])
                    else:
                        lite = lite_similarity(group["note"].tolist())
                        per_analyst[str(analyst)] = float(lite["mean_pairwise"])
                except Exception as exc:
                    warnings.warn(f"text backend failed: {exc}", UserWarning, stacklevel=2)
                    per_analyst[str(analyst)] = 0.0
    entity_score = 0.0
    used_backend = backend
    if len(notes) >= 2:
        if backend == "full":
            try:
                entity_score = float(full_similarity(notes, model_dir)["mean_pairwise"])
            except Exception as exc:
                warnings.warn(f"FULL backend failed, using LITE: {exc}", UserWarning, stacklevel=2)
                entity_score = float(lite_similarity(notes)["mean_pairwise"])
                used_backend = "lite"
        else:
            entity_score = float(lite_similarity(notes)["mean_pairwise"])
            used_backend = "lite"
    return {
        "template_similarity_score": float(max(0.0, min(1.0, entity_score))),
        "template_by_analyst": {
            k: float(max(0.0, min(1.0, v))) for k, v in per_analyst.items()
        },
        "vocabulary_richness": float(vocabulary_richness(notes)),
        "copy_paste_ratio": float(copy_paste_ratio(notes)),
        "placeholder_ratio": float(placeholder_ratio(notes)),
        "backend": used_backend,
        "note_count": int(len(notes)),
    }
