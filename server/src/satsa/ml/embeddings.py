"""Embedding wrapper: FULL local sentence-transformers or LITE TF-IDF/SVD.

Never calls the network under any code path. FULL backend loads with
local_files_only=True and blocks non-loopback sockets during encode.
Missing model path logs WARNING and falls back to LITE.
"""

from __future__ import annotations

import hashlib
import warnings
from pathlib import Path
from typing import Any

import numpy as np

_EMBEDDING_TRUNCATE = 4096
_SVD_COMPONENTS = 128
_BATCH = 64
_CACHE_DIRNAME = ".cache"


def _model_hash(model_dir: Path) -> str:
    """Return a stable hash for the model directory path."""
    return hashlib.sha256(str(model_dir).encode("utf-8", errors="replace")).hexdigest()[:16]


def _text_hash(text: str) -> str:
    """Return the SHA-256 hash of one text."""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _cache_key(model_hash: str, text: str) -> str:
    """Return the disk-cache key for one (model, text) pair."""
    return f"{model_hash}_{_text_hash(text)}"


def _lite_encode(texts: list[str]) -> np.ndarray:
    """Encode with TF-IDF (word + char) and TruncatedSVD(128), deterministic."""
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer

    cleaned = [t[:_EMBEDDING_TRUNCATE] if t.strip() else "empty note placeholder" for t in texts]
    if len(cleaned) == 0:
        return np.zeros((0, _SVD_COMPONENTS), dtype=float)
    if len(cleaned) == 1:
        # Single row: deterministic hash-projection fallback (no fit possible).
        vec = np.zeros((_SVD_COMPONENTS,), dtype=float)
        digest = hashlib.sha256(cleaned[0].encode("utf-8", errors="replace")).digest()
        for i in range(_SVD_COMPONENTS):
            vec[i] = float(digest[i % len(digest)]) / 255.0
        return vec.reshape(1, -1)
    word = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    char = TfidfVectorizer(analyzer="char", ngram_range=(2, 3), sublinear_tf=True, min_df=1)
    try:
        word_matrix = word.fit_transform(cleaned)
        char_matrix = char.fit_transform(cleaned)
    except ValueError:
        return np.zeros((len(cleaned), _SVD_COMPONENTS), dtype=float)
    from scipy.sparse import hstack

    combined = hstack([word_matrix, char_matrix])
    n_comp = int(min(_SVD_COMPONENTS, max(1, combined.shape[0] - 1), combined.shape[1]))
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    fitted: np.ndarray = np.asarray(svd.fit_transform(combined), dtype=float)
    if n_comp < _SVD_COMPONENTS:
        padded = np.zeros((fitted.shape[0], _SVD_COMPONENTS), dtype=float)
        padded[:, :n_comp] = fitted
        return padded
    return fitted


def _full_encode(
    texts: list[str], model_dir: Path, cache_dir: Path
) -> np.ndarray:
    """Encode with a local sentence-transformers model (no network).

    Loads with local_files_only=True, processes in chunks of 64, caches
    embeddings on disk keyed by (model_hash, text_hash). Blocks
    non-loopback socket connections for the duration of the call.
    """
    import io
    from contextlib import redirect_stderr

    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        raise RuntimeError("sentence-transformers not installed") from exc
    if not model_dir.exists():
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
            model = SentenceTransformer(str(model_dir), local_files_only=True)
        model_hash = _model_hash(model_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        vectors: list[np.ndarray] = []
        missing_idx: list[int] = []
        missing_texts: list[str] = []
        for i, text in enumerate(texts):
            key = _cache_key(model_hash, text[:_EMBEDDING_TRUNCATE])
            cached = cache_dir / f"{key}.npy"
            if cached.exists():
                try:
                    vectors.append(np.load(str(cached)))
                    continue
                except Exception:
                    pass
            vectors.append(np.array([]))
            missing_idx.append(i)
            missing_texts.append(text[:_EMBEDDING_TRUNCATE])
        for chunk_start in range(0, len(missing_texts), _BATCH):
            chunk = missing_texts[chunk_start : chunk_start + _BATCH]
            encoded = np.asarray(model.encode(chunk), dtype=float)
            for offset, vec in enumerate(encoded):
                global_i = missing_idx[chunk_start + offset]
                arr = np.asarray(vec, dtype=float)
                vectors[global_i] = arr
                key = _cache_key(model_hash, texts[global_i][: _EMBEDDING_TRUNCATE])
                try:
                    np.save(str(cache_dir / f"{key}.npy"), arr)
                except Exception:
                    pass
    finally:
        _socket.socket.connect = real_create  # type: ignore[method-assign]
    return np.vstack(vectors)


def encode(
    texts: list[str],
    model_dir: str | Path = "models/embeddings",
    cache_dir: str | Path = "models/embeddings/.cache",
) -> np.ndarray:
    """Encode texts to embeddings, FULL when available else LITE fallback.

    Never calls the network. Missing model path logs WARNING and uses LITE.
    Processes in chunks of 64 to avoid OOM. Deterministic for same input.
    """
    cleaned = ["" if t is None else str(t) for t in texts]
    model_path = Path(model_dir)
    # Chunk to avoid OOM; results concatenated in order (deterministic).
    chunks = [cleaned[i : i + _BATCH] for i in range(0, len(cleaned), _BATCH)] or [[]]
    parts: list[np.ndarray] = []
    for chunk in chunks:
        if not chunk:
            continue
        try:
            if not model_path.exists() or not any(model_path.iterdir()):
                raise RuntimeError(f"embedding model missing at {model_dir}")
            parts.append(_full_encode(chunk, model_path, Path(cache_dir)))
        except Exception as exc:
            warnings.warn(
                f"FULL embedding backend unavailable, using LITE: {exc}",
                UserWarning,
                stacklevel=2,
            )
            parts.append(_lite_encode(chunk))
    if not parts:
        return np.zeros((0, _SVD_COMPONENTS), dtype=float)
    return np.vstack(parts)
