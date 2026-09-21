import axios, { type AxiosInstance, isAxiosError } from 'axios';
import type { ZodType } from 'zod';
import {
  AuditEntriesResponseSchema,
  AuditVerifyResponseSchema,
  CounterfactualResponseSchema,
  EntitiesResponseSchema,
  EntityDetailResponseSchema,
  EntityFindingsResponseSchema,
  EvidenceResponseSchema,
  FindingDetailResponseSchema,
  HealthSchema,
  IngestResponseSchema,
  ManifestResponseSchema,
  QueueResponseSchema,
  RunTriggerResponseSchema,
  RunStatusResponseSchema,
  RunsResponseSchema,
  SchemaParseError,
  ValidationReportSchema,
  parseOrThrow,
  type AuditEntriesResponse,
  type AuditVerifyResponse,
  type CounterfactualResponse,
  type EntitiesResponse,
  type EntityDetailResponse,
  type EntityFindingsResponse,
  type EvidenceResponse,
  type FindingDetailResponse,
  type Health,
  type IngestResponse,
  type ManifestResponse,
  type QueueResponse,
  type RunTriggerResponse,
  type RunStatusResponse,
  type RunsResponse,
  type ValidationReport,
} from '@/types/api';

/** Typed API failure. Never a bare Error, never a console.log. */
export class ApiError extends Error {
  readonly status: number | null;
  readonly endpoint: string;

  constructor(endpoint: string, message: string, status: number | null = null) {
    super(`API ${endpoint} failed: ${message}`);
    this.name = 'ApiError';
    this.endpoint = endpoint;
    this.status = status;
  }
}

function resolveBaseUrl(): string {
  const configured =
    typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL
      ? String(import.meta.env.VITE_API_URL)
      : import.meta.env?.MODE === 'development'
        ? '/api'
        : 'http://127.0.0.1:8080';
  if (configured.startsWith('/')) {
    return configured;
  }
  if (!configured.startsWith('http://127.0.0.1') && !configured.startsWith('http://localhost')) {
    throw new Error(`Refusing non-loopback API URL: ${configured}`);
  }
  return configured;
}

function readToken(): string | null {
  if (typeof window === 'undefined' || typeof window.localStorage === 'undefined') {
    return null;
  }
  return window.localStorage.getItem('satsa-api-token');
}

export const api: AxiosInstance = axios.create({ baseURL: resolveBaseUrl(), timeout: 120000 });

api.interceptors.request.use((config) => {
  const token = readToken();
  if (token) {
    config.headers.set('X-API-Token', token);
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (isAxiosError(error) && error.response?.status === 401 && typeof window !== 'undefined') {
      window.location.assign('/settings');
    }
    throw error;
  },
);

async function validated<T>(
  endpoint: string,
  schema: ZodType<T>,
  request: Promise<{ data: unknown }>,
): Promise<T> {
  try {
    const response = await request;
    return parseOrThrow(schema, response.data, endpoint);
  } catch (error) {
    if (error instanceof SchemaParseError) {
      throw new ApiError(endpoint, error.message, null);
    }
    if (isAxiosError(error)) {
      const detail =
        typeof error.response?.data === 'object' && error.response?.data !== null
          ? String((error.response.data as { error?: unknown }).error ?? error.message)
          : error.message;
      throw new ApiError(endpoint, detail, error.response?.status ?? null);
    }
    throw new ApiError(endpoint, error instanceof Error ? error.message : String(error), null);
  }
}

export interface EntityFilters {
  band?: string;
  sector?: string;
}

function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') {
      search.set(key, String(value));
    }
  }
  const text = search.toString();
  return text ? `?${text}` : '';
}

export function getHealth(): Promise<Health> {
  return validated<Health>('GET /health', HealthSchema, api.get('/health'));
}

export function getRuns(): Promise<RunsResponse> {
  return validated<RunsResponse>('GET /runs', RunsResponseSchema, api.get('/runs'));
}

export function getRunManifest(runId: string): Promise<ManifestResponse> {
  return validated<ManifestResponse>(
    `GET /runs/${runId}/manifest`,
    ManifestResponseSchema,
    api.get(`/runs/${encodeURIComponent(runId)}/manifest`),
  );
}

export function getRunStatus(runId: string): Promise<RunStatusResponse> {
  return validated<RunStatusResponse>(
    `GET /runs/${runId}`,
    RunStatusResponseSchema,
    api.get(`/runs/${encodeURIComponent(runId)}`),
  );
}

export function getEntities(runId: string, filters: EntityFilters = {}): Promise<EntitiesResponse> {
  return validated<EntitiesResponse>(
    'GET /entities',
    EntitiesResponseSchema,
    api.get(`/entities${query({ run_id: runId, band: filters.band, sector: filters.sector })}`),
  );
}

export function getEntity(entityId: string, runId: string): Promise<EntityDetailResponse> {
  return validated<EntityDetailResponse>(
    `GET /entities/${entityId}`,
    EntityDetailResponseSchema,
    api.get(`/entities/${encodeURIComponent(entityId)}${query({ run_id: runId })}`),
  );
}

export function getEntityFindings(entityId: string, runId: string): Promise<EntityFindingsResponse> {
  return validated<EntityFindingsResponse>(
    `GET /entities/${entityId}/findings`,
    EntityFindingsResponseSchema,
    api.get(`/entities/${encodeURIComponent(entityId)}/findings${query({ run_id: runId })}`),
  );
}

export function getFinding(findingId: string, runId?: string): Promise<FindingDetailResponse> {
  return validated<FindingDetailResponse>(
    `GET /findings/${findingId}`,
    FindingDetailResponseSchema,
    api.get(`/findings/${encodeURIComponent(findingId)}${query({ run_id: runId })}`),
  );
}

export function getFindingEvidence(findingId: string, runId?: string): Promise<EvidenceResponse> {
  return validated<EvidenceResponse>(
    `GET /findings/${findingId}/evidence`,
    EvidenceResponseSchema,
    api.get(`/findings/${encodeURIComponent(findingId)}/evidence${query({ run_id: runId })}`),
  );
}

export function getFindingCounterfactual(
  findingId: string,
  runId?: string,
): Promise<CounterfactualResponse> {
  return validated<CounterfactualResponse>(
    `GET /findings/${findingId}/counterfactual`,
    CounterfactualResponseSchema,
    api.get(`/findings/${encodeURIComponent(findingId)}/counterfactual${query({ run_id: runId })}`),
  );
}

export function getQueue(runId: string, limit = 50): Promise<QueueResponse> {
  return validated<QueueResponse>(
    'GET /queue',
    QueueResponseSchema,
    api.get(`/queue${query({ run_id: runId, limit })}`),
  );
}

export function getAuditVerify(): Promise<AuditVerifyResponse> {
  return validated<AuditVerifyResponse>('GET /audit/verify', AuditVerifyResponseSchema, api.get('/audit/verify'));
}

export function getAuditEntries(runId?: string): Promise<AuditEntriesResponse> {
  return validated<AuditEntriesResponse>(
    'GET /audit/entries',
    AuditEntriesResponseSchema,
    api.get(`/audit/entries${query({ run_id: runId })}`),
  );
}

export function triggerRun(runId?: string): Promise<RunTriggerResponse> {
  return validated<RunTriggerResponse>(
    'POST /runs',
    RunTriggerResponseSchema,
    api.post('/runs', runId ? { run_id: runId } : {}),
  );
}

export function uploadSubmission(
  cseId: string,
  runId: string,
  files: File[],
): Promise<IngestResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append('files', file, file.name);
  }
  return validated<IngestResponse>(
    'POST /ingest',
    IngestResponseSchema,
    api.post(`/ingest${query({ cse_id: cseId, run_id: runId })}`, form),
  );
}

/**
 * Provisional validation-report fetch. No stable backend route exists yet;
 * callers must handle ApiError with an empty state pointing at the
 * data/curated/validation/ artefacts.
 */
export function getValidationReport(runId: string): Promise<ValidationReport> {
  return validated<ValidationReport>(
    'GET /validation',
    ValidationReportSchema,
    api.get(`/validation${query({ run_id: runId })}`),
  );
}
