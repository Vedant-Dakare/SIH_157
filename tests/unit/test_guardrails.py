"""Phase 3 guardrail tests (new file, Phase 0+1+2 untouched)."""

from __future__ import annotations

from types import SimpleNamespace


def _bundle() -> SimpleNamespace:
    """Evidence with two citable rows."""
    return SimpleNamespace(
        supporting_rows=[
            {"case_id": "c1", "alert_id": "a1", "note": "value 0.9 observed"},
            {"case_id": "c2", "alert_id": "a2", "note": "value 0.2 observed"},
        ],
        counter_rows=[{"case_id": "c3"}],
        cohort_comparison={"median": 0.5},
    )


def test_hallucinated_entity_rejected() -> None:
    """Unknown IDs fail the first check."""
    from satsa.ai.guardrails import validate_output

    passed, reason = validate_output("Entity cse_evil did a1 and a2 things.", _bundle())
    assert passed is False
    assert "hallucinated" in reason


def test_pii_email_rejected() -> None:
    """Email addresses are rejected."""
    from satsa.ai.guardrails import validate_output

    passed, reason = validate_output("Contact analyst@example.com about a1 and a2.", _bundle())
    assert passed is False
    assert "PII" in reason


def test_prescriptive_language_rejected() -> None:
    """Disciplinary directives are rejected."""
    from satsa.ai.guardrails import validate_output

    passed, reason = validate_output("We recommend action on a1 and a2 now.", _bundle())
    assert passed is False
    assert "prescriptive" in reason


def test_clean_output_passes() -> None:
    """Grounded, cited, neutral text passes."""
    from satsa.ai.guardrails import validate_output

    text = "Reviewed a1 and a2 for c1 and c2; values 0.9 and 0.2 merit a look."
    passed, _ = validate_output(text, _bundle())
    assert passed is True


def test_double_rejection_falls_back() -> None:
    """Two rejections invoke the template fallback."""
    from satsa.ai.guardrails import generate_with_guardrails

    calls = {"n": 0}

    def _bad(prompt: str) -> str:
        calls["n"] += 1
        return "Contact analyst@example.com immediately."

    out = generate_with_guardrails(_bad, "prompt", _bundle(), signal_id="EG-001", entity_id="cse_x")
    assert out["generated_by"] == "template_after_guardrail_rejection"
    assert calls["n"] == 2
