"""Phase 6 orchestrator tests with toy stages (new file, prior phases untouched)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from satsa.pipeline.stages import StageDefinition


def _succeed(ctx: dict[str, Any]) -> dict[str, Any]:
    """Toy stage output."""
    return {"records_in": 1, "records_out": 1, "warnings": [], "output": {"n": 1}}


def _ok(name: str, required: bool = True, deps: list[str] | None = None) -> StageDefinition:
    """Stage that always succeeds."""
    return StageDefinition(
        name=name, function=_succeed, required=required, dependencies=list(deps or []),
    )


def _fail(name: str, required: bool) -> StageDefinition:
    """Stage that always raises."""

    def _boom(ctx: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(f"{name} exploded")

    return StageDefinition(name=name, function=_boom, required=required, dependencies=[])


def _run(tmp_path: Path, stages: list[StageDefinition], **kwargs: Any) -> dict[str, Any]:
    """Run toy stages into tmp with isolated ledger paths."""
    from satsa.pipeline.orchestrator import run_pipeline

    return run_pipeline(
        run_id="toy", stages=stages, run_dir=tmp_path / "run",
        ledger_jsonl=tmp_path / "ledger.jsonl", ledger_db=tmp_path / "audit.duckdb",
        manifest_dir=tmp_path / "manifests", **kwargs,
    )


def test_rerun_skips_completed(tmp_path: Path) -> None:
    """Unchanged input skips finished stages on re-run."""
    out = _run(tmp_path, [_ok("a"), _ok("b", deps=["a"])])
    assert [r["status"] for r in out["rows"]] == ["ok", "ok"]
    again = _run(tmp_path, [_ok("a"), _ok("b", deps=["a"])])
    assert [r["status"] for r in again["rows"]] == ["skipped", "skipped"]


def test_force_reruns_all(tmp_path: Path) -> None:
    """--force deletes markers and reruns every stage."""
    from satsa.pipeline.orchestrator import run_pipeline

    _run(tmp_path, [_ok("a")])
    out = run_pipeline(
        run_id="toy", stages=[_ok("a")], force=True, run_dir=tmp_path / "run",
        ledger_jsonl=tmp_path / "ledger.jsonl", ledger_db=tmp_path / "audit.duckdb",
        manifest_dir=tmp_path / "manifests",
    )
    assert [r["status"] for r in out["rows"]] == ["ok"]


def test_optional_failure_continues(tmp_path: Path, capsys: Any) -> None:
    """A failing optional stage records failure and continues."""
    out = _run(tmp_path, [_ok("a"), _fail("oops", required=False), _ok("b", deps=["oops"])])
    assert [r["status"] for r in out["rows"]] == ["ok", "failed-optional", "ok"]
    assert out["aborted"] is False
    assert "oops" in capsys.readouterr().out


def test_required_failure_aborts_with_partial_manifest(tmp_path: Path, capsys: Any) -> None:
    """A failing required stage aborts and writes a partial manifest."""
    out = _run(tmp_path, [_ok("a"), _fail("boom", required=True), _ok("b", deps=["boom"])])
    assert out["aborted"] is True
    assert [r["status"] for r in out["rows"]] == ["ok", "aborted"]
    assert (tmp_path / "run" / "toy.partial.json").exists()
    assert "Run toy summary" in capsys.readouterr().out


def test_cycle_detected_at_startup() -> None:
    """Cyclic DAGs are rejected before any stage runs."""
    import pytest
    from satsa.pipeline.orchestrator import run_pipeline

    stages = [StageDefinition(name="a", function=lambda ctx: {}, required=True, dependencies=["b"]),
              StageDefinition(name="b", function=lambda ctx: {}, required=True, dependencies=["a"])]
    with pytest.raises(ValueError, match="cycle"):
        run_pipeline(run_id="toy", stages=stages, run_dir="unused")
