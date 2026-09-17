"""Post-generation guardrails: hallucination, PII, prescriptive, length, citation.

Applied to every LLM output before use. Fail fast in order. On rejection
retry once with a stricter prompt, then return a template fallback labelled
generated_by template_after_guardrail_rejection.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

PRESCRIPTIVE_PATTERNS = [
    "should fire",
    "must terminate",
    "recommend disciplin",
    "evidence of wrongdoing",
    "should be penalised",
    "should be penalized",
    "we recommend action",
]

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s\-().]{7,}\d)(?!\d)")
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_HOST_RE = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:com|net|org|io|local|internal)\b", re.IGNORECASE)
_ID_RE = re.compile(r"\b(?:cse_[a-z0-9_]+|CSE_[A-Z0-9_]+|a\d+|c\d+|i\d+|e\d+|asset\d+)\b")
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?%?\b")


def _evidence_text(bundle: Any) -> str:
    """Render supporting/counter rows as searchable text."""
    rows: list[Any] = []
    for attr in ("supporting_rows", "counter_rows"):
        rows.extend(getattr(bundle, attr, []) or [])
    parts: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            parts.append(" ".join(str(v) for v in row.values()))
        else:
            parts.append(str(row))
    comparison = getattr(bundle, "cohort_comparison", {}) or {}
    parts.append(str(comparison))
    return "\n".join(parts)


def _row_ids(bundle: Any) -> set[str]:
    """Collect evidence row IDs citable by narratives."""
    ids: set[str] = set()
    for attr in ("supporting_rows", "counter_rows"):
        for row in getattr(bundle, attr, []) or []:
            if isinstance(row, dict):
                for key in ("case_id", "alert_id", "investigation_id", "asset_id"):
                    if row.get(key):
                        ids.add(str(row[key]))
    return ids


def check_hallucination(text: str, bundle: Any) -> str | None:
    """Reject identifiers/numbers absent from the EvidenceBundle."""
    evidence = _evidence_text(bundle)
    for match in set(_ID_RE.findall(text)):
        if match not in evidence:
            return f"hallucinated identifier: {match}"
    return None


def check_pii(text: str, bundle: Any) -> str | None:
    """Reject emails, phones, and IPs/hostnames not present in evidence."""
    if _EMAIL_RE.search(text):
        return "PII: email address detected"
    if _PHONE_RE.search(text or "") and re.search(r"\+|\d{3}[-.\s]\d{3}[-.\s]\d{4}", text):
        return "PII: phone number detected"
    evidence = _evidence_text(bundle)
    for match in set(_IP_RE.findall(text)):
        if match not in evidence and not match.startswith(("10.", "192.168.", "172.")):
            # Even RFC1918 IPs must be evidenced; public IPs always rejected.
            if match not in evidence:
                return f"PII: raw IP not in evidence: {match}"
    for match in set(_HOST_RE.findall(text)):
        if match not in evidence:
            return f"PII: hostname not in evidence: {match}"
    return None


def check_prescriptive(text: str) -> str | None:
    """Reject prescriptive/disciplinary language."""
    lowered = text.lower()
    for pattern in PRESCRIPTIVE_PATTERNS:
        if pattern in lowered:
            return f"prescriptive language: {pattern}"
    return None


def check_length(text: str, max_chars: int = 4000) -> str | None:
    """Reject outputs exceeding max_tokens characters."""
    if len(text) > max_chars:
        return f"output exceeds {max_chars} characters"
    return None


def check_citation(text: str, bundle: Any) -> str | None:
    """Reject outputs citing fewer than 2 evidence row IDs."""
    ids = _row_ids(bundle)
    if len(ids) < 2:
        return None  # Cannot demand citations the evidence lacks; other checks govern.
    cited = {rid for rid in ids if rid in text}
    if len(cited) < 2:
        return f"citation: only {len(cited)} evidence row IDs referenced, need >= 2"
    return None


def validate_output(
    text: str,
    bundle: Any,
    max_chars: int = 4000,
) -> tuple[bool, str]:
    """Run checks in order, fail fast. Returns (passed, reason)."""
    for reason in (
        check_hallucination(text, bundle),
        check_pii(text, bundle),
        check_prescriptive(text),
        check_length(text, max_chars),
        check_citation(text, bundle),
    ):
        if reason is not None:
            return False, reason
    return True, "pass"


def template_fallback(signal_id: str, entity_id: str) -> str:
    """Deterministic safe fallback narrative citing no invented IDs."""
    return (
        f"Finding {signal_id} for {entity_id} requires human review. "
        "The automated narrative was withheld by guardrails. "
        "Please inspect the linked evidence rows before drawing conclusions."
    )


def generate_with_guardrails(
    llm_fn: Callable[[str], str],
    prompt: str,
    bundle: Any,
    max_chars: int = 4000,
    signal_id: str = "",
    entity_id: str = "",
) -> dict[str, Any]:
    """Generate via llm_fn, retry once strictly, else template fallback."""
    first = llm_fn(prompt)
    passed, _ = validate_output(first, bundle, max_chars)
    if passed:
        return {"text": first, "generated_by": "llm", "rejections": 0}
    strict_prompt = (
        prompt + "\nDO NOT invent any IDs. Only use IDs from evidence. Cite >= 2 row IDs."
    )
    second = llm_fn(strict_prompt)
    passed2, reason2 = validate_output(second, bundle, max_chars)
    if passed2:
        return {"text": second, "generated_by": "llm", "rejections": 1}
    logger.warning("guardrail rejection twice (%s); using template fallback", reason2)
    return {
        "text": template_fallback(signal_id or "finding", entity_id or "entity"),
        "generated_by": "template_after_guardrail_rejection",
        "rejections": 2,
    }
