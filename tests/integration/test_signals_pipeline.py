"""Integration: full signal pipeline over the ten synthetic CSEs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from satsa.signals.registry import generate_catalogue, get_enabled_signals
from satsa.signals.runner import run_all

_HIGH_ORDER = {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


@pytest.fixture(scope="module")
def pipeline() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Run the full rule + anomaly pipeline once for the module."""
    return run_all()


def test_precision_healthy_has_no_high_findings(pipeline: Any) -> None:
    """S1 (healthy) produces zero HIGH-severity findings."""
    rule_results, _ = pipeline
    for result in rule_results["cse_alpha"].values():
        if getattr(result, "is_flagged", False):
            assert _HIGH_ORDER.get(result.severity, 0) < _HIGH_ORDER["HIGH"], result.signal_id


def test_recall_planted_scenarios(pipeline: Any) -> None:
    """S2/S7/S8 fire their planted signals."""
    rule_results, _ = pipeline
    assert rule_results["cse_bravo"]["EG-001"].is_flagged is True
    assert rule_results["cse_golf"]["EG-006"].is_flagged is True
    assert rule_results["cse_hotel"]["EG-003"].is_flagged is True


def test_catalogue_generated_with_one_entry_per_signal(pipeline: Any) -> None:
    """The catalogue regenerates with one entry per enabled signal."""
    _ = pipeline
    target = generate_catalogue()
    assert target == Path("docs/SIGNAL_CATALOGUE.md")
    text = target.read_text(encoding="utf-8")
    for signal in get_enabled_signals():
        assert signal.id in text
        assert signal.name in text
