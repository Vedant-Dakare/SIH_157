# SATSA Analytics Methodology

Phase 2 feature engineering and signal detection. All cutoffs live in
`configs/thresholds.yaml` (with documented code-side defaults when a key is
absent); all signals are gated by `configs/signals.yaml` (unknown ids default
to enabled). Phase 0+1 files were not modified; Phase 2 defaults ship in
`src/satsa/signals/_config.py`.

## Entity feature vector (122 features, locked for Phase 3)

Groups: Volume (per-enrollment-day normalised counts), Latency (temporal
means/medians/p90), Quality (reopen/backfill/duplicate/orphan rates),
Coverage (gap ratios, silence maxima, category/MITRE scores), Escalation
(rates, bypass, tier dwell), Textual (template similarity, richness,
copy-paste, placeholder), Peer-relative (robust z vs cohort), Trend
(second-half minus first-half deltas; 0.0 under single-window history),
severity/category shares, raw p-values plus BH-FDR adjusted p-values.

Survivorship: entities onboarded mid-window normalise volume by enrollment
days, never raw totals. Missing data policy: unwitnessed metrics default to
0.0; sample-size-aware signals gate on `signal_min_n` instead of guessing.

## Multiple-comparison correction

Every peer p-value uses the two-sided normal tail of the modified z-score.
Benjamini-Hochberg FDR is applied across the twelve peer metrics per entity
(`src/satsa/features/entity_features.py::benjamini_hochberg`); both raw
(`p_*`) and adjusted (`padj_*`) values are exported in the feature vector.

## Peer benchmarking

`modified_z = 0.6745 * (x - median) / MAD`, with fallbacks MAD == 0 to IQR
(`0.7413 * (x - median) / IQR`), IQR == 0 to range, and range == 0 to skip
with WARNING. Cohorts come from `peer_cohorts.yaml`
(sector + size + internet exposure); cohort_n < 5 falls back to global stats
with a confidence penalty (0.20, or 0.40 for single-member cohorts) and sets
`cohort_too_small`. Note: shipped synthetic cohorts have n = 2, so production
runs currently exercise the global-fallback path by design.

## Seasonality (NS-007)

Before flagging low activity, daily counts are detrended with a 12-week
rolling-median baseline (`detrend_low_activity`); short histories fall back to
the expanding median, and inputs under 14 day-buckets return
insufficient_data. Reliable holiday/seasonal detrending needs at least 12
months of history; single-window synthetic runs therefore report
insufficient_data rather than flagging.

## Anomaly ensemble

IsolationForest, ECOD, COPOD, HBOS, LOF (PyOD) plus robust Mahalanobis
(MinCovDet with median-distance fallback), ensembled by mean rank. Each model
fit is fault-tolerant (zero-vector fallback) so degenerate matrices never
crash scoring. Contributions come from median-ablation per feature and are
stored for Phase 3 SHAP. Anomaly output is never a standalone finding: every
entity pairs with a named rule-based signal (`paired_signal_id`). Single
entities (< 2) raise so callers fall back to peer benchmarks (R2).

## Composites and confidence

COMP-001/002/003 evaluate serialisable boolean trees; severity is the
dampened maximum of member severities; confidence inherits the weakest firing
member (conservative by design, R4). New composites are addable via the
`composites` key in signals.yaml with no code changes.

## HOW TO RUN (Phase 2 entry points)

`cli.py` and `Makefile` are Phase 0+1 files and were intentionally left
untouched. Equivalents:

- Single CSE: `python -m satsa.signals.runner --cse-id cse_bravo`
- All CSEs: `python -m satsa.signals.runner --all`
- Catalogue: `python -m satsa.signals.runner --catalogue`
- Suggested Makefile additions (not applied):
  `features: python -m satsa.signals.runner --all`
  `signals: python -m satsa.signals.runner --all`

## Phase 8 signal reference (all 29)

Conventions: every rate is per-entity per-window; every signal gates on
`signal_min_n` (default 5) with `insufficient_data` instead of guessing;
peer comparison uses modified z-scores vs the sector/size cohort with
global fallback. Threshold keys live in `configs/thresholds.yaml`
(code defaults shown).

### Execution gaps (EG-001..EG-014)

- EG-001 Premature closure (HIGH): rationale — critical cases closed
  within minutes suggest cursory triage; formula — fraction of closed
  CRITICAL cases with dwell < `premature_close_minutes` (5);
  threshold `premature_rate_threshold` 0.20; peer — cohort rate quartiles.
- EG-002 Reopen churn (MEDIUM): repeated reopens imply unresolved root
  cause; fraction of cases with `reopen_count >= reopen_churn_min_reopens`
  (2); threshold `reopen_rate_threshold` 0.15.
- EG-003 Escalation bypass (HIGH): critical cases closed with no
  escalation; bypassed/total-critical; threshold
  `escalation_bypass_rate_threshold` 0.90.
- EG-004 Severity downgrade bias (MEDIUM): systematic alert→case
  downgrades hide exposure; mean alert rank minus mean case rank;
  threshold `severity_mismatch_rate_threshold` 0.25.
- EG-005 SLA breach backlog (MEDIUM): cases open beyond
  `sla_breach_hours` (72); breach fraction; threshold
  `sla_breach_rate_threshold` 0.30.
- EG-006 Bulk close burst (HIGH): one analyst closing many cases with
  identical dispositions in a sliding 60 s window suggests batch
  processing; largest burst size; threshold `bulk_close_min_count` 50.
- EG-007 Metric gaming (HIGH): high closure AND high recurrence AND low
  root-cause tagging together suggest metric optimisation; all three
  quartile conditions must hold simultaneously (config-gated).
- EG-008 After-hours closure rush (MEDIUM): closures concentrated
  22:00–06:00 suggest rushed or unsupervised work; night fraction;
  threshold `eg008_min_fraction` 0.50.
- EG-009 Backfill documentation (MEDIUM): ingest far after event suggests
  retroactive records; backfilled/alerts; threshold
  `backfill_rate_threshold` 0.10.
- EG-010 Templated notes (HIGH): near-identical investigation notes
  suggest copy-paste triage; mean pairwise TF-IDF cosine;
  threshold `template_tfidf_threshold` 0.85 with `template_min_notes` 5.
- EG-011 Duplicate chains (MEDIUM): deep `is_duplicate_of` chains or high
  DUPLICATE dispositions suggest queue hygiene failure; depth/rate;
  threshold `duplicate_rate_threshold` 0.10.
- EG-012 Orphan cases (MEDIUM): cases with no linked alerts lack
  evidence; orphan/total; threshold `orphan_case_rate_threshold` 0.30.
- EG-013 Perfect SLA (MEDIUM): 100% SLA-met with ~zero dwell variance
  suggests fabricated timestamps; fires when SLA-met ≥
  `eg013_sla_met_pct` (0.99) AND dwell CV < `eg013_cv_epsilon` (0.05),
  minimum `eg013_min_cases` (10).
- EG-014 Escalation to nowhere (MEDIUM): escalation raised but never
  accepted before closure; orphaned/total escalations; threshold
  `escalation_nowhere_rate_threshold` 0.50.

### Negative space (NS-001..NS-012)

- NS-001 Critical coverage gap (HIGH): critical assets lacking expected
  telemetry; gap ratio; threshold `telemetry_gap_ratio_threshold` 0.10.
- NS-002 Silence streak (MEDIUM): assets quiet beyond
  `silence_streak_days_threshold` (7) days.
- NS-003 Category absence (MEDIUM): missing alert categories vs peers;
  modified-z of missing count; threshold `category_absence_z_threshold` 2.0.
- NS-004 MITRE absence (MEDIUM): expected tactics never observed given
  asset profile; low-coverage bound 0.34.
- NS-005 Expected source absent (MEDIUM): any expected asset-source pair
  with zero evidence; threshold `coverage_gap_min_unmonitored_assets` 1.
- NS-006 Perimeter blind spot (MEDIUM): internet-facing assets missing
  firewall/IDS sources; same count threshold.
- NS-007 Detrended low activity (MEDIUM): residual activity below the
  detrended bound after 12-week rolling-median seasonal detrending;
  inputs under 14 day-buckets are insufficient, not flagged.
- NS-008 Internet-facing blind spot (MEDIUM): facing assets drawing zero
  alerts; count threshold 2.0.
- NS-009 Telemetry gap spike (MEDIUM): gap ratio vs threshold 0.10.
- NS-010 Silent critical estate (HIGH): fraction of critical assets with
  zero alerts; threshold 0.20.
- NS-011 No after-hours activity (LOW, always LOW confidence): near-zero
  out-of-hours share presented as observation with peer context, never
  accusation; bound `ns011_max_after_hours_fraction` 0.05.
- NS-012 Feed truncation (HIGH): current-window volume drop beyond
  `ns012_drop_pct` (0.50) vs trailing `ns012_trailing_windows` (4), unless
  a registry note explains it.

### Composites (COMP-001..003)

- COMP-001 Superficial compliance: EG-003 AND EG-013 AND (NS-005 OR NS-006).
- COMP-002 Silent critical estate: NS-001 AND NS-010 AND HIGH band.
- COMP-003 Metric theatre: EG-007 AND EG-010 AND EG-006.
Severity is the dampened member maximum; confidence inherits the weakest
firing member; new rules are config-only additions.

## Aggregation rules (rationale)

Domain score takes the member maximum (the worst credible signal sets the
ceiling) multiplied by breadth dampening `1 − exp(−k·n)` (corroboration
amplifies without double counting); overall is the weight-sum over the
seven domains (ADR-004). Alternatives (mean/max/sum) were rejected for
washing out, overweighting, or unboundedness respectively.

## Confidence model

`data_completeness` blends null fraction, quarantine rate (double
weighted), UNKNOWN-severity rate and label confidence. Below 0.6 the
entity leaves the ranking for a separate queue (ADR-005). HIGH needs
completeness ≥ 0.9, ≥ 90% adequately sampled signals, cohort adequacy and
≤ 5% feature missingness; sample-size shortfalls always resolve to
`insufficient_data`, never to imputed flags.

## Peer cohort design

Cohorts group sector/size/internet-exposure peers; MAD-based modified
z-scores resist outliers where standard deviation would inflate; minimum
cohort n = 5 with global fallback plus confidence penalty below it;
MAD = 0 falls back IQR → range → skip-with-warning.

## Multiple-comparison correction

Twelve peer metrics per entity each yield a normal-tail p-value from the
modified z-score; Benjamini-Hochberg FDR controls the false-discovery
rate across the family, exporting raw (`p_*`) and adjusted (`padj_*`)
values side by side.

## Seasonality detrending and limits

NS-007 detrends daily counts with a 12-week rolling-median baseline
(expanding-median fallback on short histories). Reliable holiday/seasonal
separation needs ≥ 12 months of history; single-window synthetic runs
report insufficient rather than flag.

## Known limitations and mitigations

Synthetic cohorts of n = 2 exercise the global-fallback path by design;
anomaly output never stands alone (`paired_signal_id` required);
calibration quality tracks label quality; breadth parameter `k` needs
production tuning; single-entity runs disable the anomaly ensemble.
