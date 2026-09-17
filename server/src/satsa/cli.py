"""SATSA command-line interface (Phase 0+1: scaffold + seed-demo live, rest stubbed)."""

from __future__ import annotations

from datetime import UTC
from pathlib import Path

import typer
from rich import print as rprint

app = typer.Typer(help="SOC Alert Triage & Security Analytics (air-gapped).")


def _not_implemented(subcommand: str, description: str) -> None:
    """Print the standard Phase 0+1 not-implemented message."""
    rprint(f"[NOT YET IMPLEMENTED] satsa {subcommand} — will {description}")


@app.command()
def scaffold() -> None:
    """Create the project folder tree idempotently."""
    dirs = [
        "configs/mappings",
        "data/synthetic",
        "data/quarantine",
        "data/raw",
        "data/processed",
        "models/embeddings",
        "server/src/satsa/canonical",
        "server/src/satsa/ingest",
        "server/src/satsa/signals",
        "server/src/satsa/ml",
        "server/src/satsa/ai",
        "server/src/satsa/synthetic",
        "server/src/satsa/reporting",
        "scripts",
        "tests/unit",
        "tests/property",
        "tests/integration",
        "docs",
    ]
    for entry in dirs:
        Path(entry).mkdir(parents=True, exist_ok=True)
    rprint("scaffold complete")


@app.command(name="seed-demo")
def seed_demo() -> None:
    """Generate the 10 synthetic CSE corpora plus ground truth."""
    from datetime import datetime

    import pandas as pd

    from satsa.ingest.quarantine import append_quarantine
    from satsa.ingest.validators import validate_records
    from satsa.synthetic.adversarial import apply_adversarial
    from satsa.synthetic.generator import generate_all

    fixed_base = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
    generate_all(base_time=fixed_base)
    apply_adversarial()
    juliet_alerts = Path("data/synthetic/cse_juliet/alerts.parquet")
    if juliet_alerts.exists():
        frame = pd.read_parquet(juliet_alerts)
        records = frame.to_dict(orient="records")
        _, quarantined = validate_records(
            records, record_type="alert", cse_id="cse_juliet", run_id="seed-demo"
        )
        if quarantined:
            append_quarantine(quarantined, "cse_juliet", "seed-demo", "data")
    rprint("seed-demo complete: 10 CSE corpora + ground_truth.parquet")


@app.command()
def ingest(
    source: Path = typer.Option(..., exists=True, readable=True, help="CSV/JSON/Parquet directory or SQLite/DuckDB export."),
    cse_id: str = typer.Option(..., help="Private entity identifier, for example acme_finance."),
    run_id: str = typer.Option("ingest", help="Audit and quarantine batch identifier."),
) -> None:
    """Ingest raw CSE submissions into canonical tables."""
    from satsa.ingest.loaders import materialize_submission

    report = materialize_submission(source, cse_id, run_id)
    rprint(
        f"ingest complete: {report['valid_rows']} valid rows, "
        f"{report['quarantined_rows']} quarantined; corpus written for {cse_id}"
    )


@app.command()
def validate() -> None:
    """Validate canonical tables and update quarantine ledgers."""
    _not_implemented("validate", "validate canonical records and write quarantine JSONL")


@app.command()
def signals() -> None:
    """Compute SOC signals from canonical data."""
    _not_implemented("signals", "compute detection signals from canonical tables")


@app.command()
def score() -> None:
    """Score entities and produce rankings."""
    _not_implemented("score", "score entities against peer cohorts")


@app.command()
def report() -> None:
    """Render analyst reports from scores and signals."""
    _not_implemented("report", "render PDF and JSON reports for analysts")


@app.command()
def cohorts() -> None:
    """Show peer cohort assignments."""
    _not_implemented("cohorts", "display peer cohort membership and definitions")


@app.command()
def coverage() -> None:
    """Check telemetry coverage expectations."""
    _not_implemented("coverage", "check telemetry coverage against expectations")


@app.command()
def audit() -> None:
    """Verify audit manifests and ledgers."""
    _not_implemented("audit", "verify manifest and ledger integrity")


@app.command(name="llm-check")
def llm_check() -> None:
    """Check LLM backend availability without enabling it."""
    _not_implemented("llm-check", "probe LLM backend availability (air-gap safe)")


@app.command()
def serve(port: int = 8080) -> None:
    """Serve the API and the UI build on loopback only (UI served when built)."""
    from satsa.api.main import API_HOST, run_server

    rprint(f"serving SAT-SA on http://{API_HOST}:{port} (UI at / when ui/dist exists)")
    run_server(port)


if __name__ == "__main__":
    app()
