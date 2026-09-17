"""Unit tests for the robust peer-benchmarking engine."""

from __future__ import annotations

from satsa.signals.peer_benchmark import benchmark_metric, modified_z


def test_modified_z_against_known_values() -> None:
    """The modified z formula matches hand-computed values."""
    stats = modified_z(10.0, [8.0, 9.0, 9.0, 10.0, 11.0])
    assert stats["median"] == 9.0
    assert stats["mad"] == 1.0
    assert abs(stats["modified_z"] - 0.6745) < 1e-9
    assert stats["method"] == "MAD"


def test_mad_zero_falls_back_to_iqr() -> None:
    """MAD == 0 triggers the IQR fallback instead of crashing."""
    stats = modified_z(5.0, [2.0, 2.0, 2.0, 4.0, 6.0])
    assert stats["method"] == "IQR"
    assert stats["modified_z"] != 0.0


def test_zero_range_skips_with_warning() -> None:
    """Identical peers skip benchmarking with a WARNING, not a crash."""
    import pytest

    with pytest.warns(UserWarning):
        stats = modified_z(3.0, [3.0, 3.0, 3.0])
    assert stats["method"] == "SKIP"
    assert stats["modified_z"] == 0.0


def test_single_member_cohort_falls_back_global() -> None:
    """Single-member cohorts fall back to global stats with max penalty."""
    values = {"cse_solo": 9.0, "g1": 1.0, "g2": 2.0, "g3": 1.5, "g4": 2.5, "g5": 1.2}
    out = benchmark_metric("cse_solo", "m", 9.0, values)
    assert out["cohort_too_small"] is True
    assert out["is_cohort_relative"] is False
    assert out["confidence_penalty"] == 0.40


def test_small_cohort_sets_flag_with_penalty() -> None:
    """Cohorts below n=5 set cohort_too_small with the standard penalty."""
    values = {"cse_alpha": 5.0, "cse_bravo": 1.0, "g1": 1.0, "g2": 1.1, "g3": 0.9}
    out = benchmark_metric("cse_alpha", "m", 5.0, values)
    assert out["cohort_n"] == 2
    assert out["cohort_too_small"] is True
    assert out["confidence_penalty"] == 0.20
    assert 0.0 <= out["percentile_rank"] <= 1.0
