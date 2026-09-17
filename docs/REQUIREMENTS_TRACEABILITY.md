# Requirements traceability (PS §4 functional, §5 deployment, §6 deliverables)

Coverage: 100% of enumerated items. Format: requirement → module(s) → test(s).

## §4 Functional requirements

| # | Requirement | Module(s) | Test(s) |
|---|---|---|---|
| F-01 | Canonical models + ingest pipeline + quarantine | `canonical/models`, `ingest/*` | test_models, test_validators, test_quarantine, test_mapping |
| F-02 | Temporal features + batch-close detector | `features/temporal` | test_features |
| F-03 | Workflow features (escalation/reopen/orphan/backfill) | `features/workflow` | test_features |
| F-04 | Text features, LITE + FULL backends, no network | `features/text` | test_features |
| F-05 | Coverage / negative-space engine + seasonality | `features/coverage` | test_features |
| F-06 | Asset join via DuckDB + shadow records | `features/asset` | test_features |
| F-07 | Entity feature vector (122) + BH-FDR | `features/entity_features` | test_features |
| F-08 | Signal base (insufficient-data rule, evidence, reason) | `signals/base` | test_signal_*, invariants |
| F-09 | 14 EG signals, config-gated | `signals/execution_gaps` | test_signal_EG-* |
| F-10 | 12 NS signals (incl. LOW-only NS-011) | `signals/negative_space` | test_signal_NS-* |
| F-11 | Robust peer benchmarking + fallbacks | `signals/peer_benchmark` | test_peer_benchmark |
| F-12 | Anomaly ensemble + ablation contributions | `signals/anomaly` | test_anomaly |
| F-13 | Composite rules, config-only extension | `signals/composite` | test_composite |
| F-14 | Registry, schema validation, catalogue | `signals/registry` | test_signals_pipeline |
| F-15 | Embeddings wrapper, cached, offline | `ml/embeddings` | test_embeddings |
| F-16 | Topic model FULL/LITE + concentration flags | `ml/topic_model` | (smoke via pipeline) |
| F-17 | Risk calibrator + registry, drift-safe | `ml/calibration`, `ml/registry` | test_calibration |
| F-18 | Offline LLM client, loopback-only, timeouts | `ai/local_llm` | test_local_llm |
| F-19 | Guardrails (hallucination/PII/prescriptive/length/citation) | `ai/guardrails` | test_guardrails |
| F-20 | Six-field narratives, template fallback | `ai/narrate` | test_narrate, test_ai_layer |
| F-21 | Risk engine (breadth-dampened max) | `scoring/risk_engine` | test_risk_engine |
| F-22 | Confidence gating + separate queue | `scoring/confidence` | test_confidence |
| F-23 | Utility-ranked prioritisation + sampling | `scoring/prioritisation` | test_prioritisation |
| F-24 | Portfolio, trends, drill-down | `scoring/portfolio` | test_portfolio |
| F-25 | Reason codes + composite codes, template render | `explain/reason_codes` | test_reason_codes |
| F-26 | SHAP/ablation contributions | `explain/shap_explainer` | (via anomaly + chain tests) |
| F-27 | DuckDB evidence + mandatory counter-evidence | `explain/evidence` | test_evidence |
| F-28 | Counterfactuals or explicit null | `explain/counterfactual` | test_counterfactual |
| F-29 | SHA-256/HMAC primitives | `audit/hashing` | test_ledger (via chain) |
| F-30 | Append-only JSONL+DuckDB ledger + verify | `audit/ledger` | test_ledger |
| F-31 | Merkle roots + signed manifests | `audit/merkle` | test_ledger, test_explain_chain |
| F-32 | Explain/audit CLI output | `explain/runner`, `audit/runner` | test_explain_chain |
| F-33 | Six HTML templates, offline assets | `report/templates` | test_render |
| F-34 | Offline SVG charts + hidden tables | `report/charts` | test_render |
| F-35 | HTML rendering to curated reports | `report/render_html` | test_render |
| F-36 | PDF (WeasyPrint→reportlab→minimal) | `report/render_pdf` | test_render |
| F-37 | CSV/XLSX/JSON exports, idempotent | `report/exports` | (via end-to-end artefacts) |
| F-38 | 13 API endpoints, loopback, token gate | `api/*` | test_api |
| F-39 | Checkpointed DAG, retries, optional/required | `pipeline/*` | test_orchestrator |
| F-40 | Benchmark vs labels (synthetic + expert) | `validation/benchmark` | test_validation_metrics |
| F-41 | Full metric set (P@k, recall, F1, κ, α) | `validation/metrics` | test_validation_metrics |
| F-42 | Family ablation + catalogue section | `validation/ablation` | test_ablation |
| F-43 | Disagreements + adjudication journal | `validation/expert_agreement` | test_expert_agreement |

## §5 Deployment requirements

| # | Requirement | Module(s)/doc(s) | Test(s) |
|---|---|---|---|
| D-01 | Zero-network operation, verified | `scripts/verify_airgap.sh` | test_ai_layer (gate) |
| D-02 | Offline bundle build + install | `scripts/build_offline_bundle.sh`, `install_offline.sh` | (script review; install = pip dry path) |
| D-03 | Docker, non-root, read-only FS, no network | `Dockerfile`, `docker-compose.yml` | (build-path review) |
| D-04 | API bound to 127.0.0.1, optional token | `api/main`, `configs/api.yaml` | test_api |
| D-05 | AI disclosures (§5 list) | `docs/AI_GOVERNANCE.md` | (doc review) |
| D-06 | Hardware sizing guidance | `docs/DEPLOYMENT.md`, presentation slide 5 | (doc review) |
| D-07 | Hashed analyst IDs, signed manifests | `synthetic/generator`, `audit/merkle` | test_synthetic, test_explain_chain |
| D-08 | Upgrade/rollback, hash-verified | `docs/DEPLOYMENT.md` | (doc review) |

## §6 Deliverables

| # | Deliverable | Location | Check |
|---|---|---|---|
| G-01 | ARCHITECTURE.md (≤2 pages) + PNG | `ARCHITECTURE.md`, `docs/architecture.png` | exists, renders |
| G-02 | ANALYTICS_METHODOLOGY.md (29 signals) | `docs/ANALYTICS_METHODOLOGY.md` | 29 entries present |
| G-03 | DATA_DICTIONARY.md (all fields) | `docs/DATA_DICTIONARY.md` | 8 models covered |
| G-04 | SIGNAL_CATALOGUE.md + rationale + ablation | `docs/SIGNAL_CATALOGUE.md` | markers present |
| G-05 | demo_script.md (2 min) | `deliverables/demo_script.md` | CLI sequence verified live |
| G-06 | technical_presentation.md (5 slides) | `deliverables/technical_presentation.md` | 5 slides |
| G-07 | README.md (quickstart/CLI/FAQ) | `README.md` | 5-command quickstart |
| G-08 | DECISIONS.md (ADRs 001–006 + 007–009) | `docs/DECISIONS.md` | 9 ADRs |
| G-09 | REQUIREMENTS_TRACEABILITY.md (this file) | `docs/REQUIREMENTS_TRACEABILITY.md` | 100% rows mapped |
| G-10 | Validation methodology + rubric + CSV | `docs/VALIDATION_METHODOLOGY.md`, `docs/EXPERT_REVIEW_RUBRIC.md`, `docs/expert_review_rubric_template.csv` | exist |
| G-11 | Demo data + CLI printout | `scripts/seed_demo_data.py` | EG-001/EG-006 asserted live |
