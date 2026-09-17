# SATSA Deployment Notes (Phase 5 audit excerpt)

## Ledger archiving (R1 mitigation)

- The JSONL ledger (`data/warehouse/audit_ledger.jsonl`) grows unbounded:
  one line per RUN_START / STAGE_COMPLETE / FINDING / RUN_END / VERIFY event.
- Archiving policy: rotate monthly — move sealed months to
  `data/warehouse/archive/YYYY-MM.jsonl`, keep a manifest of archived
  ranges with their Merkle roots. The DuckDB table (`audit.duckdb`)
  remains queryable across rotation; on any divergence the JSONL archive
  is the verification source of truth (A1).
- Verification works offline end-to-end: `python -m satsa.audit.runner
  verify` needs only the local warehouse directory.

## Signature key management (R2)

- Ledger entries carry an optional Ed25519 `signature` over `entry_hash`.
- Default: unsigned (`signature=None`); the hash chain alone provides
  tamper evidence. To enable, pass a `signer` callable to
  `append_event` and manage keys out of band (HSM or sealed secret).
- Run manifests are HMAC-signed with `SATSA_MANIFEST_KEY`
  (`settings.manifest_key`); rotate before production — default values
  raise in production mode via the settings validator.

## Air-gap

- No audit or explainability code path performs network I/O. Verification
  bundles (`deliverables/<run>_audit_bundle.zip`) are the only cross-
  boundary artefact: manifest + ledger entries for the run.

## Phase 6 reporting and serving notes

- PDF rendering prefers WeasyPrint (R1: needs pango/cairo system libs —
  `apt install libpango-1.0-0 libcairo2 libgdk-pixbuf2.0-0`; without them
  the reportlab fallback runs, and without reportlab the builtin minimal
  PDF writer still produces a valid file with the Merkle root in bytes).
- Charts use matplotlib SVG (no kaleido/plotly air-gapped; R2 headless
  covered by the Agg backend, `svg.hashsalt` pinned for determinism).
- Templates are Jinja2-valid and render with Jinja2 when installed, else
  the builtin `{{ }}/for/if` subset with identical output for that subset.
- HOW TO RUN mapping (`cli.py` frozen since Phase 0; module runners):
  `satsa run --config …` → `python -m satsa.pipeline.orchestrator --run-id demo`;
  `satsa serve --port 8080` → `python -m satsa.api.main --port 8080`
  (http://127.0.0.1:8080/docs when FastAPI is installed).
- API binds 127.0.0.1 only (asserted); static token gate off by default,
  enable via `configs/api.yaml` or `SATSA_API_TOKEN*` env on shared hosts.

## Air-gap runbook (Phase 8)

Prerequisites: Ubuntu 22.04 LTS recommended, Python 3.11, git for
`pipeline_version` (falls back to `src/satsa/__init__.py` version).

| Scale | CSEs × alerts | Hardware |
|---|---|---|
| demo | ≤15 × 200 | 4c / 8 GB / 20 GB disk |
| min | ≤50 × 5k | 8c / 32 GB / 500 GB |
| recommended | ≤200 × 50k | 16c / 64 GB / 2 TB |
| large | 1000+ × 100k | 32c / 128 GB / 8 TB |

Bundle transfer: copy `sat-sa-offline-bundle.tar.zst` +
`sat-sa-bundle.sha256` via USB, optical media, or secure file transfer;
verify the hash before unpacking. Install: `tar --zstd -xf
sat-sa-offline-bundle.tar.zst && bash install_offline.sh`.
Config customisation per CSE: edit `configs/entity_registry.yaml`
(sector/size/cohort) and severity/threshold maps under
`configs/mappings/`; thresholds stay in `configs/thresholds.yaml`.
First run: `cp .env.example .env`, `make scaffold`, `make seed-demo`,
`satsa run --config configs/default.yaml` (module:
`python -m satsa.pipeline.orchestrator --run-id demo`).
Verification: `satsa audit verify` then `bash scripts/verify_airgap.sh`
(strace path on Linux, dtrace note on macOS per R1).

Docker (exact):
`docker run --network none -v $(pwd)/data:/data -v $(pwd)/models:/models -v $(pwd)/configs:/configs satsa:latest satsa run`
or `docker compose up` (API on an isolated container network).

Troubleshooting (top 10): missing venv → recreate per README; empty
reports → re-run seed-demo; ledger FAIL → restore JSONL from archive;
airgap FAIL on URL → check allowlist; PDF fallback → expected without
system libs; strace missing → static-audit path runs instead; slow runs →
use `--force` only when inputs changed; quarantine spikes → inspect
`data/quarantine/`; token 401s → check `configs/api.yaml`; bundle hash
mismatch → re-transfer, never install.

Upgrade (offline, versioned, hash-verified): transfer the new bundle,
verify its sha256, unpack beside the old tree, re-run the pipeline,
compare Merkle roots. Rollback: restore the prior bundle directory and
re-run; reports are versioned per run_id so nothing is overwritten.
