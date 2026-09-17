"""Explain one finding end-to-end (module runner; cli.py untouched).

Usage: python -m satsa.explain.runner --finding-id <id>
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from rich.console import Console
from rich.table import Table


def explain_finding(
    finding_id: str,
    synthetic_root: str = "data/synthetic",
    run_id: str = "phase2-run",
    record_audit: bool = True,
) -> dict[str, Any]:
    """Resolve a finding to reason, evidence, counterfactual and ledger ref."""
    from satsa.audit import ledger as audit_ledger
    from satsa.explain import counterfactual as cf_mod
    from satsa.explain import evidence as ev_mod
    from satsa.explain import reason_codes as rc_mod

    entity_id, result, bundle, signal = ev_mod.find_finding(finding_id, synthetic_root, run_id)
    signal_name = getattr(signal, "name", "") if signal is not None else ""
    reason = rc_mod.from_result(result, signal_name, bundle)
    window = f"{getattr(result, 'window_start', '')}..{getattr(result, 'window_end', '')}"
    stored = ev_mod.materialize(finding_id, reason.code, entity_id, window, bundle)
    counterfactual = cf_mod.counterfactual_for(result)
    try:
        from satsa.scoring.confidence import assess_confidence
        from satsa.signals.runner import load_entity

        frames = load_entity(entity_id, synthetic_root)
        confidence = assess_confidence(entity_id, frames, {reason.code: result}, {})
        confidence_out = {"level": confidence.level, "reason": confidence.reason}
    except Exception:
        confidence_out = {"level": str(getattr(result, "confidence", "LOW")), "reason": ""}
    audit_ref: dict[str, Any] = {"recorded": False, "seq": None}
    if record_audit:
        try:
            entry = audit_ledger.append_event(
                run_id,
                "FINDING",
                {
                    "finding_id": finding_id,
                    "signal_id": reason.code,
                    "entity_id": entity_id,
                    "evidence_id": stored.evidence_id,
                    "window": window,
                },
            )
            audit_ref = {"recorded": True, "seq": entry.seq, "entry_hash": entry.entry_hash}
        except Exception as exc:
            audit_ref = {"recorded": False, "error": str(exc)[:200]}
    return {
        "finding_id": finding_id,
        "entity_id": entity_id,
        "reason": reason.model_dump(),
        "plain": rc_mod.render_plain(reason),
        "evidence": stored.model_dump(),
        "counterfactual": counterfactual.model_dump(),
        "confidence": confidence_out,
        "audit": audit_ref,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry: --finding-id ID [--run-id ID] [--no-audit]."""
    parser = argparse.ArgumentParser(description="SATSA finding explainer (Phase 5)")
    parser.add_argument("--finding-id", required=True)
    parser.add_argument("--run-id", default="phase2-run")
    parser.add_argument("--no-audit", action="store_true")
    args = parser.parse_args(argv)
    try:
        out = explain_finding(args.finding_id, run_id=args.run_id, record_audit=not args.no_audit)
    except KeyError as exc:
        print(f"error: {exc}")
        return 1
    console = Console()
    reason = out["reason"]
    evidence = out["evidence"]
    counter = out["counterfactual"]
    table = Table(title=f"Finding {out['finding_id']} ({reason['code']})")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Entity", out["entity_id"])
    table.add_row("Reason", reason["label"])
    table.add_row("Observed / threshold", f"{reason['observed']} / {reason['threshold']}")
    table.add_row("Severity / confidence", f"{reason['severity']} / {reason['confidence']}")
    table.add_row("Plain language", reason["plain_language"])
    table.add_row("Supporting rows", str(len(evidence["supporting_rows"])))
    for row in evidence["supporting_rows"][:5]:
        table.add_row("  evidence", str(row)[:120])
    if evidence["counter_rows"]:
        table.add_row("Counter rows", str(len(evidence["counter_rows"])))
        for row in evidence["counter_rows"][:5]:
            table.add_row("  counter", str(row)[:120])
    else:
        table.add_row("Counter rows", f"none found: {evidence['counter_rows_absent_reason']}")
    baseline = reason.get("peer_baseline", {})
    table.add_row("Peer baseline", str(baseline))
    if counter["computable"]:
        table.add_row("Counterfactual", counter["plain_language"])
    else:
        table.add_row("Counterfactual", f"not computable: {counter['reason_if_null']}")
    conf_text = f"{out['confidence']['level']}: {out['confidence']['reason']}"
    table.add_row("Confidence", conf_text[:200])
    table.add_row("Audit", str(out["audit"]))
    console.print(table)
    return 0


if __name__ == "__main__":
    sys.exit(main())
