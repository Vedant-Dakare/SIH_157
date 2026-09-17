"""Narrative layer: LLM path with guardrails, deterministic template fallback.

Every output carries generated_by: llm | template |
template_after_guardrail_rejection. Template mode always fills all six
fields with non-empty strings. LLM backend is imported lazily so disabled
runs never touch local_llm/llama/Ollama modules.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

PROMPT_DIR = Path(__file__).parent / "prompts"

NARRATIVE_FIELDS = [
    "rationale",
    "what_we_observed",
    "why_it_matters",
    "peer_context",
    "confidence_statement",
    "suggested_review_focus",
]


def _read_prompt(name: str) -> str:
    """Read a prompt template (empty string when missing)."""
    path = PROMPT_DIR / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _fill(template: str, values: dict[str, Any]) -> str:
    """Fill {placeholders} without Jinja2 (air-gap minimal deps)."""
    rendered = template
    for key, val in values.items():
        rendered = rendered.replace("{" + key + "}", str(val))
    return rendered


def _llm_enabled(config_path: str | Path = "configs/llm.yaml") -> tuple[bool, dict[str, Any]]:
    """Return (enabled, config) without importing the LLM client."""
    import yaml

    path = Path(config_path)
    data: dict[str, Any] = {}
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
        except Exception:
            data = {}
    return bool(data.get("enabled", False)), data


def _result_summary(result: Any) -> dict[str, Any]:
    """Coerce a SignalResult to plain values (never crashes on shape)."""

    def _get(name: str, default: Any) -> Any:
        return getattr(result, name, default)

    return {
        "signal_id": str(_get("signal_id", "UNKNOWN")),
        "entity_id": str(_get("entity_id", "unknown")),
        "value": float(_get("value", 0.0) or 0.0),
        "threshold": float(_get("threshold", 0.0) or 0.0),
        "severity": str(_get("severity", "INFO")),
        "confidence": str(_get("confidence", "LOW")),
        "sample_size": int(_get("sample_size", 0) or 0),
        "window": f"{_get('window_start', '')}..{_get('window_end', '')}",
    }


def _bundle_summary(bundle: Any) -> dict[str, str]:
    """Render evidence rows compactly for prompts."""
    supporting = getattr(bundle, "supporting_rows", []) or []
    counter = getattr(bundle, "counter_rows", []) or []
    comparison = getattr(bundle, "cohort_comparison", {}) or {}

    def _rows(rows: Any) -> str:
        if not rows:
            return "(none)"
        return json.dumps(rows[:5], default=str)[:3000]

    return {
        "supporting_rows": _rows(supporting),
        "counter_rows": _rows(counter),
        "cohort_comparison": json.dumps(comparison, default=str)[:1500],
    }


def template_narrative(result: Any, bundle: Any, seed: int = 42) -> dict[str, Any]:
    """Deterministic template narrative; all six fields non-empty strings."""
    info = _result_summary(result)
    evidence = _bundle_summary(bundle)
    supporting = getattr(bundle, "supporting_rows", []) or []
    row_ids = []
    for row in supporting:
        if isinstance(row, dict):
            for key in ("case_id", "alert_id", "investigation_id", "asset_id"):
                if row.get(key):
                    row_ids.append(str(row[key]))
                    break
    cites = ", ".join(row_ids[:2]) if len(row_ids) >= 2 else "the listed evidence rows"
    # Seed pins phrasing deterministically (byte-identical for same seed).
    variant = int(hashlib.sha256(f"{info['signal_id']}|{seed}".encode()).hexdigest(), 16) % 2
    hedge = "may suggest" if variant == 0 else "can indicate"
    rationale = (
        f"Signal {info['signal_id']} was observed for {info['entity_id']} "
        f"with value {info['value']:.3f} against threshold {info['threshold']:.3f} "
        f"(evidence: {cites}). This {hedge} a process gap worth a closer look, "
        f"though routine variation cannot be ruled out."
    )
    return {
        "rationale": rationale,
        "what_we_observed": (
            f"We observed {info['value']:.3f} versus an expected bound of "
            f"{info['threshold']:.3f} across {info['sample_size']} records "
            f"in window {info['window']}."
        ),
        "why_it_matters": (
            "Supervisors track this pattern because persistent gaps can hide "
            "unresolved risk in the triage process."
        ),
        "peer_context": (
            "Cohort comparison for this window is "
            f"{evidence['cohort_comparison'][:200] or 'unavailable'}; "
            "peer-relative standing should be read alongside local context."
        ),
        "confidence_statement": (
            f"Confidence is {info['confidence']} based on {info['sample_size']} records; "
            "larger samples would strengthen the reading."
        ),
        "suggested_review_focus": (
            f"Could you walk through a sample of the cited rows ({cites}) "
            "and confirm whether the pattern reflects practice or data coverage?"
        ),
        "generated_by": "template",
    }


def _parse_llm_json(text: str) -> dict[str, Any] | None:
    """Parse LLM JSON; None when invalid or missing fields."""
    try:
        data = json.loads(text)
    except Exception:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            data = json.loads(text[start : end + 1])
        except Exception:
            return None
    if not isinstance(data, dict):
        return None
    if any(not isinstance(data.get(f), str) or not data[f].strip() for f in NARRATIVE_FIELDS):
        return None
    return {f: str(data[f]) for f in NARRATIVE_FIELDS}


def narrate_finding(
    result: Any,
    bundle: Any,
    seed: int = 42,
    config_path: str | Path = "configs/llm.yaml",
) -> dict[str, Any]:
    """Narrate one finding via LLM+guardrails or deterministic template."""
    enabled, _ = _llm_enabled(config_path)
    if not enabled:
        return template_narrative(result, bundle, seed)
    try:
        from satsa.ai import guardrails as _guardrails
        from satsa.ai.local_llm import generate as _generate
        from satsa.ai.local_llm import load_llm_config as _load_cfg
    except Exception:
        return template_narrative(result, bundle, seed)
    cfg = _load_cfg(config_path)
    if not bool(cfg.get("enabled", False)):
        return template_narrative(result, bundle, seed)
    info = _result_summary(result)
    evidence = _bundle_summary(bundle)
    prompt = _fill(_read_prompt("narrate_finding.txt"), {**info, **evidence})
    if not prompt.strip():
        return template_narrative(result, bundle, seed)
    max_chars = int(cfg.get("max_tokens", 512)) * 4

    def _call(text: str) -> str:
        return _generate(text, cfg)

    try:
        first = _call(prompt)
    except Exception:
        return template_narrative(result, bundle, seed)
    passed, _ = _guardrails.validate_output(first, bundle, max_chars)
    parsed = _parse_llm_json(first) if passed else None
    if parsed is not None:
        return {**parsed, "generated_by": "llm"}
    strict = prompt + "\nDO NOT invent any IDs. Only use IDs from evidence. Cite >= 2 row IDs."
    try:
        second = _call(strict)
    except Exception:
        return template_narrative(result, bundle, seed)
    passed2, _ = _guardrails.validate_output(second, bundle, max_chars)
    parsed2 = _parse_llm_json(second) if passed2 else None
    if parsed2 is not None:
        return {**parsed2, "generated_by": "llm"}
    fallback = template_narrative(result, bundle, seed)
    fallback["generated_by"] = "template_after_guardrail_rejection"
    return fallback


def summarise_entity(
    entity_id: str,
    results: dict[str, Any],
    feature_summary: dict[str, Any] | None = None,
    seed: int = 42,  # noqa: ARG001
    config_path: str | Path = "configs/llm.yaml",  # noqa: ARG001
) -> dict[str, Any]:
    """Summarise one entity; template path is deterministic and complete."""
    fired = sorted(rid for rid, res in results.items() if getattr(res, "is_flagged", False))
    silent = sorted(rid for rid in results if rid not in fired)
    summary = json.dumps(feature_summary or {}, default=str)[:2000]
    _ = _read_prompt("summarise_entity.txt")  # Prompt reserved for LLM path.
    top = fired[:3]
    return {
        "executive_summary": (
            f"{entity_id} shows {len(fired)} flagged signals out of {len(results)}. "
            f"Top concerns are {', '.join(top) if top else 'none flagged'}. "
            "Overall posture should be confirmed against raw evidence."
        ),
        "top_concerns": top,
        "positive_indicators": silent[:3],
        "suggested_focus": (
            f"Which of {', '.join(top) if top else 'the monitored areas'} "
            "would you like to review first with the underlying rows?"
        ),
        "feature_summary": summary,
        "generated_by": "template",
    }


def explain_negative_space(
    result: Any,
    bundle: Any,
    seed: int = 42,  # noqa: ARG001
    config_path: str | Path = "configs/llm.yaml",  # noqa: ARG001
) -> dict[str, Any]:
    """Explain a missing-evidence finding; always notes absence != evidence."""
    info = _result_summary(result)
    _ = _read_prompt("explain_negative_space.txt")  # Prompt reserved for LLM path.
    return {
        "what_is_missing": (
            f"Signal {info['signal_id']} for {info['entity_id']} notes expected "
            f"telemetry or categories with no observations in window {info['window']}."
        ),
        "why_it_matters": (
            "Coverage gaps matter because unseen activity cannot be triaged."
        ),
        "how_to_verify": (
            "Please compare the expected-source list against collector health "
            "and confirm whether the gap is collection or activity."
        ),
        "confidence_statement": (
            f"Confidence is {info['confidence']} over {info['sample_size']} records; "
            "absence of evidence is not evidence of absence."
        ),
        "suggested_review_focus": (
            "Could you confirm whether collection was healthy for the "
            "expected sources during this window?"
        ),
        "generated_by": "template",
    }


def narrate_entity(
    entity_id: str,
    synthetic_root: str | Path = "data/synthetic",
    seed: int = 42,
) -> dict[str, Any]:
    """Narrate every flagged finding for one entity (template when LLM off)."""
    from satsa.signals.runner import run_entity

    results = run_entity(entity_id, synthetic_root=synthetic_root)
    narratives: dict[str, Any] = {}
    for signal_id, result in results.items():
        if not getattr(result, "is_flagged", False):
            continue
        try:
            from satsa.signals.registry import get_signal

            signal = get_signal(signal_id)
            bundle = signal.evidence(result) if signal is not None else None
        except Exception:
            bundle = None
        if bundle is None:
            from satsa.signals._evidence import make_bundle

            bundle = make_bundle(signal_id, result, [], [])
        narratives[signal_id] = narrate_finding(result, bundle, seed)
    return {"entity_id": entity_id, "narratives": narratives}


def main(argv: list[str] | None = None) -> int:
    """CLI entry: --entity ID | --all (module runner; cli.py untouched)."""
    parser = argparse.ArgumentParser(description="SATSA narrative runner (Phase 3)")
    parser.add_argument("--entity", default=None, help="Narrate one entity id")
    parser.add_argument("--cse-id", default=None, help="Alias for --entity")
    parser.add_argument("--all", action="store_true", help="Narrate all entities")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    target = args.entity or args.cse_id
    if target:
        out = narrate_entity(target, seed=args.seed)
        print(json.dumps(out, indent=2, default=str))
        return 0
    if args.all:
        from satsa.signals.runner import list_entities

        for entity_id in list_entities():
            out = narrate_entity(entity_id, seed=args.seed)
            flagged = sorted(out["narratives"].keys())
            print(f"{entity_id}: {len(flagged)} narratives: {flagged}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
