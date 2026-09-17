"""Signal-family ablation: recall contribution per family (pure over finding sets)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from satsa.validation.benchmark import ExpertLabel, compare, family_of_signal

MARKER_START = "<!-- ABLATION-START -->"
MARKER_END = "<!-- ABLATION-END -->"


class AblationRow(BaseModel):
    """One family's recall contribution."""

    family_name: str = ""
    signals_disabled: list[str] = Field(default_factory=list)
    baseline_recall: float = 0.0
    ablated_recall: float = 0.0
    recall_drop: float = 0.0
    relative_contribution_pct: float = 0.0


def _recall(
    flagged: set[tuple[str, str]],
    details: dict[tuple[str, str], tuple[str, float]],
    labels: list[ExpertLabel],
    disabled: set[str],
) -> float:
    """Overall recall with a set of signal ids disabled."""
    return compare(flagged, details, labels, disabled=disabled).overall_recall


def ablate(
    flagged: set[tuple[str, str]],
    details: dict[tuple[str, str], tuple[str, float]],
    labels: list[ExpertLabel],
    families: tuple[str, ...] = ("execution_gap", "negative_space", "composite"),
) -> list[AblationRow]:
    """Disable each family in turn; sort rows by relative contribution desc."""
    baseline = _recall(flagged, details, labels, set())
    rows: list[AblationRow] = []
    for family in families:
        disabled = {signal for _, signal in flagged if family_of_signal(signal) == family}
        ablated = _recall(flagged, details, labels, disabled)
        drop = baseline - ablated
        rows.append(
            AblationRow(
                family_name=family,
                signals_disabled=sorted(disabled),
                baseline_recall=baseline,
                ablated_recall=ablated,
                recall_drop=drop,
                relative_contribution_pct=float(drop / baseline * 100.0) if baseline > 0 else 0.0,
            )
        )
    rows.sort(key=lambda r: r.relative_contribution_pct, reverse=True)
    return rows


def render_markdown(rows: list[AblationRow]) -> str:
    """Markdown table evidencing per-family supervisory contribution."""
    lines = [
        "## Signal-family ablation (validation)",
        "",
        "Recall contribution of each signal family, measured by disabling the",
        "family and re-scoring against ground truth. Sorted by contribution.",
        "",
        "| family | signals disabled | baseline | ablated | drop | contribution % |",
        "|--------|------------------|----------|---------|------|----------------|",
    ]
    for row in rows:
        lines.append(
            f"| {row.family_name} | {len(row.signals_disabled)} | {row.baseline_recall:.3f} | "
            f"{row.ablated_recall:.3f} | {row.recall_drop:.3f} | "
            f"{row.relative_contribution_pct:.1f} |"
        )
    return "\n".join(lines) + "\n"


def append_to_catalogue(
    rows: list[AblationRow], path: str | Path = "docs/SIGNAL_CATALOGUE.md"
) -> Path:
    """Idempotently replace the ablation section in the signal catalogue."""
    target = Path(path)
    section = f"{MARKER_START}\n{render_markdown(rows)}{MARKER_END}\n"
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    import re

    pattern = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END) + r"\n?", re.DOTALL
    )
    if pattern.search(existing):
        updated = pattern.sub(section, existing)
    else:
        updated = existing.rstrip("\n") + "\n\n" + section
    target.write_text(updated, encoding="utf-8")
    return target


def table_to_dicts(rows: list[AblationRow]) -> list[dict[str, Any]]:
    """Serialise rows for JSON export."""
    return [row.model_dump() for row in rows]
