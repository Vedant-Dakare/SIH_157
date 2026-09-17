"""Phase 7 ablation tests (new file, prior phases untouched)."""

from __future__ import annotations


def test_disabling_all_signals_kills_recall() -> None:
    """Empty finding set proves the harness has teeth (recall 0)."""
    from satsa.validation.benchmark import compare

    from tests.unit.validation_helpers import get_validation_inputs

    flagged, details, labels, _ = get_validation_inputs()
    all_ids = {signal for _, signal in flagged}
    report = compare(flagged, details, labels, disabled=all_ids)
    assert report.overall_recall == 0.0


def test_disabling_eg_family_drops_recall() -> None:
    """Removing the execution-gap family measurably hurts recall."""
    from satsa.validation.ablation import ablate
    from satsa.validation.benchmark import compare, family_of_signal

    from tests.unit.validation_helpers import get_validation_inputs

    flagged, details, labels, _ = get_validation_inputs()
    baseline = compare(flagged, details, labels).overall_recall
    eg_ids = {signal for _, signal in flagged if family_of_signal(signal) == "execution_gap"}
    ablated = compare(flagged, details, labels, disabled=eg_ids).overall_recall
    assert baseline - ablated > 0.1
    rows = ablate(flagged, details, labels)
    assert rows[0].family_name == "execution_gap"


def test_table_sorted_by_contribution() -> None:
    """Ablation rows descend by relative contribution."""
    from satsa.validation.ablation import ablate

    from tests.unit.validation_helpers import get_validation_inputs

    flagged, details, labels, _ = get_validation_inputs()
    rows = ablate(flagged, details, labels)
    assert {r.family_name for r in rows} == {"execution_gap", "negative_space", "composite"}
    values = [r.relative_contribution_pct for r in rows]
    assert values == sorted(values, reverse=True)
