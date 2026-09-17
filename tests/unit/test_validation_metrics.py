"""Phase 7 validation-metric tests (new file, prior phases untouched)."""

from __future__ import annotations


def test_report_from_synthetic_ground_truth() -> None:
    """A full ValidationReport builds without error."""
    from satsa.validation.benchmark import compare

    from tests.unit.validation_helpers import get_validation_inputs

    flagged, details, labels, _ = get_validation_inputs()
    report = compare(flagged, details, labels)
    assert report.n_expected == 10
    assert report.n_flagged > 0
    assert set(report.precision_at_k) == {5, 10, 20}
    assert len(report.recall_by_scenario) == 10


def test_top5_precision_and_s2_recall() -> None:
    """Top-5 precision is nonzero; EG-001 always fires on S2."""
    from satsa.validation.benchmark import compare

    from tests.unit.validation_helpers import get_validation_inputs

    flagged, details, labels, _ = get_validation_inputs()
    report = compare(flagged, details, labels)
    assert report.precision_at_k[5] > 0
    assert report.recall_by_scenario["S2"] == 1.0


def test_kappa_bounded_and_s1_conditional() -> None:
    """Kappa in [-1, 1]; S1 appears only on genuine control fires."""
    from satsa.validation.benchmark import compare

    from tests.unit.validation_helpers import get_validation_inputs

    flagged, details, labels, _ = get_validation_inputs()
    report = compare(flagged, details, labels)
    assert -1.0 <= report.cohens_kappa <= 1.0
    assert -1.0 <= report.krippendorffs_alpha <= 1.0
    for item in report.false_positive_analysis:
        assert item["entity_id"] == "cse_alpha"
        assert (item["entity_id"], item["signal_id"]) in flagged
