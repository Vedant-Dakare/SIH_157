import type {
  AuditEntry,
  Counterfactual,
  Entity,
  EntityDetail,
  EvidenceBundle,
  Finding,
  QueueItem,
  RunManifest,
} from '@/types/api';

export const RUN_ID = 'demo';
export const GENERATED_AT = '2024-06-01T12:00:00Z';

export const mockEntities: Entity[] = [
  { entity_id: 'cse_alpha', band: 'HIGH', sector: 'finance', overall_score: 82.4, confidence: 'HIGH' },
  { entity_id: 'cse_bravo', band: 'ELEVATED', sector: 'finance', overall_score: 61.0, confidence: 'MEDIUM' },
  { entity_id: 'cse_charlie', band: 'MODERATE', sector: 'healthcare', overall_score: 33.7, confidence: 'MEDIUM' },
  { entity_id: 'cse_delta', band: 'LOW', sector: 'technology', overall_score: 4.2, confidence: 'HIGH' },
  { entity_id: 'cse_echo', band: 'LOW', sector: 'technology', overall_score: 0.0, confidence: 'LOW' },
];

export const mockEntityDetail: EntityDetail = {
  entity_id: 'cse_alpha',
  run_id: RUN_ID,
  window: '2024-05-03..2024-05-31',
  domain_scores: { operational_discipline: 78.5, governance: 41.2 },
  domain_contributions: { operational_discipline: 11.8, governance: 4.1 },
  domain_members: { operational_discipline: ['EG-001'], governance: [] },
  domain_weights: { operational_discipline: 0.15, governance: 0.1 },
  overall_score: 82.4,
  calibrated_score: 79.9,
  band: 'HIGH',
  confidence: 'HIGH',
  confidence_reason: 'Data completeness 0.97; samples adequate.',
  n_signals_flagged: 2,
  flagged_signals: ['EG-001', 'EG-006'],
  data_completeness: 0.97,
  capped_by_completeness: false,
  calibrated: true,
  computed_at: GENERATED_AT,
  sector: 'finance',
};

function finding(overrides: Partial<Finding> & { finding_id: string; signal_id: string }): Finding {
  return {
    entity_id: 'cse_alpha',
    observed: 1.0,
    threshold: 0.2,
    severity: 'HIGH',
    confidence: 'MEDIUM',
    score: 1.0,
    band: 'HIGH',
    window: '2024-05-03..2024-05-31',
    label: 'Premature closure',
    plain_language: 'Critical cases closed implausibly fast.',
    peer_baseline: { median: 0.1, p95: 0.4, n: 12, cohort_id: 'FIN_LARGE_EXTERNAL' },
    supporting_rows: [{ case_id: 'c1' }],
    counter_rows: [],
    counter_absent_reason: 'no counter-examples in window',
    evidence_id: 'e1e2e3e4',
    audit_ref: 'seq 3',
    is_flagged: true,
    confidence_reason: 'Adequate samples.',
    ...overrides,
  };
}

export const mockFindings: Finding[] = [
  finding({ finding_id: 'f-eg1', signal_id: 'EG-001' }),
  finding({ finding_id: 'f-eg2', signal_id: 'EG-006', severity: 'MEDIUM' }),
  finding({ finding_id: 'f-eg3', signal_id: 'EG-010' }),
  finding({ finding_id: 'f-eg4', signal_id: 'EG-003', entity_id: 'cse_bravo' }),
  finding({ finding_id: 'f-ns1', signal_id: 'NS-001' }),
  finding({ finding_id: 'f-ns2', signal_id: 'NS-005', severity: 'LOW', confidence: 'LOW' }),
  finding({ finding_id: 'f-ns3', signal_id: 'NS-011', severity: 'LOW', confidence: 'LOW' }),
  finding({ finding_id: 'f-comp1', signal_id: 'COMP-001' }),
  finding({ finding_id: 'f-peer1', signal_id: 'PEER-001', label: 'Peer divergence' }),
  finding({ finding_id: 'f-anom1', signal_id: 'ANOM-001', label: 'Anomaly outlier' }),
];

export const mockEvidence: EvidenceBundle = {
  finding_id: 'f-eg1',
  evidence_id: 'e1e2e3e4',
  supporting_rows: [{ case_id: 'c1', severity: 'CRITICAL' }, { case_id: 'c2', severity: 'CRITICAL' }],
  counter_rows: [{ case_id: 'c9', note: 'normal dwell' }],
  counter_rows_absent_reason: '',
  cohort_comparison: { median: 0.1 },
  retrieved_at: GENERATED_AT,
};

export const mockCounterfactual: Counterfactual = {
  finding_id: 'f-eg1',
  computable: true,
  threshold_value: 0.2,
  required_value: 0.19,
  metric_name: 'premature_rate',
  plain_language: 'If premature_rate had fallen to 0.19, EG-001 would not fire.',
  reason_if_null: '',
};

export const mockQueue: QueueItem[] = [
  {
    rank: 1, entity_id: 'cse_alpha', priority: 33.5, risk_score: 82.4, band: 'HIGH',
    confidence: 'HIGH', focus_area: 'operational_discipline', signal_ids: ['EG-001', 'EG-006'],
    expected_review_minutes: 20, sample_alert_ids: ['a1'], sample_case_ids: ['c1'],
    novelty_weight: 1.0, coverage_gap_weight: 1.25,
  },
  {
    rank: 2, entity_id: 'cse_bravo', priority: 12.8, risk_score: 61.0, band: 'ELEVATED',
    confidence: 'MEDIUM', focus_area: 'escalation_integrity', signal_ids: ['EG-003'],
    expected_review_minutes: 10, sample_alert_ids: ['a2'], sample_case_ids: ['c2'],
    novelty_weight: 1.0, coverage_gap_weight: 1.25,
  },
  {
    rank: 3, entity_id: 'cse_charlie', priority: 8.4, risk_score: 33.7, band: 'MODERATE',
    confidence: 'MEDIUM', focus_area: 'governance', signal_ids: ['EG-007'],
    expected_review_minutes: 10, sample_alert_ids: [], sample_case_ids: ['c3'],
    novelty_weight: 0.4, coverage_gap_weight: 1.0,
  },
  {
    rank: 4, entity_id: 'cse_delta', priority: 2.1, risk_score: 4.2, band: 'LOW',
    confidence: 'HIGH', focus_area: 'investigation_quality', signal_ids: [],
    expected_review_minutes: 1, sample_alert_ids: [], sample_case_ids: [],
    novelty_weight: 1.0, coverage_gap_weight: 1.0,
  },
  {
    rank: 5, entity_id: 'cse_echo', priority: 0.0, risk_score: 0.0, band: 'LOW',
    confidence: 'LOW', focus_area: '', signal_ids: [],
    expected_review_minutes: 1, sample_alert_ids: [], sample_case_ids: [],
    novelty_weight: 1.0, coverage_gap_weight: 1.0,
  },
];

let hashCounter = 0;
function chainedHash(): string {
  hashCounter += 1;
  return `h${hashCounter}`.padEnd(64, '0');
}

export const mockAuditEntries: AuditEntry[] = Array.from({ length: 10 }, (_, index) => ({
  seq: index,
  run_id: RUN_ID,
  ts: GENERATED_AT,
  event_type: index === 0 ? 'RUN_START' : 'FINDING',
  payload: { finding_id: `f-${index}` },
  prev_hash: index === 0 ? '0'.repeat(64) : chainedHash(),
  entry_hash: chainedHash(),
  signature: null,
}));

export const mockManifest: RunManifest = {
  run_id: RUN_ID,
  created_at: GENERATED_AT,
  window_start: '2024-05-03',
  window_end: '2024-05-31',
  entity_count: 5,
  finding_count: 10,
  first_seq: 0,
  last_seq: 9,
  entry_count: 10,
  merkle_root: 'm'.repeat(64),
  ledger_hashes: [],
  thresholds_hash: 't'.repeat(64),
  signals_version: 'phase2-registry',
  settings_snapshot: {},
  signature: 's'.repeat(64),
};
