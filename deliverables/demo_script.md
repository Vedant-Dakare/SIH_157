# Demo script (2 minutes, shot-by-shot)

Prerequisite: `python scripts/seed_demo_data.py` (≈20 s, one time; asserts
EG-001/EG-006 signatures live). Afterwards restore the canonical suite with
`Remove-Item -Recurse data/synthetic/CSE_*` (demo corpora otherwise join
every listing).

- t=0s — Show network disabled. Run `bash scripts/verify_airgap.sh` → PASS.
- t=15s — `satsa run` (module: `python -m satsa.pipeline.orchestrator
  --run-id demo`). Show the run summary table (11 stages, all ok).
- t=35s — Show the run manifest + Merkle root in the terminal
  (`data/warehouse/runs/demo.manifest.json`).
- t=50s — Open `data/curated/reports/demo/portfolio_report.html` →
  top-band entities highlighted with confidence badges.
- t=65s — Drill into CSE_FASTCLOSE → finding EG-001 → evidence rows
  (`finding_<id>.html`).
- t=80s — Show counterfactual: "premature_rate would need to fall below
  the 0.20 threshold for EG-001 to clear".
- t=95s — Show counter-evidence panel ("none found" is explicit, never blank).
- t=110s — `satsa audit verify` (module: `python -m satsa.audit.runner
  verify`) → PASS + Merkle root.
- t=120s — `satsa validate` (module: `python -m satsa.validation.benchmark`)
  → precision@10 and recall S2 = 1.0 on screen.
