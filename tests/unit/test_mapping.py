"""Unit tests for the YAML-driven mapping DSL."""

from __future__ import annotations

import hashlib
import os

import pytest
from satsa.errors import SatsaIngestError
from satsa.ingest.mapping import (
    apply_mapping,
    hash_value,
    load_mapping,
    normalise_severity,
    parse_timestamp,
)


def test_dsl_loads_from_fixture() -> None:
    """DSL loads correctly from fixture cse_alpha.yaml."""
    mapping = load_mapping("cse_alpha")
    assert mapping.cse_id == "cse_alpha"
    assert "alerts" in mapping.tables


def test_severity_norm_table_applied() -> None:
    """Severity norm table maps P1 to CRITICAL."""
    mapping = load_mapping("cse_alpha")
    assert mapping.tables["alerts"].fields["severity_norm"].severity_norm is True
    table = {"P1": "CRITICAL", "P2": "HIGH"}
    assert normalise_severity("P1", table) == "CRITICAL"


def test_unknown_severity_warns_not_crash() -> None:
    """Unknown severity maps to UNKNOWN with WARNING."""
    with pytest.warns(UserWarning):
        assert normalise_severity("NOPE", {"P1": "CRITICAL"}) == "UNKNOWN"


def test_timestamp_parsed_in_three_formats() -> None:
    """Timestamps parse in all three documented formats."""
    mapping = load_mapping("cse_alpha")
    rule = mapping.tables["alerts"].timestamp_fields["detected_ts"]
    assert len(rule.formats) == 3
    for raw in ["2024-01-02T03:04:05+0530", "2024-01-02 03:04:05", "02/01/2024 03:04"]:
        utc_dt, _ = parse_timestamp(raw, rule.formats, mapping.source_timezone)
        assert utc_dt.tzinfo is not None


def test_hashed_field_consistent() -> None:
    """Hashed field produces consistent SHA-256 output for same input plus salt."""
    os.environ["SATSA_ANALYST_SALT"] = "unit-salt"
    first = hash_value("alice", "SATSA_ANALYST_SALT")
    second = hash_value("alice", "SATSA_ANALYST_SALT")
    assert first == second
    assert first == hashlib.sha256(b"aliceunit-salt").hexdigest()


def test_missing_required_field_raises() -> None:
    """Missing required source field raises SatsaIngestError."""
    mapping = load_mapping("cse_alpha")
    with pytest.raises(SatsaIngestError):
        apply_mapping([{"subject": "x"}], mapping, "alerts")


def test_missing_mapping_file_identity_warns() -> None:
    """Missing mapping file falls back to identity mapping with WARNING."""
    with pytest.warns(UserWarning):
        mapping = load_mapping("cse_does_not_exist_xyz")
    assert mapping.tables == {}


def test_csv_injection_stripped_with_warning() -> None:
    """CSV injection pattern is stripped with WARNING."""
    mapping = load_mapping("cse_alpha")
    rows = [
        {
            "id": "a1",
            "host_id": "asset1",
            "subject": "=CMD|calc",
            "priority": "P1",
            "created_at": "2024-01-02 03:04:05",
        }
    ]
    with pytest.warns(UserWarning):
        mapped = apply_mapping(rows, mapping, "alerts")
    assert mapped[0]["title"] == "CMD|calc"
