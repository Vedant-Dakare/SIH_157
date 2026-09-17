"""Phase 3 embeddings tests (new file, Phase 0+1+2 untouched)."""

from __future__ import annotations

import numpy as np


def test_encode_deterministic() -> None:
    """Same input yields identical output."""
    from satsa.ml.embeddings import encode

    texts = ["Investigated alert, closed as benign.", "Escalated critical case to T2."]
    first = encode(texts, model_dir="models/embeddings-missing-xyz")
    second = encode(texts, model_dir="models/embeddings-missing-xyz")
    assert isinstance(first, np.ndarray)
    assert first.shape == second.shape
    assert np.allclose(first, second)


def test_missing_model_falls_back_with_warning() -> None:
    """Missing path warns and returns LITE vectors."""
    import warnings

    from satsa.ml.embeddings import encode

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        vectors = encode(["note one", "note two"], model_dir="models/does-not-exist-xyz")
    assert any("LITE" in str(w.message) for w in caught)
    assert vectors.shape[0] == 2
    assert vectors.shape[1] == 128


def test_no_network_calls_during_encode(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """No requests/urllib/socket network use during encode."""
    import socket

    import satsa.ml.embeddings as emb

    calls: list[str] = []
    real_connect = socket.socket.connect

    def _spy(self: object, address: object, *args: object, **kwargs: object) -> object:
        calls.append(str(address))
        return real_connect(self, address, *args, **kwargs)  # type: ignore[arg-type, misc]

    monkeypatch.setattr(socket.socket, "connect", _spy)
    try:
        import requests  # type: ignore[import-not-found]

        def _blocked(*a: object, **k: object) -> object:
            raise RuntimeError("net")

        monkeypatch.setattr(requests, "get", _blocked)
    except Exception:
        pass
    emb.encode(["alpha note", "beta note"], model_dir="models/does-not-exist-xyz")
    assert calls == []
