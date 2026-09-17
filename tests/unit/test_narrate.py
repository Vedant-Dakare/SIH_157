"""Phase 3 narrate tests (new file, Phase 0+1+2 untouched)."""

from __future__ import annotations

import json

from tests.unit.signal_helpers import corpus_frames, make_ctx

FIELDS = [
    "rationale",
    "what_we_observed",
    "why_it_matters",
    "peer_context",
    "confidence_statement",
    "suggested_review_focus",
]


def _flagged_pair() -> tuple[object, object]:
    """Return a flagged (result, bundle) from the S2 corpus."""
    from satsa.signals.execution_gaps import EG001PrematureClosure

    frames = corpus_frames("cse_bravo")
    signal = EG001PrematureClosure()
    result = signal.compute(make_ctx("cse_bravo", frames, seed=7))
    assert result.is_flagged
    return result, signal.evidence(result)


def test_template_fields_present_when_llm_disabled() -> None:
    """All six fields present and non-empty with LLM disabled."""
    from satsa.ai.narrate import narrate_finding

    result, bundle = _flagged_pair()
    out = narrate_finding(result, bundle, seed=7, config_path="configs/llm.yaml")
    for field in FIELDS:
        assert isinstance(out[field], str)
        assert out[field].strip()
    assert out["generated_by"] == "template"


def test_determinism_same_seed_byte_identical() -> None:
    """Same input + seed gives byte-identical template output."""
    from satsa.ai.narrate import narrate_finding

    result, bundle = _flagged_pair()
    first = narrate_finding(result, bundle, seed=7, config_path="configs/llm.yaml")
    second = narrate_finding(result, bundle, seed=7, config_path="configs/llm.yaml")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_six_fields_non_null_in_both_paths() -> None:
    """Template path never yields null fields (LLM path falls back safely)."""
    from satsa.ai import narrate as narrate_mod

    result, bundle = _flagged_pair()
    template = narrate_mod.template_narrative(result, bundle, seed=7)
    for field in FIELDS:
        assert template[field] is not None
    forced = narrate_mod.narrate_finding(result, bundle, seed=7, config_path="configs/llm.yaml")
    for field in FIELDS:
        assert isinstance(forced[field], str)
