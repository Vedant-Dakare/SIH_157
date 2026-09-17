"""Benchmark harness: SAT-SA findings vs ground-truth or expert labels.

Label sources (one-line config change):
  (a) data/synthetic/ground_truth.parquet (synthetic, default)
  (b) any parquet with the same schema (expert review labels)

Usage: python -m satsa.validation.benchmark --labels <parquet> [--run-id ID]
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from satsa.validation import metrics as metric_mod

DEFAULT_LABELS = Path("data/synthetic/ground_truth.parquet")
VALIDATION_ROOT = Path("data/curated/validation")

# Synthetic SIG_* ids mapped to the Phase-2 signals that plant them.
SIG_TO_SIGNAL = {
    "SIG_PREMATURE_CLOSE": "EG-001",
    "SIG_COVERAGE_GAP": "NS-001",
    "SIG_TEMPLATE_NOTES": "EG-010",
    "SIG_SLA_BREACH": "EG-005",
    "SIG_REOPEN_CHURN": "EG-002",
    "SIG_SEVERITY_MISMATCH": "EG-004",
    "SIG_BULK_CLOSE": "EG-006",
    "SIG_ESCALATION_BYPASS": "EG-003",
    "SIG_AFTER_HOURS": "EG-008",
    "SIG_DATA_QUALITY": "EG-009",
}
SIGNAL_TO_SIG = {v: k for k, v in SIG_TO_SIGNAL.items()}

MANUAL_MINUTES_PER_CASE = 10.0
RUBRIC_CASES = 200


class ExpertLabel(BaseModel):
    """One human review judgement (synthetic or NCIIPC labels share this schema)."""

    entity_id: str = Field(min_length=1)
    issue_type: str = Field(min_length=1)
    severity: str = "MEDIUM"
    evidence_ref: str | None = None
    reviewer_id: str = "synthetic"
    reviewed_at: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    note: str | None = None


def load_labels(path: str | Path = DEFAULT_LABELS) -> list[ExpertLabel]:
    """Load labels from synthetic or expert parquet (same schema)."""
    frame = pd.read_parquet(Path(path))
    labels: list[ExpertLabel] = []
    for _, row in frame.iterrows():
        if "severity" in frame.columns and str(row.get("severity", "")):
            severity = str(row.get("severity", "MEDIUM"))
        else:
            severity = "HIGH" if bool(row.get("expected_flag", 0)) else "LOW"
        labels.append(
            ExpertLabel(
                entity_id=str(row.get("entity_id", "")),
                issue_type=str(row.get("signal_id", row.get("issue_type", ""))),
                severity=severity,
                evidence_ref=None,
                reviewer_id=str(row.get("reviewer_id", "synthetic")),
                reviewed_at=str(row.get("reviewed_at", "")),
                confidence=float(row.get("confidence", 1.0) or 0.0),
                note=str(row.get("rationale", row.get("note", "") or "")) or None,
            )
        )
    return labels


def _is_positive(label: ExpertLabel) -> bool:
    """A label counts as expected-positive by severity or planted-note wording."""
    if label.severity in ("HIGH", "CRITICAL"):
        return True
    note = label.note or ""
    return "planted" in note and "not planted" not in note


def expected_set(labels: list[ExpertLabel]) -> set[tuple[str, str]]:
    """Positive (entity, signal) pairs, mapped onto Phase-2 signal ids."""
    out: set[tuple[str, str]] = set()
    for label in labels:
        if _is_positive(label):
            out.add((label.entity_id, SIG_TO_SIGNAL.get(label.issue_type, label.issue_type)))
    return out


def scenario_of(labels: list[ExpertLabel]) -> dict[str, set[tuple[str, str]]]:
    """Positive pairs grouped by scenario (scenario == entity cohort label)."""
    from satsa.synthetic.scenarios import SCENARIOS

    grouped: dict[str, set[tuple[str, str]]] = {}
    for label in labels:
        if label.entity_id in SCENARIOS:
            scenario = SCENARIOS[label.entity_id].scenario_id
        else:
            scenario = "SX"
        grouped.setdefault(scenario, set())
        if _is_positive(label):
            grouped[scenario].add(
                (label.entity_id, SIG_TO_SIGNAL.get(label.issue_type, label.issue_type))
            )
    return grouped


def collect_flagged(
    synthetic_root: str | Path = "data/synthetic", run_id: str = "validate",
) -> tuple[set[tuple[str, str]], dict[tuple[str, str], tuple[str, float]], dict[str, Any]]:
    """Run signals over all entities; return flagged pairs, ranking details, results."""
    from satsa.signals.runner import build_all_features, list_entities, run_entity

    features = build_all_features(synthetic_root)
    flagged: set[tuple[str, str]] = set()
    details: dict[tuple[str, str], tuple[str, float]] = {}
    results_by_entity: dict[str, Any] = {}
    for entity_id in list_entities(synthetic_root):
        results = run_entity(entity_id, features, synthetic_root, run_id)
        results_by_entity[entity_id] = results
        for signal_id, result in results.items():
            if bool(getattr(result, "is_flagged", False)):
                flagged.add((entity_id, signal_id))
                details[(entity_id, signal_id)] = (str(result.severity), float(result.score))
    return flagged, details, results_by_entity


def family_of_signal(signal_id: str) -> str:
    """Family for a signal id (registry-backed, composite-aware)."""
    if signal_id.startswith("COMP-"):
        return "composite"
    if signal_id.startswith("NS-"):
        return "negative_space"
    if signal_id.startswith("EG-"):
        return "execution_gap"
    return "execution_gap"


def compare(
    flagged: set[tuple[str, str]],
    details: dict[tuple[str, str], tuple[str, float]],
    labels: list[ExpertLabel],
    run_id: str = "validate",
    label_source: str = str(DEFAULT_LABELS),
    runtime_seconds: float = 0.0,
    disabled: set[str] | None = None,
) -> metric_mod.ValidationReport:
    """Compare findings against labels; disabled filters signal ids (ablation)."""
    disabled = disabled or set()
    active = {item for item in flagged if item[1] not in disabled}
    expected_active = expected_set(labels)
    ranked = metric_mod.rank_findings(active, details)
    precision = metric_mod.precision_at_k(ranked, expected_active)
    scenarios = scenario_of(labels)
    recall_scn = metric_mod.recall_by_scenario(scenarios, active)
    family_of = {signal: family_of_signal(signal) for _, signal in active | expected_active}
    _, _, f1 = metric_mod.family_scores(active, expected_active, family_of)
    universe = sorted(
        {(label.entity_id, SIG_TO_SIGNAL.get(label.issue_type, label.issue_type))
         for label in labels}
    )
    cells = [((e, s) in expected_active, (e, s) in active) for e, s in universe]
    hits = len(active & expected_active)
    overall_recall = float(hits / len(expected_active)) if expected_active else 1.0
    overall_precision = float(hits / len(active)) if active else 1.0
    n_manual_minutes = RUBRIC_CASES * MANUAL_MINUTES_PER_CASE
    saved_hours = (n_manual_minutes / 60.0 - runtime_seconds / 3600.0) / max(1, len(active))
    false_positives = [
        {"signal_id": signal, "entity_id": entity, "reason": "fired on healthy control S1"}
        for entity, signal in sorted(active)
        if entity == "cse_alpha"
    ]
    return metric_mod.ValidationReport(
        run_id=run_id,
        generated_at=datetime.now(UTC).isoformat(),
        label_source=label_source,
        precision_at_k=precision,
        recall_by_scenario=recall_scn,
        overall_recall=overall_recall,
        overall_precision=overall_precision,
        f1_by_family=f1,
        cohens_kappa=metric_mod.cohens_kappa(cells),
        krippendorffs_alpha=metric_mod.krippendorffs_alpha(cells),
        false_positive_analysis=false_positives,
        coverage_rate=overall_recall,
        efficiency_gain_hours_per_finding=float(saved_hours),
        time_to_finding={"pipeline_seconds": float(runtime_seconds),
                         "manual_estimate_seconds": float(n_manual_minutes * 60.0)},
        n_expected=len(expected_active),
        n_flagged=len(active),
        n_hits=hits,
    )


def render_html(report: metric_mod.ValidationReport) -> str:
    """Self-contained HTML validation report (no external assets)."""
    rows = "".join(
        f"<tr><td>{k}</td><td>{v:.3f}</td></tr>"
        for k, v in sorted(report.recall_by_scenario.items())
    )
    pk = "".join(
        f"<tr><td>@{k}</td><td>{v:.3f}</td></tr>" for k, v in sorted(report.precision_at_k.items())
    )
    fam = "".join(
        f"<tr><td>{k}</td><td>{v:.3f}</td></tr>" for k, v in sorted(report.f1_by_family.items())
    )
    fps = "".join(
        f"<tr><td>{f['entity_id']}</td><td>{f['signal_id']}</td><td>{f['reason']}</td></tr>"
        for f in report.false_positive_analysis
    ) or "<tr><td colspan=3>none</td></tr>"
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Validation Report — {report.run_id}</title>
<style>body{{font-family:Arial,sans-serif;margin:2em}}table{{border-collapse:collapse}}
th,td{{border:1px solid #999;padding:6px}}</style>
</head><body><h1>Validation Report ({report.run_id})</h1>
<p>Labels: {report.label_source} | {report.generated_at}</p>
<p>Recall {report.overall_recall:.3f} | Precision {report.overall_precision:.3f} |
Kappa {report.cohens_kappa:.3f} | Alpha {report.krippendorffs_alpha:.3f} |
Coverage {report.coverage_rate:.3f} | Saved {report.efficiency_gain_hours_per_finding:.2f}h each</p>
<h2>Precision@k</h2><table><tr><th>k</th><th>precision</th></tr>{pk}</table>
<h2>Recall by scenario</h2><table><tr><th>scenario</th><th>recall</th></tr>{rows}</table>
<h2>F1 by family</h2><table><tr><th>family</th><th>f1</th></tr>{fam}</table>
<h2>False positives on S1</h2>
<table><tr><th>entity</th><th>signal</th><th>reason</th></tr>{fps}</table>
<h2>Assumptions &amp; Limitations</h2>
<p>Synthetic labels are a proxy for expert review (R1); kappa treats synthetic
labels and SAT-SA as two raters (R2); S10 recall is expected to be low (R3).</p>
<footer>run {report.run_id} | {report.generated_at}</footer></body></html>"""


def write_report(
    report: metric_mod.ValidationReport, out_dir: str | Path = VALIDATION_ROOT,
    run_id: str = "validate",
) -> tuple[Path, Path]:
    """Write HTML + JSON validation reports; return both paths."""
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    html_path = target / f"{run_id}_validation_report.html"
    json_path = target / f"{run_id}_validation_report.json"
    html_path.write_text(render_html(report), encoding="utf-8")
    json_path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return html_path, json_path


def main(argv: list[str] | None = None) -> int:
    """CLI entry: --labels PATH [--run-id ID] (module runner; cli.py untouched)."""
    parser = argparse.ArgumentParser(description="SATSA validation runner (Phase 7)")
    parser.add_argument("--labels", default=str(DEFAULT_LABELS))
    parser.add_argument("--run-id", default="validate")
    parser.add_argument("--out-dir", default=str(VALIDATION_ROOT))
    args = parser.parse_args(argv)
    started = time.monotonic()
    flagged, details, _ = collect_flagged()
    runtime = time.monotonic() - started
    labels = load_labels(args.labels)
    report = compare(flagged, details, labels, run_id=args.run_id,
                     label_source=args.labels, runtime_seconds=runtime)
    html_path, json_path = write_report(report, args.out_dir, args.run_id)
    from satsa.validation.ablation import ablate, append_to_catalogue

    table = ablate(flagged, details, labels)
    append_to_catalogue(table)
    print(f"recall={report.overall_recall:.3f} precision={report.overall_precision:.3f} "
          f"kappa={report.cohens_kappa:.3f}")
    print(f"wrote {html_path} and {json_path}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
