"""Phase 3 local LLM tests (new file, Phase 0+1+2 untouched)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest


def test_raises_when_no_backend(tmp_path: Path) -> None:
    """No GGUF and no Ollama raises LLMUnavailable."""
    from satsa.ai.local_llm import generate
    from satsa.errors import LLMUnavailable

    config = {
        "model_path": str(tmp_path / "missing.gguf"),
        "timeout_seconds": 2,
        "max_tokens": 32,
        "temperature": 0.0,
        "top_p": 1.0,
        "seed": 42,
    }
    with pytest.raises(LLMUnavailable):
        generate("hello", config)


def test_never_calls_non_localhost(monkeypatch: Any, tmp_path: Path) -> None:
    """Socket connections, if any, target loopback only."""
    import socket

    from satsa.ai import local_llm
    from satsa.errors import LLMUnavailable

    hosts: list[str] = []

    def _spy(self: object, address: object, *args: object, **kwargs: object) -> object:
        host = address[0] if isinstance(address, tuple) else str(address)
        hosts.append(str(host))
        raise OSError("blocked in test")

    monkeypatch.setattr(socket.socket, "connect", _spy)
    monkeypatch.setattr(local_llm, "_ollama_available", lambda *a: False)
    config = {"model_path": str(tmp_path / "missing.gguf"), "timeout_seconds": 1}
    with pytest.raises(LLMUnavailable):
        local_llm.generate("hello", config)
    assert all(h in ("127.0.0.1", "localhost", "::1") for h in hosts)


def test_timeout_triggers_unavailable() -> None:
    """Slow backend triggers LLMUnavailable via timeout wrapper."""
    import time

    from satsa.ai.local_llm import _run_with_timeout
    from satsa.errors import LLMUnavailable

    def _slow() -> str:
        time.sleep(5)
        return "late"

    with pytest.raises(LLMUnavailable):
        _run_with_timeout(_slow, 0.2)
