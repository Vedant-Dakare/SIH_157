"""Phase 7 validation-pipeline integration (new file, prior phases untouched)."""

from __future__ import annotations

import json
from pathlib import Path


def test_validate_cli_and_degraded_delta() -> None:
    """satsa validate exits 0, writes HTML, and degraded recall drops >= 0.10."""
    import subprocess
    import sys

    run_id = "validate-int"
    proc = subprocess.run(
        [sys.executable, "-m", "satsa.validation.benchmark", "--run-id", run_id],
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    html_path = Path("data/curated/validation") / f"{run_id}_validation_report.html"
    json_path = Path("data/curated/validation") / f"{run_id}_validation_report.json"
    assert html_path.exists()
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["n_expected"] == 10

    from satsa.validation.benchmark import compare

    from tests.unit.validation_helpers import get_validation_inputs

    flagged, details, labels, _ = get_validation_inputs()
    full = compare(flagged, details, labels).overall_recall
    degraded_ids = {"EG-001", "EG-002", "EG-003", "EG-005", "EG-006", "EG-010"}
    degraded = compare(flagged, details, labels, disabled=degraded_ids).overall_recall
    assert full - degraded >= 0.10
