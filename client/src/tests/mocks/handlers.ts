import { HttpResponse, http } from 'msw';
import { setupServer } from 'msw/node';

import {
  GENERATED_AT,
  RUN_ID,
  mockAuditEntries,
  mockCounterfactual,
  mockEntities,
  mockEntityDetail,
  mockEvidence,
  mockFindings,
  mockManifest,
  mockQueue,
} from '@/tests/mocks/data';

const BASE = 'http://127.0.0.1:8080';

function envelope<T extends object>(payload: T): T & { run_id: string; generated_at: string } {
  return { run_id: RUN_ID, generated_at: GENERATED_AT, ...payload };
}

export const handlers = [
  http.get(`${BASE}/health`, () =>
    HttpResponse.json(envelope({ status: 'ok', pipeline_version: 'phase6' })),
  ),
  http.get(`${BASE}/runs`, () => HttpResponse.json(envelope({ runs: [RUN_ID, 'e2e'] }))),
  http.get(`${BASE}/runs/:runId/manifest`, () =>
    HttpResponse.json(envelope({ manifest: mockManifest })),
  ),
  http.post(`${BASE}/runs`, () =>
    HttpResponse.json(envelope({ run_id: 'run-20240601120000', status: 'started' }), { status: 202 }),
  ),
  http.get(`${BASE}/entities`, () => HttpResponse.json(envelope({ entities: mockEntities }))),
  http.get(`${BASE}/entities/:entityId`, ({ params }) =>
    HttpResponse.json(
      envelope({ entity: { ...mockEntityDetail, entity_id: String(params.entityId) } }),
    ),
  ),
  http.get(`${BASE}/entities/:entityId/findings`, () =>
    HttpResponse.json(
      envelope({
        findings: mockFindings.map((finding) => ({
          finding_id: finding.finding_id,
          entity_id: finding.entity_id,
          signal_id: finding.signal_id,
          severity: finding.severity,
          confidence: finding.confidence,
        })),
      }),
    ),
  ),
  http.get(`${BASE}/findings/:findingId`, ({ params }) =>
    HttpResponse.json(
      envelope({
        finding: { ...mockFindings[0], finding_id: String(params.findingId) },
        provenance: { evidence_id: mockEvidence.evidence_id },
      }),
    ),
  ),
  http.get(`${BASE}/findings/:findingId/evidence`, () =>
    HttpResponse.json(
      envelope({
        supporting_rows: mockEvidence.supporting_rows,
        counter_rows: mockEvidence.counter_rows,
        counter_rows_absent_reason: mockEvidence.counter_rows_absent_reason,
        provenance: { evidence_id: mockEvidence.evidence_id },
      }),
    ),
  ),
  http.get(`${BASE}/findings/:findingId/counterfactual`, () =>
    HttpResponse.json(
      envelope({
        counterfactual: mockCounterfactual,
        provenance: { evidence_id: mockEvidence.evidence_id },
      }),
    ),
  ),
  http.get(`${BASE}/queue`, () =>
    HttpResponse.json(envelope({ queue: mockQueue, insufficient_queue: ['cse_juliet'] })),
  ),
  http.get(`${BASE}/audit/verify`, () =>
    HttpResponse.json(envelope({ valid: true, entry_count: 10, merkle_root: mockManifest.merkle_root })),
  ),
  http.get(`${BASE}/audit/entries`, () =>
    HttpResponse.json(envelope({ entries: mockAuditEntries })),
  ),
];

/** Error variants for error-state tests. Swap in with server.use(). */
export const errorHandlers = [
  http.get(`${BASE}/entities`, () =>
    HttpResponse.json({ run_id: RUN_ID, generated_at: GENERATED_AT, error: 'boom' }, { status: 500 }),
  ),
  http.get(`${BASE}/findings/:findingId`, () =>
    HttpResponse.json(
      {
        run_id: RUN_ID,
        generated_at: GENERATED_AT,
        finding: { ...mockFindings[0], score: 'not-a-number' },
        provenance: { evidence_id: 'e' },
      },
      { status: 200 },
    ),
  ),
];

export const server = setupServer(...handlers);
