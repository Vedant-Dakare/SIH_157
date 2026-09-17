"""Offline LLM client: llama-cpp GGUF first, Ollama localhost second.

Never calls any non-localhost address. Ollama URL is hardcoded to
127.0.0.1 and never taken from user input. Missing backends raise
LLMUnavailable. Slow responses beyond timeout_seconds raise
LLMUnavailable. Deterministic via fixed seed.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml

from satsa.errors import LLMUnavailable

OLLAMA_URL = "http://127.0.0.1:11434"
_ALLOWED_HOSTS = {"127.0.0.1", "localhost", "::1"}

_DEFAULTS: dict[str, Any] = {
    "model_path": "models/llm/model.gguf",
    "n_ctx": 4096,
    "n_threads": 4,
    "temperature": 0.1,
    "top_p": 0.9,
    "max_tokens": 512,
    "seed": 42,
    "timeout_seconds": 30,
}


def load_llm_config(config_path: str | Path = "configs/llm.yaml") -> dict[str, Any]:
    """Load llm.yaml over defaults (never crashes on absence)."""
    merged = dict(_DEFAULTS)
    merged["enabled"] = False
    path = Path(config_path)
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
            for key, val in data.items():
                merged[key] = val
        except Exception:
            pass
    return merged


def _assert_localhost(url: str) -> str:
    """Validate a URL points at loopback; raise LLMUnavailable otherwise."""
    host = urllib.parse.urlparse(url).hostname or ""
    if host.lower() not in _ALLOWED_HOSTS:
        raise LLMUnavailable(f"non-localhost LLM address rejected: {host}")
    return url


def _ollama_available(timeout: float = 2.0) -> bool:
    """Probe the hardcoded Ollama endpoint without leaking non-local hosts."""
    _assert_localhost(OLLAMA_URL)
    try:
        request = urllib.request.Request(OLLAMA_URL + "/api/tags", method="GET")
        with urllib.request.urlopen(request, timeout=timeout):
            return True
    except Exception:
        return False


def _run_with_timeout(func: Any, timeout_seconds: float) -> Any:
    """Run func() with a hard timeout; TimeoutError becomes LLMUnavailable."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(func)
        try:
            return future.result(timeout=timeout_seconds)
        except TimeoutError as exc:
            raise LLMUnavailable("LLM response exceeded timeout_seconds") from exc
        except LLMUnavailable:
            raise
        except Exception as exc:
            raise LLMUnavailable(str(exc)[:300]) from exc


def _generate_llamacpp(prompt: str, config: dict[str, Any]) -> str:
    """Generate via llama-cpp-python GGUF (local file only)."""
    try:
        from llama_cpp import Llama
    except Exception as exc:
        raise LLMUnavailable("llama-cpp-python not installed") from exc
    model_path = Path(str(config.get("model_path", _DEFAULTS["model_path"])))
    if not model_path.exists():
        raise LLMUnavailable(f"GGUF missing at {model_path}")
    timeout = float(config.get("timeout_seconds", 30))

    def _call() -> str:
        llm = Llama(
            model_path=str(model_path),
            n_ctx=int(config.get("n_ctx", 4096)),
            n_threads=int(config.get("n_threads", 4)),
            seed=int(config.get("seed", 42)),
            verbose=False,
        )
        out = llm(
            prompt,
            max_tokens=int(config.get("max_tokens", 512)),
            temperature=float(config.get("temperature", 0.1)),
            top_p=float(config.get("top_p", 0.9)),
            seed=int(config.get("seed", 42)),
        )
        choices = out.get("choices", []) if isinstance(out, dict) else []
        if choices:
            return str(choices[0].get("text", ""))
        return ""

    text: str = _run_with_timeout(_call, timeout)
    return text


def _generate_ollama(prompt: str, config: dict[str, Any]) -> str:
    """Generate via Ollama on hardcoded 127.0.0.1 only."""
    url = _assert_localhost(OLLAMA_URL) + "/api/generate"
    timeout = float(config.get("timeout_seconds", 30))
    payload = {
        "model": str(config.get("ollama_model", "satsa-local")),
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": float(config.get("temperature", 0.1)),
            "top_p": float(config.get("top_p", 0.9)),
            "num_predict": int(config.get("max_tokens", 512)),
            "seed": int(config.get("seed", 42)),
        },
    }

    def _call() -> str:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
        return str(data.get("response", ""))

    try:
        text: str = _run_with_timeout(_call, timeout + 5.0)
    except TimeoutError as exc:
        raise LLMUnavailable("LLM response exceeded timeout_seconds") from exc
    return text


def generate(prompt: str, config: dict[str, Any] | None = None) -> str:
    """Generate text offline: GGUF first, then localhost Ollama.

    Raises LLMUnavailable when neither backend is reachable or on timeout.
    Never calls any non-localhost address under any code path.
    """
    cfg = dict(config) if config is not None else load_llm_config()
    errors: list[str] = []
    try:
        return _generate_llamacpp(prompt, cfg)
    except LLMUnavailable as exc:
        errors.append(str(exc))
    if _ollama_available():
        try:
            return _generate_ollama(prompt, cfg)
        except LLMUnavailable as exc:
            errors.append(str(exc))
    else:
        errors.append("ollama not reachable on 127.0.0.1:11434")
    raise LLMUnavailable("; ".join(errors)[:500])


def is_available(config: dict[str, Any] | None = None) -> bool:
    """Return True when any offline backend is reachable (air-gap safe)."""
    cfg = dict(config) if config is not None else load_llm_config()
    if Path(str(cfg.get("model_path", ""))).exists():
        try:
            import llama_cpp  # noqa: F401

            return True
        except Exception:
            pass
    return _ollama_available()
