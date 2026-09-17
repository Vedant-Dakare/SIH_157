"""Self-contained HTML rendering: DuckDB/store → Jinja2 (or builtin) → HTML files.

Templates are valid Jinja2 using only variables, for-loops and if-blocks so
the builtin fallback renders byte-identical output when Jinja2 is absent.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

TEMPLATE_DIR = Path(__file__).parent / "templates"
REPORTS_ROOT = Path("data/curated/reports")

ASSUMPTIONS = (
    "Scores are supervisory triage aids, not verdicts. Synthetic-data thresholds "
    "approximate production; partial feeds are quarantined from ranking; absence "
    "of evidence is not evidence of absence. A human examiner makes all decisions."
)
METHODOLOGY = (
    "Transparent weighted composite over seven domains (ADR-004); confidence "
    "gating with a separate insufficient-evidence queue (ADR-005); hash-chained "
    "audit ledger with Merkle roots (ADR-008)."
)


def _resolve(expr: str, ctx: dict[str, Any]) -> Any:
    """Resolve dotted names against the context (missing → '')."""
    current: Any = ctx
    for part in expr.strip().split("."):
        if isinstance(current, dict):
            current = current.get(part, "")
        else:
            current = getattr(current, part, "")
        if current == "":
            return ""
    return current


def _builtin_render(template: str, ctx: dict[str, Any]) -> str:
    """Minimal Jinja-subset renderer: vars, for-loops, if-blocks (nestable)."""
    for_pattern = re.compile(
        r"{%\s*for\s+(\w+)\s+in\s+([\w.]+)\s*%}(.*?){%\s*endfor\s*%}", re.DOTALL
    )
    if_pattern = re.compile(r"{%\s*if\s+([\w.]+)\s*%}(.*?){%\s*endif\s*%}", re.DOTALL)

    def _for(match: re.Match[str]) -> str:
        var, seq_expr, body = match.group(1), match.group(2), match.group(3)
        seq = _resolve(seq_expr, ctx)
        if not isinstance(seq, list | tuple):
            return ""
        return "".join(_builtin_render(body, {**ctx, var: item}) for item in seq)

    def _if(match: re.Match[str]) -> str:
        expr, body = match.group(1), match.group(2)
        return _builtin_render(body, ctx) if _resolve(expr, ctx) else ""

    previous = None
    rendered = template
    while previous != rendered:
        previous = rendered
        rendered = for_pattern.sub(_for, rendered)
        rendered = if_pattern.sub(_if, rendered)
    var_pattern = re.compile(r"{{\s*([\w.]+)\s*}}")
    return var_pattern.sub(lambda m: html.escape(str(_resolve(m.group(1), ctx))), rendered)


def render_template(name: str, ctx: dict[str, Any]) -> str:
    """Render a template with Jinja2 when installed, else the builtin subset."""
    text = (TEMPLATE_DIR / name).read_text(encoding="utf-8")
    try:
        from jinja2 import Environment, FileSystemLoader, select_jinja_autoescape

        env = Environment(
            loader=FileSystemLoader(str(TEMPLATE_DIR)),
            autoescape=select_jinja_autoescape(["html"]),
        )
        rendered: str = env.get_template(name).render(**ctx)
        return rendered
    except ImportError:
        return _builtin_render(text, ctx)


def _footer(store: dict[str, Any]) -> dict[str, Any]:
    """Shared footer / methodology context."""
    return {
        "generated_at": str(store.get("generated_at", "")),
        "run_id": str(store.get("run_id", "")),
        "pipeline_version": str(store.get("pipeline_version", "phase6")),
        "merkle_root": str(store.get("merkle_root", "")),
        "methodology": METHODOLOGY,
        "assumptions": ASSUMPTIONS,
    }


def _write(out_dir: Path, filename: str, content: str) -> str:
    """Write report HTML and return the text."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / filename).write_text(content, encoding="utf-8")
    return content


def render_portfolio_report(
    run_id: str, settings: Any = None, store: dict[str, Any] | None = None,
    out_dir: str | Path | None = None,
) -> str:
    """Render all-entities-by-band portfolio HTML."""
    from satsa.report import charts as chart_mod

    _ = settings
    store = store or load_store(run_id)
    records = store.get("records", {})
    bands: dict[str, int] = {}
    for record in records.values():
        bands[record.get("band", "LOW")] = bands.get(record.get("band", "LOW"), 0) + 1
    findings = sorted(
        (
            {"entity_id": f["entity_id"], "signal_id": f["signal_id"],
             "score": round(float(f.get("score", 0.0)), 3),
             "band": f.get("band", "LOW"), "confidence": f.get("confidence", "LOW")}
            for f in store.get("findings", {}).values()
        ),
        key=lambda f: f["score"],
        reverse=True,
    )[:5]
    sectors: dict[str, list[float]] = {}
    for entity_id, record in records.items():
        sectors.setdefault(str(record.get("sector", "unknown")), []).append(
            float(record.get("overall_score", 0.0)))
    import statistics

    ctx = {
        "run_id": run_id,
        "window": str(store.get("window", "")),
        "band_chart": chart_mod.risk_band_distribution(bands),
        "band_rows": [
            {"band": b, "count": bands.get(b, 0)} for b in ("LOW", "MODERATE", "ELEVATED", "HIGH")
        ],
        "top_findings": findings,
        "sector_rows": [
            {"sector": s, "median": round(float(statistics.median(v)), 2)}
            for s, v in sorted(sectors.items())
        ],
        "trend": str(store.get("portfolio_trend", "STABLE")),
        **_footer(store),
    }
    target = Path(out_dir) if out_dir else REPORTS_ROOT / run_id
    return _write(target, "portfolio_report.html", render_template("portfolio_report.html", ctx))


def _peer_scores(store: dict[str, Any], entity_id: str) -> list[float]:
    """Overall scores of all other entities for peer charts."""
    return [
        float(r.get("overall_score", 0.0))
        for e, r in store.get("records", {}).items()
        if e != entity_id
    ]


def render_entity_report(
    entity_id: str, run_id: str, settings: Any = None, store: dict[str, Any] | None = None,
    out_dir: str | Path | None = None,
) -> str:
    """Render one CSE deep-dive HTML."""
    from satsa.report import charts as chart_mod

    _ = settings
    store = store or load_store(run_id)
    record = store.get("records", {}).get(entity_id, {})
    domains = [
        {"name": d, "score": round(float(s), 2),
         "contribution": round(float(record.get("domain_contributions", {}).get(d, 0.0)), 2),
         "signals": ", ".join(record.get("domain_members", {}).get(d, [])) or "—"}
        for d, s in record.get("domain_scores", {}).items()
    ]
    findings = [f for f in store.get("findings", {}).values() if f.get("entity_id") == entity_id]
    fallback_window = [{"window": store.get("window", ""),
                        "overall_score": record.get("overall_score", 0.0)}]
    history = store.get("trend_windows", {}).get(entity_id, fallback_window)
    ctx = {
        "entity_id": entity_id,
        "overall_score": round(float(record.get("overall_score", 0.0)), 2),
        "band": record.get("band", "LOW"),
        "confidence": record.get("confidence", "LOW"),
        "confidence_reason": str(record.get("confidence_reason", "")),
        "trend_chart": chart_mod.entity_trend_line(entity_id, history),
        "domains": domains,
        "findings": [
            {"signal_id": f.get("signal_id", ""), "label": f.get("label", ""),
             "plain_language": f.get("plain_language", ""),
             "observed": f.get("observed", ""), "threshold": f.get("threshold", ""),
             "comparator": ">=",
             "peer_median": (f.get("peer_baseline", {}) or {}).get("median", ""),
             "peer_n": (f.get("peer_baseline", {}) or {}).get("n", ""),
             "counterfactual": f.get("counterfactual", ""),
             "evidence_summary": f.get("evidence_summary", "")}
            for f in findings
        ],
        "peer_chart": chart_mod.peer_scatter(
            entity_id, "overall_score", _peer_scores(store, entity_id),
            float(record.get("overall_score", 0.0))),
        "quality_rows": [
            {"metric": k, "value": v}
            for k, v in (store.get("data_quality", {}).get(entity_id, {}) or {}).items()
        ],
        "window": str(store.get("window", "")),
        **_footer(store),
    }
    target = Path(out_dir) if out_dir else REPORTS_ROOT / run_id
    page = render_template("entity_report.html", ctx)
    return _write(target, f"entity_{entity_id}.html", page)


def _cf_chart(
    chart_mod: Any, finding_id: str, finding: dict[str, Any], counter: dict[str, Any]
) -> str:
    """Counterfactual bars when computable, else an insufficiency placeholder."""
    if counter.get("computable"):
        chart: str = chart_mod.counterfactual_bars(
            finding_id,
            float(finding.get("observed", 0.0) or 0.0),
            float(counter.get("required_value", 0.0) or 0.0),
            float(finding.get("threshold", 0.0) or 0.0),
        )
        return chart
    placeholder: str = chart_mod.entity_trend_line(finding_id, [])
    return placeholder


def render_finding_detail(
    finding_id: str, run_id: str, store: dict[str, Any] | None = None,
    out_dir: str | Path | None = None,
) -> str:
    """Render one finding's full detail HTML."""
    from satsa.report import charts as chart_mod

    store = store or load_store(run_id)
    finding = store.get("findings", {}).get(finding_id, {})
    counter = finding.get("counterfactual", {}) or {}
    ctx = {
        "finding_id": finding_id,
        "signal_id": finding.get("signal_id", ""),
        "entity_id": finding.get("entity_id", ""),
        "severity": finding.get("severity", "INFO"),
        "confidence": finding.get("confidence", "LOW"),
        "plain_language": finding.get("plain_language", ""),
        "observed": finding.get("observed", ""),
        "threshold": finding.get("threshold", ""),
        "comparator": ">=",
        "window": finding.get("window", ""),
        "supporting_rows": [
            {"n": i + 1, "text": str(r)[:300]}
            for i, r in enumerate(finding.get("supporting_rows", [])[:10])
        ],
        "has_counter": bool(finding.get("counter_rows")),
        "counter_rows": [
            {"n": i + 1, "text": str(r)[:300]}
            for i, r in enumerate(finding.get("counter_rows", [])[:10])
        ],
        "counter_note": finding.get("counter_absent_reason", "")
        or "Counter-evidence listed above.",
        "peer_median": (finding.get("peer_baseline", {}) or {}).get("median", ""),
        "peer_p95": (finding.get("peer_baseline", {}) or {}).get("p95", ""),
        "peer_n": (finding.get("peer_baseline", {}) or {}).get("n", ""),
        "cohort_id": (finding.get("peer_baseline", {}) or {}).get("cohort_id", ""),
        "counterfactual_chart": _cf_chart(chart_mod, finding_id, finding, counter),
        "counterfactual_text": counter.get("plain_language", "")
        or counter.get("reason_if_null", ""),
        "confidence_reason": finding.get("confidence_reason", ""),
        "audit_ref": str(finding.get("audit_ref", "")),
        **_footer(store),
    }
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in finding_id)
    target = Path(out_dir) if out_dir else REPORTS_ROOT / run_id
    page = render_template("finding_detail.html", ctx)
    return _write(target, f"finding_{safe}.html", page)


def _completeness_of(store: dict[str, Any], entity_id: str) -> float:
    """Rounded data completeness for one entity."""
    record = store.get("records", {}).get(entity_id, {})
    return round(float(record.get("data_completeness", 0.0)), 2)


def render_review_queue(
    run_id: str, settings: Any = None, store: dict[str, Any] | None = None,
    out_dir: str | Path | None = None,
) -> str:
    """Render the prioritised worklist HTML (print-ready A4 landscape)."""
    _ = settings
    store = store or load_store(run_id)
    ctx = {
        "run_id": run_id,
        "entries": [
            {"rank": e.get("rank", i + 1), "entity_id": e.get("entity_id", ""),
             "focus_area": e.get("focus_area", ""),
             "signal_ids": ", ".join(e.get("signal_ids", [])),
             "minutes": e.get("expected_review_minutes", 0),
             "alerts": ", ".join(e.get("sample_alert_ids", [])[:5]),
             "cases": ", ".join(e.get("sample_case_ids", [])[:5])}
            for i, e in enumerate(store.get("queue", []))
        ],
        "insufficient": [
            {"entity_id": e, "completeness": _completeness_of(store, e)}
            for e in store.get("insufficient", [])
        ],
        **_footer(store),
    }
    target = Path(out_dir) if out_dir else REPORTS_ROOT / run_id
    return _write(target, "review_queue.html", render_template("review_queue.html", ctx))


def render_negative_space_map(
    run_id: str, store: dict[str, Any] | None = None, out_dir: str | Path | None = None,
) -> str:
    """Render the coverage heatmap HTML."""
    from satsa.report import charts as chart_mod

    store = store or load_store(run_id)
    cells = store.get("coverage_cells", [])
    ctx = {
        "run_id": run_id,
        "coverage_chart": chart_mod.coverage_heatmap(cells),
        "cells": [
            {"entity_id": c.get("entity_id", ""), "asset_type": c.get("asset_type", ""),
             "source": c.get("source", ""), "gap": c.get("gap", ""),
             "css": c.get("css", "gap-ok"), "link": c.get("link", "#"),
             "finding_id": c.get("finding_id", "")}
            for c in cells
        ],
        **_footer(store),
    }
    target = Path(out_dir) if out_dir else REPORTS_ROOT / run_id
    page = render_template("negative_space_map.html", ctx)
    return _write(target, "negative_space_map.html", page)


def render_data_quality_report(
    run_id: str, store: dict[str, Any] | None = None, out_dir: str | Path | None = None,
) -> str:
    """Render the per-CSE ingestion scorecard HTML."""
    store = store or load_store(run_id)
    rows = []
    for entity_id, quality in (store.get("data_quality", {}) or {}).items():
        rate = float(quality.get("quarantine_rate", 0.0))
        rows.append({
            "entity_id": entity_id, "total": quality.get("total", 0),
            "valid": quality.get("valid", 0), "quarantined": quality.get("quarantined", 0),
            "rate": round(rate, 3), "top_reason": str(quality.get("top_reason", "—")),
            "health": "POOR" if rate >= 0.2 else ("DEGRADED" if rate >= 0.05 else "HEALTHY"),
        })
    ctx = {
        "run_id": run_id,
        "rows": sorted(rows, key=lambda r: r["entity_id"]),
        "trend_note": str(store.get("quality_trend", "Single-window run; trends after repeats.")),
        **_footer(store),
    }
    target = Path(out_dir) if out_dir else REPORTS_ROOT / run_id
    page = render_template("data_quality_report.html", ctx)
    return _write(target, "data_quality_report.html", page)


def load_store(run_id: str, root: str | Path = REPORTS_ROOT) -> dict[str, Any]:
    """Load a run store built by the orchestrator report stage."""
    import json

    path = Path(root) / run_id / "run_store.json"
    data: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"invalid run store: {path}")
    return data
