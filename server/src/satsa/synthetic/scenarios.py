"""Scenario definitions for the 10 synthetic CSE corpora."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScenarioConfig(BaseModel):
    """Configuration for one synthetic CSE scenario."""

    entity_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    alert_volume: int = Field(ge=0)
    seed: int = Field(ge=0)
    planted_signals: list[str] = Field(default_factory=list)
    description: str = Field(min_length=1)
    alert_volume_range: tuple[int, int] = Field(default=(0, 0))


SCENARIOS: dict[str, ScenarioConfig] = {
    "cse_alpha": ScenarioConfig(
        entity_id="cse_alpha",
        scenario_id="S1",
        alert_volume=200,
        seed=1001,
        planted_signals=[],
        description=(
            "S1 healthy baseline with normal triage, "
            "full coverage, and no planted anomalies."
        ),
        alert_volume_range=(180, 220),
    ),
    "cse_bravo": ScenarioConfig(
        entity_id="cse_bravo",
        scenario_id="S2",
        alert_volume=200,
        seed=1002,
        planted_signals=["SIG_PREMATURE_CLOSE"],
        description="S2 rushed triage where CRITICAL cases close within minutes of opening.",
        alert_volume_range=(180, 220),
    ),
    "cse_charlie": ScenarioConfig(
        entity_id="cse_charlie",
        scenario_id="S3",
        alert_volume=200,
        seed=1003,
        planted_signals=["SIG_COVERAGE_GAP"],
        description="S3 coverage gap with CRITICAL assets missing expected telemetry sources.",
        alert_volume_range=(180, 220),
    ),
    "cse_delta": ScenarioConfig(
        entity_id="cse_delta",
        scenario_id="S4",
        alert_volume=200,
        seed=1004,
        planted_signals=["SIG_TEMPLATE_NOTES"],
        description="S4 templated investigations with boilerplate notes swapped by minor words.",
        alert_volume_range=(180, 220),
    ),
    "cse_echo": ScenarioConfig(
        entity_id="cse_echo",
        scenario_id="S5",
        alert_volume=260,
        seed=1005,
        planted_signals=["SIG_SLA_BREACH"],
        description="S5 backlog with cases breaching the response SLA window.",
        alert_volume_range=(230, 290),
    ),
    "cse_foxtrot": ScenarioConfig(
        entity_id="cse_foxtrot",
        scenario_id="S6",
        alert_volume=220,
        seed=1006,
        planted_signals=["SIG_REOPEN_CHURN", "SIG_SEVERITY_MISMATCH"],
        description="S6 churn with repeated reopens and alert-case severity mismatch.",
        alert_volume_range=(200, 240),
    ),
    "cse_golf": ScenarioConfig(
        entity_id="cse_golf",
        scenario_id="S7",
        alert_volume=220,
        seed=1007,
        planted_signals=["SIG_BULK_CLOSE"],
        description="S7 bulk-close with 150 cases closed by one analyst in a 20-second window.",
        alert_volume_range=(200, 240),
    ),
    "cse_hotel": ScenarioConfig(
        entity_id="cse_hotel",
        scenario_id="S8",
        alert_volume=200,
        seed=1008,
        planted_signals=["SIG_ESCALATION_BYPASS"],
        description="S8 escalation bypass with CRITICAL T1 cases and an empty escalations table.",
        alert_volume_range=(180, 220),
    ),
    "cse_india": ScenarioConfig(
        entity_id="cse_india",
        scenario_id="S9",
        alert_volume=210,
        seed=1009,
        planted_signals=["SIG_AFTER_HOURS"],
        description="S9 after-hours activity concentrated outside business hours.",
        alert_volume_range=(190, 230),
    ),
    "cse_juliet": ScenarioConfig(
        entity_id="cse_juliet",
        scenario_id="S10",
        alert_volume=200,
        seed=1010,
        planted_signals=["SIG_DATA_QUALITY"],
        description=(
            "S10 partial feed with nulled fields, "
            "monotonicity violations, and unknown severities."
        ),
        alert_volume_range=(180, 220),
    ),
}

ALL_SIGNAL_IDS: list[str] = [
    "SIG_PREMATURE_CLOSE",
    "SIG_COVERAGE_GAP",
    "SIG_TEMPLATE_NOTES",
    "SIG_SLA_BREACH",
    "SIG_REOPEN_CHURN",
    "SIG_SEVERITY_MISMATCH",
    "SIG_BULK_CLOSE",
    "SIG_ESCALATION_BYPASS",
    "SIG_AFTER_HOURS",
    "SIG_DATA_QUALITY",
]


def get_scenario(entity_id: str) -> ScenarioConfig:
    """Return the ScenarioConfig for an entity identifier."""
    return SCENARIOS[entity_id]
