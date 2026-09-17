"""Phase 7 validation test helpers (new file, prior phases untouched)."""

from __future__ import annotations

from typing import Any

_cache: dict[str, Any] = {}


def get_validation_inputs() -> tuple[
    set[tuple[str, str]], dict[tuple[str, str], tuple[str, float]], Any, Any
]:
    """Collect signals + labels once per session (cached)."""
    if "payload" not in _cache:
        from satsa.validation.benchmark import collect_flagged, load_labels

        flagged, details, results = collect_flagged()
        labels = load_labels()
        _cache["payload"] = (flagged, details, labels, results)
    return _cache["payload"]
