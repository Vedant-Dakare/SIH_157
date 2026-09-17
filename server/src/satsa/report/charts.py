"""Offline charts: matplotlib SVG, base64-embedded, with hidden data tables.

Plotly/kaleido are unavailable air-gapped, so matplotlib (Agg) renders
static SVG. Every chart embeds its underlying data as a hidden <table>
inside the SVG for accessibility fallback. Deterministic for same input.
"""

from __future__ import annotations

import base64
import hashlib
import html
import io
import re
from collections.abc import Sequence
from typing import Any

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "satsa-phase6"

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def _table_html(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    """Render a hidden data table for SVG embedding."""
    cells = "".join(f"<th>{html.escape(str(h))}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in row) + "</tr>"
        for row in rows
    )
    return f'<table style="display:none"><tr>{cells}</tr>{body}</table>'


def _b64(fig: Any, table: str, seed: int = 42) -> str:
    """Serialise a figure to base64 SVG with the data table embedded."""
    _ = seed
    buf = io.BytesIO()
    fig.savefig(buf, format="svg")
    plt.close(fig)
    svg = buf.getvalue().decode("utf-8", errors="replace")
    svg = re.sub(r"<dc:date>.*?</dc:date>", "<dc:date>1970-01-01T00:00:00</dc:date>", svg)
    if "</svg>" in svg:
        svg = svg.replace("</svg>", table + "</svg>")
    else:
        svg += table
    return base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _seeded(seed: int) -> None:
    """Pin numpy randomness for deterministic rendering."""
    np.random.seed(seed)


def risk_band_distribution(band_counts: dict[str, int], seed: int = 42) -> str:
    """Bar chart of entity counts per risk band."""
    _seeded(seed)
    bands = ["LOW", "MODERATE", "ELEVATED", "HIGH"]
    values = [int(band_counts.get(b, 0)) for b in bands]
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(bands, values, color=["#2e7d32", "#f9a825", "#e65100", "#b00020"])
    ax.set_title("Entities by risk band")
    ax.set_ylabel("Entities")
    table = _table_html(["band", "count"], [[b, v] for b, v in zip(bands, values)])
    return _b64(fig, table, seed)


def entity_trend_line(entity_id: str, windows: list[dict[str, Any]], seed: int = 42) -> str:
    """Line chart of one entity's score across windows."""
    _seeded(seed)
    labels = [str(w.get("window", f"w{i}")) for i, w in enumerate(windows)]
    values = [float(w.get("overall_score", 0.0)) for w in windows]
    fig, ax = plt.subplots(figsize=(6, 3.5))
    if len(values) >= 2:
        ax.plot(labels, values, marker="o")
    else:
        ax.text(0.5, 0.5, "insufficient history", ha="center")
    ax.set_title(f"Trend: {entity_id}")
    ax.set_ylabel("Score")
    table = _table_html(["window", "score"], [[a, b] for a, b in zip(labels, values)])
    return _b64(fig, table, seed)


def signal_heatmap(
    entity_ids: list[str], signal_ids: list[str], matrix: list[list[float]], seed: int = 42
) -> str:
    """Entity × signal heatmap of signal scores."""
    _seeded(seed)
    data = np.asarray(matrix, dtype=float) if matrix else np.zeros((1, 1))
    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(data, aspect="auto", vmin=0.0, vmax=1.0)
    ax.set_xticks(range(len(signal_ids)), signal_ids, rotation=90, fontsize=6)
    ax.set_yticks(range(len(entity_ids)), entity_ids, fontsize=6)
    ax.set_title("Signal heatmap")
    fig.colorbar(im, ax=ax)
    rows = [[e] + [round(float(v), 3) for v in row] for e, row in zip(entity_ids, data.tolist())]
    table = _table_html(["entity", *signal_ids], rows)
    return _b64(fig, table, seed)


def coverage_heatmap(
    rows: list[dict[str, Any]], seed: int = 42
) -> str:
    """Entity × asset × source gap heatmap (gap flag severity)."""
    _seeded(seed)
    keys = [
        (str(r.get("entity_id", "")), str(r.get("asset_type", "")), str(r.get("source", "")))
        for r in rows
    ]
    flags = [1.0 if str(r.get("gap", "")) in ("gap", "1", "True", "true") else 0.0 for r in rows]
    labels = [f"{e}/{a}/{s}" for e, a, s in keys] or ["none"]
    data = np.asarray([flags or [0.0]])
    fig, ax = plt.subplots(figsize=(7, max(2, 0.4 * len(labels))))
    ax.imshow(data, aspect="auto", vmin=0.0, vmax=1.0, cmap="Reds")
    ax.set_yticks(range(len(labels)), labels, fontsize=6)
    ax.set_title("Coverage gaps")
    table = _table_html(["cell", "gap"], [[a, b] for a, b in zip(labels, flags or [0.0])])
    return _b64(fig, table, seed)


def peer_scatter(
    entity_id: str, metric: str, peers: list[float], value: float, seed: int = 42
) -> str:
    """Entity value vs cohort distribution for one metric."""
    _seeded(seed)
    fig, ax = plt.subplots(figsize=(6, 3.5))
    if peers:
        ax.scatter(peers, [0.0] * len(peers), label="cohort")
    ax.scatter([value], [0.0], color="red", s=80, label=entity_id)
    median = float(np.median(peers)) if peers else value
    ax.axvline(median, color="grey", linestyle="--", label="median")
    ax.set_title(f"{metric}: {entity_id} vs cohort")
    ax.legend()
    digest = hashlib.sha256(f"{entity_id}{metric}{seed}".encode()).hexdigest()
    table = _table_html(
        ["entity", "metric", "value", "salt"], [[entity_id, metric, value, digest[:8]]]
    )
    return _b64(fig, table, seed)


def latency_distribution(
    entity_id: str, latencies: list[float], cohort_median: float, seed: int = 42
) -> str:
    """Histogram of dwell/latency values with cohort median marker."""
    _seeded(seed)
    fig, ax = plt.subplots(figsize=(6, 3.5))
    if latencies:
        ax.hist([float(v) for v in latencies], bins=min(20, max(5, len(latencies) // 5)))
    else:
        ax.text(0.5, 0.5, "no latency data", ha="center")
    ax.axvline(float(cohort_median), color="red", linestyle="--", label="cohort median")
    ax.set_title(f"Latency distribution: {entity_id}")
    ax.legend()
    median = float(np.median(latencies)) if latencies else 0.0
    table = _table_html(
        ["n", "median", "cohort_median"], [[len(latencies), median, cohort_median]]
    )
    return _b64(fig, table, seed)


def counterfactual_bars(
    finding_id: str, observed: float, required: float, threshold: float, seed: int = 42
) -> str:
    """Observed vs required vs threshold bars for a counterfactual."""
    _seeded(seed)
    labels = ["observed", "required", "threshold"]
    values = [float(observed), float(required), float(threshold)]
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(labels, values, color=["#b00020", "#2e7d32", "#616161"])
    ax.set_title(f"Counterfactual: {finding_id}")
    table = _table_html(["bar", "value"], [[a, b] for a, b in zip(labels, values)])
    return _b64(fig, table, seed)
