"""Phase 4 risk-engine tests (new file, prior phases untouched)."""

from __future__ import annotations

import math

from tests.unit.scoring_helpers import corpus_inputs, fake_result


def test_healthy_s1_low_band_high_confidence() -> None:
    """CSE_HEALTHY (S1) scores LOW band with HIGH confidence."""
    from satsa.scoring.risk_engine import score_entity

    frames, results, features = corpus_inputs("cse_alpha")
    record = score_entity("cse_alpha", results, frames, features, run_id="t")
    assert record["band"] == "LOW"
    assert record["confidence"] == "HIGH"
    assert record["overall_score"] == 0.0
    assert record["confidence_reason"]
    assert record["computed_at"]


def test_multi_signal_fires_high_band() -> None:
    """S2+S3+S5-style multi-domain CRITICAL findings score HIGH band."""
    from satsa.scoring._config import load_scoring_config
    from satsa.scoring.risk_engine import score_entity

    frames, _, features = corpus_inputs("cse_alpha")
    fired_ids = [
        "EG-005", "NS-001",  # detection_coverage
        "EG-010", "EG-002",  # investigation_quality
        "EG-003", "EG-014",  # escalation_integrity
        "EG-001", "EG-006",  # operational_discipline
        "NS-003", "NS-004",  # peer_divergence
        "NS-006", "NS-010",  # negative_space
        "COMP-001", "COMP-003",  # governance
    ]
    fired = {sid: fake_result(sid, severity="CRITICAL") for sid in fired_ids}
    record = score_entity("cse_probe", fired, frames, features, run_id="t")
    elevated = float(load_scoring_config().get("risk_band_elevated", 75.0))
    assert record["overall_score"] >= elevated
    assert record["band"] == "HIGH"


def test_domain_scores_decompose_to_overall() -> None:
    """Weighted domain contributions sum to overall_score."""
    from satsa.scoring.risk_engine import score_entity

    frames, results, features = corpus_inputs("cse_charlie")
    record = score_entity("cse_charlie", results, frames, features, run_id="t")
    total = sum(record["domain_contributions"].values())
    assert total == record["overall_score"]
    check = sum(
        record["domain_weights"][d] * record["domain_scores"][d]
        for d in record["domain_scores"]
    )
    assert check == record["overall_score"]
    assert abs(total - check) < 1e-9


def test_band_thresholds_from_config_not_hardcoded() -> None:
    """Band edges track thresholds.yaml values."""
    from satsa.scoring._config import load_scoring_config
    from satsa.scoring.risk_engine import assign_band

    config = load_scoring_config()
    low = float(config["risk_band_low"])
    moderate = float(config["risk_band_moderate"])
    elevated = float(config["risk_band_elevated"])
    assert assign_band(low - 0.1, config) == "LOW"
    assert assign_band(low, config) == "MODERATE"
    assert assign_band(moderate, config) == "ELEVATED"
    assert assign_band(elevated, config) == "HIGH"
    assert assign_band(100.0, config) == "HIGH"


def test_aggregation_formula_max_times_breadth() -> None:
    """domain_score = max * (1 - exp(-k*n)) for known inputs."""
    from satsa.scoring.risk_engine import domain_score

    assert domain_score([], 0.8) == 0.0
    assert domain_score([80.0, 60.0], 0.8) == 80.0 * (1.0 - math.exp(-1.6))
    assert domain_score([50.0], 0.8) == 50.0 * (1.0 - math.exp(-0.8))
