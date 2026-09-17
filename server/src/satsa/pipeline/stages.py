"""Pipeline stage definitions: one StageDefinition per stage, DAG validation."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StageDefinition:
    """One DAG node: function, requirement level, dependencies, retries."""

    name: str
    function: Callable[[dict[str, Any]], dict[str, Any]]
    required: bool = True
    dependencies: list[str] = field(default_factory=list)
    retry_count: int = 3


def validate_dag(stages: list[StageDefinition]) -> None:
    """Detect unknown dependencies and cycles at startup (networkx or DFS)."""
    names = [s.name for s in stages]
    if len(set(names)) != len(names):
        raise ValueError("duplicate stage names")
    for stage in stages:
        for dep in stage.dependencies:
            if dep not in names:
                raise ValueError(f"stage {stage.name} depends on unknown {dep}")
    try:
        import networkx as nx

        graph = nx.DiGraph()
        graph.add_nodes_from(names)
        for stage in stages:
            for dep in stage.dependencies:
                graph.add_edge(dep, stage.name)
        cycles = list(nx.simple_cycles(graph))
        if cycles:
            raise ValueError(f"pipeline cycle detected: {cycles}")
        return
    except ImportError:
        pass
    order: dict[str, int] = {}
    visiting: set[str] = set()

    def _visit(node: str) -> None:
        if node in order:
            return
        if node in visiting:
            raise ValueError(f"pipeline cycle detected at {node}")
        visiting.add(node)
        for dep in next(s for s in stages if s.name == node).dependencies:
            _visit(dep)
        visiting.remove(node)
        order[node] = len(order)

    for name in names:
        _visit(name)


def _stage(
    name: str,
    required: bool,
    dependencies: list[str],
    function: Callable[[dict[str, Any]], dict[str, Any]],
) -> StageDefinition:
    """Build a stage with default retries."""
    return StageDefinition(
        name=name, function=function, required=required, dependencies=dependencies
    )


def default_stages() -> list[StageDefinition]:
    """The eleven canonical stages in dependency order."""
    from satsa.pipeline import orchestrator as orch

    return [
        _stage("ingest", True, [], orch.stage_ingest),
        _stage("canonical", True, ["ingest"], orch.stage_canonical),
        _stage("features", True, ["canonical"], orch.stage_features),
        _stage("signals", True, ["features"], orch.stage_signals),
        _stage("ml", False, ["signals"], orch.stage_ml),
        _stage("score", True, ["signals"], orch.stage_score),
        _stage("prioritise", True, ["score"], orch.stage_prioritise),
        _stage("explain", False, ["prioritise"], orch.stage_explain),
        _stage("narrate", False, ["explain"], orch.stage_narrate),
        _stage("report", False, ["prioritise"], orch.stage_report),
        _stage("audit_seal", False, ["report"], orch.stage_audit_seal),
    ]
