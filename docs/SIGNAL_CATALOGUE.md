# SATSA Signal Catalogue

Auto-generated from the signal registry. Do not edit by hand.

Total enabled signals: 26
Composite rules: 3

| ID | Name | Family | Severity | Required features |
|----|------|--------|----------|-------------------|
| EG-001 | Premature closure | execution_gap | HIGH | premature_rate, case_count |
| EG-002 | Reopen churn | execution_gap | MEDIUM | reopen_rate, case_count |
| EG-003 | Escalation bypass | execution_gap | HIGH | bypass_rate, case_count |
| EG-004 | Severity downgrade bias | execution_gap | MEDIUM | alert_share_HIGH, case_share_HIGH |
| EG-005 | SLA breach backlog | execution_gap | MEDIUM | sla_breach_rate, case_count |
| EG-006 | Bulk close burst | execution_gap | HIGH | case_count, alert_count |
| EG-007 | Metric gaming composite pattern | execution_gap | HIGH | case_count, reopen_rate, escalation_rate |
| EG-008 | After-hours closure rush | execution_gap | MEDIUM | night_fraction, case_count |
| EG-009 | Backfill documentation | execution_gap | MEDIUM | backfill_rate, alert_count |
| EG-010 | Templated investigation notes | execution_gap | HIGH | template_similarity, copy_paste_ratio |
| EG-011 | Duplicate chain depth | execution_gap | MEDIUM | duplicate_chain_depth, case_count |
| EG-012 | Orphan case rate | execution_gap | MEDIUM | orphan_case_rate, case_count |
| EG-013 | Suspiciously perfect SLA | execution_gap | MEDIUM | sla_breach_rate, lat_case_duration_median |
| EG-014 | Escalation to nowhere | execution_gap | MEDIUM | escalation_rate, case_count |
| NS-001 | Critical coverage gap | negative_space | HIGH | telemetry_gap_ratio, asset_count |
| NS-002 | Telemetry silence streak | negative_space | MEDIUM | silence_max, asset_count |
| NS-003 | Category absence vs peers | negative_space | MEDIUM | category_coverage, alert_count |
| NS-004 | MITRE coverage absence | negative_space | MEDIUM | mitre_coverage, alert_count |
| NS-005 | Expected core source absent | negative_space | MEDIUM | expected_absent_count, asset_count |
| NS-006 | Perimeter blind spot | negative_space | MEDIUM | internet_facing_alert_rate, asset_count |
| NS-007 | Detrended low activity | negative_space | MEDIUM | alerts_per_day, alert_count |
| NS-008 | Internet-facing blind spot | negative_space | MEDIUM | internet_facing_alert_rate, asset_count |
| NS-009 | Telemetry gap spike | negative_space | MEDIUM | telemetry_gap_ratio, asset_count |
| NS-010 | Silent critical estate | negative_space | HIGH | critical_asset_coverage, asset_count |
| NS-011 | Absence of out-of-hours activity | negative_space | LOW | night_fraction, case_count |
| NS-012 | Feed truncation | negative_space | HIGH | alert_count, alerts_per_day |

## Composite rules

- **COMP-001** (Superficial compliance): `(EG-003 AND EG-013) AND (NS-005 OR NS-006)`
- **COMP-002** (Silent critical estate): `NS-001 AND NS-010 AND asset_criticality_band=HIGH`
- **COMP-003** (Metric theatre): `EG-007 AND EG-010 AND EG-006`

Feature schema columns: 122

<!-- RATIONALE-START -->
## Hand-written signal rationales (Phase 8)

Formula/threshold details live in `docs/ANALYTICS_METHODOLOGY.md` Phase 8
reference. Family ablation contributions (Phase 7, synthetic ground truth):
execution_gap 87.5%, negative_space 12.5%, composite 0.0% (never fires alone
on synthetic data; fires in production compositions).

- EG-001: rushed triage on criticals; expected S2; FP from legitimately
  fast true-positive closures during incidents.
- EG-002: churned reopens; expected S6; FP from complex cases needing
  genuine multi-pass work.
- EG-003: bypassed escalation; expected S8; FP from empowered T1 teams
  with documented authority.
- EG-004: downgrade bias; expected S6; FP from noisy vendor severities.
- EG-005: SLA backlog; expected S5; FP from staffing gaps, not negligence.
- EG-006: batch closures; expected S7; FP from sanctioned bulk actions
  (e.g. false-positive storms).
- EG-007: metric gaming pattern; no single scenario; FP when closure,
  recurrence and tagging move together legitimately.
- EG-008: night-shift rush; expected S9; FP from legitimate follow-the-sun
  operations.
- EG-009: retroactive documentation; FP from delayed feed ingestion.
- EG-010: templated notes; expected S4; FP from genuinely similar incidents.
- EG-011: duplicate chains; FP from noisy deduplication tooling.
- EG-012: orphan cases; FP from manual case creation without linkage.
- EG-013: perfect SLA; FP from small samples (gated by min_cases 10).
- EG-014: dead escalations; FP from tooling that drops accept events.
- NS-001: dark critical assets; expected S3; FP from unlisted compensating
  controls.
- NS-002: silent assets; FP from decommissioned-but-listed hosts.
- NS-003: missing categories; FP from specialised estates with narrow
  threat surface.
- NS-004: MITRE gaps; FP from asset profiles that genuinely lack exposure.
- NS-005: absent core sources; FP from renamed collectors.
- NS-006: perimeter blindness; FP from cloud-native perimeters.
- NS-007: detrended lull; FP from holidays (needs 12-month history).
- NS-008: quiet facing assets; FP from effective prevention.
- NS-009: gap spikes; FP from onboarding collectors mid-window.
- NS-010: silent critical estate; FP from segmented estates.
- NS-011: no night activity; observation only, never accusation.
- NS-012: truncated feed; FP from planned maintenance (registry-noted).
- COMP-001/002/003: compositional patterns; FP when members coincide by
  chance — dampened severity accounts for this.
<!-- RATIONALE-END -->

<!-- ABLATION-START -->
## Signal-family ablation (validation)

Recall contribution of each signal family, measured by disabling the
family and re-scoring against ground truth. Sorted by contribution.

| family | signals disabled | baseline | ablated | drop | contribution % |
|--------|------------------|----------|---------|------|----------------|
| execution_gap | 9 | 0.800 | 0.100 | 0.700 | 87.5 |
| negative_space | 6 | 0.800 | 0.700 | 0.100 | 12.5 |
| composite | 0 | 0.800 | 0.800 | 0.000 | 0.0 |
<!-- ABLATION-END -->
