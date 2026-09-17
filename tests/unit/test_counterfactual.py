"""Phase 5 counterfactual tests (new file, prior phases untouched)."""

from __future__ import annotations

from types import SimpleNamespace


def _eg001_firing() -> SimpleNamespace:
    """Real firing EG-001 result from the S2 corpus."""
    from satsa.signals.runner import build_all_features, run_entity

    features = build_all_features()
    results = run_entity("cse_bravo", features)
    result = results["EG-001"]
    assert result.is_flagged
    return result


def test_fast_close_counterfactual_numerically_correct() -> None:
    """Required value sits just below threshold so the flag would clear."""
    from satsa.explain.counterfactual import counterfactual_for

    result = _eg001_firing()
    out = counterfactual_for(result)
    assert out.computable is True
    assert out.threshold_value == result.threshold
    assert out.required_value < result.threshold
    assert out.metric_name
    assert out.plain_language
    assert out.reason_if_null == ""


def test_composite_is_null_with_reason() -> None:
    """Composite findings are explicitly non-computable."""
    from satsa.explain.counterfactual import counterfactual_for

    result = SimpleNamespace(
        finding_id="f",
        signal_id="COMP-001",
        value=1.0,
        threshold=1.0,
        is_flagged=True,
        insufficient_data=False,
    )
    out = counterfactual_for(result)
    assert out.computable is False
    assert out.reason_if_null.strip()


def test_absence_is_null_with_reason() -> None:
    """NS absence findings are explicitly non-computable."""
    from satsa.explain.counterfactual import counterfactual_for

    result = SimpleNamespace(
        finding_id="f",
        signal_id="NS-001",
        value=0.5,
        threshold=0.1,
        is_flagged=True,
        insufficient_data=False,
    )
    out = counterfactual_for(result)
    assert out.computable is False
    assert out.reason_if_null.strip()
