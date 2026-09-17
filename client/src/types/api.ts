import { z } from 'zod';

/** Thrown when a response fails Zod validation. Never a bare Error. */
export class SchemaParseError extends Error {
  readonly context: string;
  readonly issues: string;

  constructor(context: string, issues: string) {
    super(`Response failed validation (${context}): ${issues}`);
    this.name = 'SchemaParseError';
    this.context = context;
    this.issues = issues;
  }
}

/** Parse wrapper: validates unknown data, throws SchemaParseError on failure. */
export function parseOrThrow<T>(schema: z.ZodType<T>, data: unknown, context: string): T {
  const result = schema.safeParse(data);
  if (!result.success) {
    throw new SchemaParseError(context, result.error.message);
  }
  return result.data;
}

// ---------------------------------------------------------------- unions

export const RiskBandSchema = z.enum(['HIGH', 'ELEVATED', 'MODERATE', 'LOW']);
export type RiskBand = z.infer<typeof RiskBandSchema>;

export const ConfidenceLevelSchema = z.enum(['HIGH', 'MEDIUM', 'LOW']);
export type ConfidenceLevel = z.infer<typeof ConfidenceLevelSchema>;

export const SignalFamilySchema = z.enum([
  'execution_gap',
  'negative_space',
  'peer',
  'anomaly',
  'composite',
]);
export type SignalFamily = z.infer<typeof SignalFamilySchema>;

export const TrendStatusSchema = z.enum(['IMPROVING', 'STABLE', 'DETERIORATING', 'INSUFFICIENT_HISTORY']);
export type TrendStatus = z.infer<typeof TrendStatusSchema>;

// ---------------------------------------------------------------- envelope

const EnvelopeSchema = z.object({
  run_id: z.string(),
  generated_at: z.string(),
});

// ---------------------------------------------------------------- health / runs

export const HealthSchema = EnvelopeSchema.extend({
  status: z.string(),
  pipeline_version: z.string(),
});
export type Health = z.infer<typeof HealthSchema>;

export const RunManifestSchema = z
  .object({
    run_id: z.string(),
    created_at: z.string(),
    window_start: z.string(),
    window_end: z.string(),
    entity_count: z.number(),
    finding_count: z.number(),
    first_seq: z.number(),
    last_seq: z.number(),
    entry_count: z.number(),
    merkle_root: z.string(),
    ledger_hashes: z.array(z.string()),
    thresholds_hash: z.string(),
    signals_version: z.string(),
    settings_snapshot: z.record(z.string(), z.unknown()),
    signature: z.string(),
  })
  .passthrough();
export type RunManifest = z.infer<typeof RunManifestSchema>;

// ---------------------------------------------------------------- entities

export const ConfidenceSchema = z.object({
  level: ConfidenceLevelSchema,
  reason: z.string(),
  data_completeness: z.number(),
  capped_by_completeness: z.boolean(),
});
export type Confidence = z.infer<typeof ConfidenceSchema>;

export const DomainScoreSchema = z.object({
  domain: z.string(),
  score: z.number(),
  contribution: z.number(),
  signals: z.array(z.string()),
});
export type DomainScore = z.infer<typeof DomainScoreSchema>;

export const EntitySchema = z.object({
  entity_id: z.string(),
  band: RiskBandSchema,
  sector: z.string(),
  overall_score: z.number(),
  confidence: ConfidenceLevelSchema,
});
export type Entity = z.infer<typeof EntitySchema>;

export const EntityDetailSchema = z
  .object({
    entity_id: z.string(),
    run_id: z.string(),
    window: z.string(),
    domain_scores: z.record(z.string(), z.number()),
    domain_contributions: z.record(z.string(), z.number()),
    domain_members: z.record(z.string(), z.array(z.string())),
    domain_weights: z.record(z.string(), z.number()),
    overall_score: z.number(),
    calibrated_score: z.number(),
    band: RiskBandSchema,
    confidence: ConfidenceLevelSchema,
    confidence_reason: z.string(),
    n_signals_flagged: z.number(),
    flagged_signals: z.array(z.string()),
    data_completeness: z.number(),
    capped_by_completeness: z.boolean(),
    calibrated: z.boolean(),
    computed_at: z.string(),
    sector: z.string().optional(),
  })
  .passthrough();
export type EntityDetail = z.infer<typeof EntityDetailSchema>;

// ---------------------------------------------------------------- findings

export const SignalResultSchema = z.object({
  finding_id: z.string(),
  entity_id: z.string(),
  signal_id: z.string(),
  value: z.number(),
  threshold: z.number(),
  score: z.number(),
  severity: z.string(),
  confidence: ConfidenceLevelSchema,
  sample_size: z.number(),
  window: z.string(),
  is_flagged: z.boolean(),
});
export type SignalResult = z.infer<typeof SignalResultSchema>;

export const ReasonCodeSchema = z.object({
  code: z.string(),
  label: z.string(),
  observed: z.union([z.number(), z.string()]),
  threshold: z.union([z.number(), z.string()]),
  comparator: z.string(),
  peer_baseline: z.object({
    median: z.number(),
    p95: z.number(),
    n: z.number(),
    cohort_id: z.string(),
  }),
  window: z.string(),
  severity: z.string(),
  confidence: ConfidenceLevelSchema,
  plain_language: z.string(),
});
export type ReasonCode = z.infer<typeof ReasonCodeSchema>;

export const FindingSchema = z
  .object({
    entity_id: z.string(),
    signal_id: z.string(),
    observed: z.union([z.number(), z.string()]),
    threshold: z.union([z.number(), z.string()]),
    severity: z.string(),
    confidence: ConfidenceLevelSchema,
    score: z.number(),
    band: RiskBandSchema,
    window: z.string(),
    label: z.string(),
    plain_language: z.string(),
    peer_baseline: z.record(z.string(), z.unknown()),
    supporting_rows: z.array(z.record(z.string(), z.unknown())),
    counter_rows: z.array(z.record(z.string(), z.unknown())),
    counter_absent_reason: z.string(),
    evidence_id: z.string(),
    audit_ref: z.string(),
    is_flagged: z.boolean(),
    confidence_reason: z.string(),
  })
  .passthrough();
export type Finding = z.infer<typeof FindingSchema>;

export const EvidenceBundleSchema = z.object({
  finding_id: z.string(),
  evidence_id: z.string(),
  supporting_rows: z.array(z.record(z.string(), z.unknown())),
  counter_rows: z.array(z.record(z.string(), z.unknown())),
  counter_rows_absent_reason: z.string(),
  cohort_comparison: z.record(z.string(), z.unknown()),
  retrieved_at: z.string(),
});
export type EvidenceBundle = z.infer<typeof EvidenceBundleSchema>;

export const EvidenceSchema = EvidenceBundleSchema;
export type Evidence = z.infer<typeof EvidenceSchema>;

export const CounterfactualSchema = z.object({
  finding_id: z.string(),
  computable: z.boolean(),
  threshold_value: z.number(),
  required_value: z.number(),
  metric_name: z.string(),
  plain_language: z.string(),
  reason_if_null: z.string(),
});
export type Counterfactual = z.infer<typeof CounterfactualSchema>;

// ---------------------------------------------------------------- queue

export const QueueItemSchema = z.object({
  rank: z.number(),
  entity_id: z.string(),
  priority: z.number(),
  risk_score: z.number(),
  band: RiskBandSchema,
  confidence: ConfidenceLevelSchema,
  focus_area: z.string(),
  signal_ids: z.array(z.string()),
  expected_review_minutes: z.number(),
  sample_alert_ids: z.array(z.string()),
  sample_case_ids: z.array(z.string()),
  novelty_weight: z.number(),
  coverage_gap_weight: z.number(),
});
export type QueueItem = z.infer<typeof QueueItemSchema>;

// ---------------------------------------------------------------- audit

export const AuditEntrySchema = z.object({
  seq: z.number(),
  run_id: z.string(),
  ts: z.string(),
  event_type: z.string(),
  payload: z.record(z.string(), z.unknown()),
  prev_hash: z.string(),
  entry_hash: z.string(),
  signature: z.union([z.string(), z.null()]),
});
export type AuditEntry = z.infer<typeof AuditEntrySchema>;

// ---------------------------------------------------------------- portfolio / validation

export const PortfolioSummarySchema = z.object({
  entity_count_by_band: z.record(RiskBandSchema, z.number()),
  top_5_entities_by_risk: z.array(z.string()),
  sector_aggregates: z.record(z.string(), z.number()),
  portfolio_trend: TrendStatusSchema,
});
export type PortfolioSummary = z.infer<typeof PortfolioSummarySchema>;

export const ValidationReportSchema = z
  .object({
    run_id: z.string(),
    generated_at: z.string(),
    label_source: z.string(),
    precision_at_k: z.record(z.string(), z.number()),
    recall_by_scenario: z.record(z.string(), z.number()),
    overall_recall: z.number(),
    overall_precision: z.number(),
    f1_by_family: z.record(z.string(), z.number()),
    cohens_kappa: z.number(),
    krippendorffs_alpha: z.number(),
    coverage_rate: z.number(),
    n_expected: z.number(),
    n_flagged: z.number(),
    n_hits: z.number(),
  })
  .passthrough();
export type ValidationReport = z.infer<typeof ValidationReportSchema>;

// ---------------------------------------------------------------- response envelopes

const ProvenanceSchema = z.object({ evidence_id: z.string() });

export const RunSchema = z.object({ run_id: z.string() });
export type Run = z.infer<typeof RunSchema>;

export const RunsResponseSchema = EnvelopeSchema.extend({ runs: z.array(z.string()) });
export type RunsResponse = z.infer<typeof RunsResponseSchema>;
export const ManifestResponseSchema = EnvelopeSchema.extend({ manifest: RunManifestSchema });
export type ManifestResponse = z.infer<typeof ManifestResponseSchema>;
export const EntitiesResponseSchema = EnvelopeSchema.extend({ entities: z.array(EntitySchema) });
export type EntitiesResponse = z.infer<typeof EntitiesResponseSchema>;
export const EntityDetailResponseSchema = EnvelopeSchema.extend({ entity: EntityDetailSchema });
export type EntityDetailResponse = z.infer<typeof EntityDetailResponseSchema>;
export const EntityFindingsResponseSchema = EnvelopeSchema.extend({
  findings: z.array(
    z.object({
      finding_id: z.string(),
      entity_id: z.string(),
      signal_id: z.string(),
      severity: z.string(),
      confidence: ConfidenceLevelSchema,
    }),
  ),
});
export type EntityFindingsResponse = z.infer<typeof EntityFindingsResponseSchema>;
export const FindingDetailResponseSchema = EnvelopeSchema.extend({
  finding: FindingSchema,
  provenance: ProvenanceSchema,
});
export type FindingDetailResponse = z.infer<typeof FindingDetailResponseSchema>;
export const EvidenceResponseSchema = EnvelopeSchema.extend({
  supporting_rows: z.array(z.record(z.string(), z.unknown())),
  counter_rows: z.array(z.record(z.string(), z.unknown())),
  counter_rows_absent_reason: z.string(),
  provenance: ProvenanceSchema,
});
export type EvidenceResponse = z.infer<typeof EvidenceResponseSchema>;
export const CounterfactualResponseSchema = EnvelopeSchema.extend({
  counterfactual: CounterfactualSchema,
  provenance: ProvenanceSchema,
});
export type CounterfactualResponse = z.infer<typeof CounterfactualResponseSchema>;
export const QueueResponseSchema = EnvelopeSchema.extend({
  queue: z.array(QueueItemSchema),
  insufficient_queue: z.array(z.string()),
});
export type QueueResponse = z.infer<typeof QueueResponseSchema>;
export const AuditVerifyResponseSchema = EnvelopeSchema.extend({
  valid: z.boolean(),
  entry_count: z.number(),
  merkle_root: z.string(),
});
export type AuditVerifyResponse = z.infer<typeof AuditVerifyResponseSchema>;
export const AuditEntriesResponseSchema = EnvelopeSchema.extend({
  entries: z.array(AuditEntrySchema),
});
export type AuditEntriesResponse = z.infer<typeof AuditEntriesResponseSchema>;
export const RunTriggerResponseSchema = EnvelopeSchema.extend({
  run_id: z.string(),
  status: z.string(),
});
export type RunTriggerResponse = z.infer<typeof RunTriggerResponseSchema>;
export const RunStatusResponseSchema = EnvelopeSchema.extend({ status: z.string() });
export type RunStatusResponse = z.infer<typeof RunStatusResponseSchema>;
export const IngestResponseSchema = EnvelopeSchema.extend({
  run_id: z.string(),
  status: z.string(),
  report: z.record(z.string(), z.unknown()).optional(),
});
export type IngestResponse = z.infer<typeof IngestResponseSchema>;
export const ErrorResponseSchema = EnvelopeSchema.extend({ error: z.string() });
export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;
