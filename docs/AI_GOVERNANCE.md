# SATSA AI Governance (Phase 3)

Covers PS §5 AI disclosures for every model: purpose, architecture,
training-data provenance + hash, hardware, offline training, inference,
update mechanism, explainability, auditability, limitations, failure modes,
and human-in-the-loop boundary. All inference runs air-gapped; LLM defaults
to disabled (`configs/llm.yaml` `enabled: false`).

Global rules: no network under any code path (verified by
`scripts/verify_airgap.sh`); feature-list drift raises or emits
`calibrated: false` (never silent); guardrails reject hallucinated IDs,
PII, prescriptive language, over-length and under-cited outputs; anomaly
output is never a standalone finding (`paired_signal_id` required).

---

## 1. Anomaly ensemble (PyOD + robust Mahalanobis)

- Purpose: unsupervised peer-relative outlier scoring over the 122-column
  entity feature vector; triage aid only, never a finding by itself.
- Architecture: IsolationForest, ECOD, COPOD, HBOS, LOF (PyOD) plus robust
  Mahalanobis via MinCovDet with median-distance fallback; ensemble by mean
  rank; ablation contributions per feature stored for Phase 3 review.
  Code: `src/satsa/signals/anomaly.py`.
- Training data provenance and hash: entity feature vectors built from
  `data/synthetic/*/alerts|cases|investigations|escalations|assets|telemetry.parquet`
  (seed 42 corpora); no external data. Hash via `training_data_hash()`
  recorded in `models/registry.json` on calibration runs.
- Hardware requirements: CPU-only; 2 GB RAM minimum, 4 GB recommended for
  10-entity runs; no GPU required.
- Offline training procedure: 1) `seed-demo` corpora present; 2) build
  features via `satsa.signals.runner.build_all_features`; 3) fit ensemble
  in-memory per run (no persisted weights except contributions JSON).
- Inference procedure: same feature pipeline, `ensemble_scores()` then
  `feature_contributions()` median-ablation; pair with top rule signal.
- Update mechanism: manual, offline, versioned — code change + registry
  entry; no auto-retraining.
- Explainability controls: per-entity `top5_contributing_features` plus full
  contribution dict; never sole basis for a finding.
- Auditability controls: deterministic seed; contributions JSON alongside
  result; `paired_signal_id` logged.
- Known limitations: needs >= 2 entities with >= 2 varying features;
  single-entity runs fall back to peer benchmarks; small-n ranks are coarse.
- Failure modes and mitigations: degenerate matrix → per-model zero-vector
  fallback, never crash; MCD failure → median distance; < 2 entities →
  ValueError → peer fallback.
- Human-in-the-loop boundary: humans decide whether an outlier warrants
  review; the ensemble may not open, close, or prioritise cases alone.

## 2. Topic model (UMAP+HDBSCAN / NMF fallback)

- Purpose: discover new supervision-relevant note patterns beyond named
  signals; exploratory, not dispositive.
- Architecture: FULL `UMAP(n_components=5) → HDBSCAN → c-TF-IDF` labels when
  umap-learn+hdbscan installed; otherwise LITE `NMF(n_components=10,
  random_state=seed)` over TF-IDF. Code: `src/satsa/ml/topic_model.py`.
- Training data provenance and hash: investigation notes from
  `data/synthetic/*/investigations.parquet`; hash recorded when registered.
- Hardware requirements: CPU-only; 2 GB RAM minimum (NMF path); FULL path
  needs 4 GB for UMAP on >5k notes.
- Offline training procedure: 1) collect notes; 2) `discover_topics(notes,
  seed)`; 3) inspect `top_terms`, `entity_distribution`,
  `concentration_ratio`.
- Inference procedure: same call; deterministic for same input + seed.
- Update mechanism: manual, offline, versioned.
- Explainability controls: `top_terms`, `example_note_ids`,
  `entity_distribution` per topic; concentration flag with threshold from
  `thresholds.yaml` (`topic_concentration_threshold`, default 0.60).
- Auditability controls: seed logged; backend (`full`/`lite`) recorded.
- Known limitations: quality degrades below ~500 notes (R3); short
  boilerplate notes inflate similarity; minimum corpus size 500 documented
  here.
- Failure modes and mitigations: missing optional deps → LITE fallback;
  < 2 docs → single trivial topic; empty input → zero topics, no crash.
- Human-in-the-loop boundary: humans decide whether a topic is meaningful;
  concentrated topics are observations, never accusations.

## 3. Risk calibrator (isotonic / Platt)

- Purpose: map composite 0–1 scores to a 0–100 supervisory-risk scale.
- Architecture: isotonic regression if n >= 50 else Platt (logistic
  regression). Code: `src/satsa/ml/calibration.py`; artefact
  `models/artifacts/risk_calibrator.joblib`.
- Training data provenance and hash: `data/synthetic/ground_truth.parquet`
  (`expected_flag` labels); SHA-256 over sorted CSV stored as
  `training_data_hash`; Brier score + reliability curve persisted.
- Hardware requirements: CPU-only; < 1 GB RAM.
- Offline training procedure: 1) assemble (score, label) pairs;
  2) `train_calibrator(scores, labels, feature_list)`; 3) artefact +
  `models/registry.json` entry written offline.
- Inference procedure: `calibrate_scores(scores, feature_list)`; drift →
  ERROR log + `calibrated: false` with raw*100 (never crash, never silent).
- Update mechanism: manual, offline, versioned via `ModelRegistry`.
- Explainability controls: method (`isotonic`/`platt`), Brier, reliability
  bins exposed.
- Auditability controls: `training_data_hash`, `feature_list`, file SHA-256
  in registry; `verify_hashes()` checks artefacts.
- Known limitations: synthetic-label quality bounds accuracy (R2); small-n
  Platt fits are coarse; uncalibrated outputs must be labelled as such.
- Failure modes and mitigations: no labels → `calibrated: false`, no crash;
  corrupt artefact → same; drift → ERROR + uncalibrated.
- Human-in-the-loop boundary: humans interpret the 0–100 scale; the number
  never auto-escalates or closes a case.

## 4. Local LLM (GGUF / Ollama localhost)

- Purpose: draft plain-language narratives from signal evidence; template
  mode is the default and always available.
- Architecture: (a) llama-cpp-python GGUF from `models/llm/` path in
  `configs/llm.yaml`; (b) Ollama HTTP to hardcoded
  `http://127.0.0.1:11434` only. Code: `src/satsa/ai/local_llm.py`.
- Training data provenance and hash: GGUF obtained separately via
  `scripts/fetch_models_offline.sh` (documents exact name + SHA-256);
  recorded in `models/registry.json` when registered. Default install ships
  no GGUF (R1).
- Hardware requirements: template mode any CPU / 1 GB RAM; GGUF needs 8 GB
  RAM minimum CPU inference; Ollama needs its own daemon on loopback.
- Offline training procedure: no training in SATSA; GGUF is a frozen
  artefact verified by hash before placement in `models/llm/`.
- Inference procedure: `generate(prompt, config)` tries GGUF then Ollama;
  fixed seed, `temperature=0.1`, `top_p=0.9`, `max_tokens=512`,
  `timeout_seconds` (default 30); output always passes `guardrails.py`.
- Update mechanism: manual, offline, versioned — replace GGUF + registry
  entry; never auto-download (fetch script runs only on connected machine).
- Explainability controls: prompts in `src/satsa/ai/prompts/`; every output
  labelled `generated_by`; guardrail rejections logged.
- Auditability controls: prompt, evidence ids, seed and backend logged;
  `verify_airgap.sh` asserts no non-localhost calls.
- Known limitations: `max_tokens=512` bounds rationale length (A3);
  all-MiniLM-L6-v2 sentence model is 22M params CPU-friendly (A2); without
  GGUF/Ollama the system degrades gracefully to templates.
- Failure modes and mitigations: no backend → `LLMUnavailable` → template;
  timeout → `LLMUnavailable` → template; non-localhost URL → rejected
  before any HTTP; guardrail double-reject → template fallback.
- Human-in-the-loop boundary: narratives are drafts with a
  `suggested_review_focus` question; humans make all supervisory decisions;
  prescriptive/disciplinary text is rejected by guardrails.

## HOW TO RUN (air-gap)

```bash
# Connected machine, then transfer models/ :
bash scripts/fetch_models_offline.sh

# Air-gapped machine (LLM disabled default):
python -m satsa.ai.narrate --entity cse_bravo
python -m satsa.ai.narrate --all
bash scripts/verify_airgap.sh
```
