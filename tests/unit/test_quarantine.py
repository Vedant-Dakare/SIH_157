"""Unit tests for quarantine append and scorecards."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from satsa.errors import SatsaQuarantineError
from satsa.ingest.quarantine import QuarantineRecord, append_quarantine, build_scorecard


def _record(idx: int, reason: str = "ENUM_VIOLATION") -> QuarantineRecord:
    """Build a quarantine record fixture."""
    return QuarantineRecord(
        cse_id="cse_alpha",
        run_id="run1",
        record_index=idx,
        reason_code=reason,
        details="test",
        raw_record={"field": "value"},
    )


def test_jsonl_written_per_schema(tmp_path: Path) -> None:
    """JSONL rows match the quarantine schema."""
    records = [_record(0), _record(1, "TIMESTAMP_MONOTONICITY_VIOLATION")]
    append_quarantine(records, "cse_alpha", "run1", tmp_path)
    lines = (tmp_path / "quarantine" / "cse_alpha.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    payload = json.loads(lines[0])
    for key in ("cse_id", "run_id", "record_index", "reason_code", "raw_record"):
        assert key in payload


def test_idempotent_on_rerun(tmp_path: Path) -> None:
    """Re-appending the same records does not duplicate rows."""
    records = [_record(0)]
    append_quarantine(records, "cse_alpha", "run1", tmp_path)
    append_quarantine(records, "cse_alpha", "run1", tmp_path)
    lines = (tmp_path / "quarantine" / "cse_alpha.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1


def test_scorecard_totals(tmp_path: Path) -> None:
    """Scorecard total_rows equals valid plus quarantined."""
    scorecard = build_scorecard("cse_alpha", "run1", 10, 7, [_record(0), _record(1), _record(2)])
    assert scorecard.total_rows == scorecard.valid_rows + scorecard.quarantined_rows


def test_reason_counts_sum(tmp_path: Path) -> None:
    """reason_code_counts sums to quarantined_rows."""
    quarantined = [_record(0), _record(1, "TIMESTAMP_MONOTONICITY_VIOLATION")]
    scorecard = build_scorecard("cse_alpha", "run1", 5, 3, quarantined)
    assert sum(scorecard.reason_code_counts.values()) == scorecard.quarantined_rows


def test_quarantine_error_only_on_write_failure(tmp_path: Path) -> None:
    """SatsaQuarantineError is raised only when the write itself fails."""
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file", encoding="utf-8")
    with pytest.raises(SatsaQuarantineError):
        append_quarantine([_record(0)], "cse_alpha", "run1", blocker)
