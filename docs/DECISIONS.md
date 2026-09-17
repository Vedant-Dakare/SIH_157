# SATSA Architecture Decisions

## ADR-001 — DuckDB over PostgreSQL

- Status: accepted.
- Context: the pipeline needs analytical queries over parquet corpora on
  a single air-gapped box with zero services to operate.
- Decision: DuckDB (embedded, in-process) for evidence/ledger analytics;
  parquet files as the interchange format. No database server, no
  migrations, no credentials.
- Alternatives considered: PostgreSQL (rejected: server process,
  credentials, backup story — unjustified for single-box analytics);
  pandas-only (rejected: joins over large frames are slower and hungrier).
- Consequences: single-file warehouse (`data/warehouse/*.duckdb`);
  scale-out deferred until multi-box demand exists.

## ADR-002 — Hash chain over blockchain

- Status: accepted (consolidates ADR-008, same content, canonical number).
- Context: findings need a tamper-evident, offline-verifiable audit trail.
- Decision: append-only hash chain (each entry binds prev_hash, payload,
  seq, ts, run_id, event_type) in JSONL + DuckDB kept in sync, JSONL
  authoritative on divergence; binary Merkle root per run; HMAC-signed
  run manifests. Verification is pure local recomputation.
- Alternatives considered: blockchain anchoring (rejected: needs network
  and peers); bare JSONL (rejected: tampering undetectable).
- Consequences: unbounded growth handled by the archive policy in
  `docs/DEPLOYMENT.md`; signatures optional (unsigned by default).

## ADR-003 — Template fallback over LLM dependency

- Status: accepted.
- Context: narratives must render on hardware with no model files and no
  network, while improving when a local model exists.
- Decision: three modes — template-only default (deterministic, zero
  assets), local GGUF, loopback Ollama — with guardrails on every LLM
  output and automatic fallback to templates on any failure or rejection.
- Alternatives considered: LLM-only narratives (rejected: hard dependency,
  hardware floor, hallucination surface); no narratives (rejected:
  supervisors need plain-language findings).
- Consequences: every finding renders in every mode; `generated_by`
  labels the provenance of each narrative.

## ADR-004 — Risk aggregation: max-severity × breadth dampening (Phase 4)

- Status: accepted.
- Context: entity risk must combine up to 29 signal scores across seven
  supervisory domains without letting one noisy outlier dominate, while
  still surfacing entities with broad multi-domain evidence.
- Decision: within each domain,
  `domain_score = max(severity_weighted_signal_scores) * (1 - exp(-k * n_flagged))`
  with `k = risk_breadth_k` from thresholds.yaml (default 0.8), then
  `overall = sum(domain_weight * domain_score)` with the seven domain
  weights from signals.yaml (`risk_weights`, defaults 0.20/0.20/0.15/0.15/
  0.10/0.10/0.10). Bands from thresholds.yaml
  (`risk_band_low/moderate/elevated`, defaults 25/50/75).
- Alternatives considered: plain mean (washes out a single critical
  finding), plain max (one outlier sets the whole score), additive sums
  (unbounded, hard to band). Max preserves the worst credible signal;
  the breadth term rewards corroboration without double counting.
- Consequences: single-signal entities score modestly even at HIGH
  severity; multi-domain entities rise; `k` needs production tuning (R3).
- Note: `ANALYTICS_METHODOLOGY.md` is a prior-phase file and frozen, so
  the aggregation choice is documented here instead of there.

## ADR-005 — Confidence gating and the insufficient-evidence queue (Phase 4)

- Status: accepted.
- Context: partial feeds must never be ranked alongside complete ones
  (false-accusation risk).
- Decision: `data_completeness` blends null fraction, quarantine rate
  (double-weighted), UNKNOWN-severity rate and ground-truth label
  confidence. Below 0.6 confidence is capped at LOW with
  `capped_by_completeness=true` and the entity is excluded from the main
  ranking into a separate queue. Cohort adequacy accepts the documented
  global fallback (synthetic cohorts have n = 2 by design).
- Consequences: S10 (70 quarantined / 200 alerts, completeness ≈ 0.20)
  is always quarantined from ranking; healthy entities keep HIGH.

## ADR-006 — Calibration placement (Phase 4)

- Status: accepted.
- Context: the Phase 3 isotonic calibrator maps 0-1 to 0-100 but was fit
  on synthetic labels; remapping would break score decomposition.
- Decision: `overall_score` stays the transparent weighted composite so
  every point decomposes domain → signal → evidence; the supervised
  mapping is reported separately as `calibrated_score` with an honest
  `calibrated` flag (false when the artefact is missing or drifted).

## ADR-007 — Novelty decay and review ledger (Phase 4)

- Status: accepted.
- Context: repeat findings should sink so new issues surface; first runs
  have no history (R1).
- Decision: `novelty_weight` is 1.0 with no history, `downweight`
  (default 0.4) once an entity appears in N (default 2) consecutive prior
  runs, decaying geometrically (`downweight^(streak-N+1)`) for longer
  streaks. Ledger lives at `data/scoring/ledger.json`, capped at 10 runs.
  `coverage_gap_weight` (default 1.25) applies when unreviewed for more
  than M days (default 30); never-reviewed counts as stale. Review cost
  uses `avg_review_time` (default 10 min, R2) until measured.

## ADR-008 — Hash-chained ledger over blockchain (Phase 5)

- Status: accepted.
- Context: findings need a tamper-evident, offline-verifiable audit trail.
  (Phase 5 calls this "ADR-005"; that number was already taken by the
  Phase 4 confidence-gating decision, so it is recorded here as ADR-008
  with identical content.)
- Decision: append-only hash chain (each entry binds prev_hash, payload,
  seq, ts, run_id, event_type) in JSONL + DuckDB kept in sync, JSONL
  authoritative on divergence; binary Merkle root per run; HMAC-signed
  run manifests. No blockchain: no network, no consensus, no external
  dependency — verification is pure local recomputation (`verify_chain`).
- Alternatives considered: blockchain anchoring (rejected: requires
  network/peers, incompatible with air-gap); bare JSONL without hashes
  (rejected: tampering undetectable); DuckDB-only (rejected: binary
  format harder to archive/diff than JSONL).
- Consequences: unbounded JSONL growth handled by the archiving policy in
  `docs/DEPLOYMENT.md`; signatures optional (unsigned by default).

## ADR-009 — No auto-tuning of thresholds in production (Phase 7)

- Status: accepted.
- Context: adjudication feedback proposes threshold adjustments, and an
  automated loop could apply them. (Phase 7 calls this "ADR-006"; that
  number was already taken by the Phase 4 calibration-placement decision,
  so it is recorded here as ADR-009 with identical content.)
- Decision: thresholds change only by human-edited `thresholds.yaml`
  commits. The pipeline records `AdjudicationFeedback` (including an
  advisory `threshold_adjustment`) to `adjudications.jsonl` and stops
  there — no training, fitting, or config rewrite runs in production.
- Alternatives considered: closed-loop auto-tuning (rejected: silent
  sensitivity drift, unauditable); reviewer-vote auto-apply above a
  quorum (rejected: same auditability problem, weaker form).
- Consequences: threshold changes are slow and reviewable; every change
  is a versioned config diff attributable to a human.

