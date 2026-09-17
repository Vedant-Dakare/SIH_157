"""Review-queue route."""

from __future__ import annotations

from typing import Any


def review_queue(query: dict[str, str], store: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    """GET /queue with optional limit."""
    try:
        limit = int(query.get("limit", "50"))
    except ValueError:
        limit = 50
    queue = list(store.get("queue", []))[: max(0, limit)]
    return 200, {"queue": queue, "insufficient_queue": store.get("insufficient", [])}
