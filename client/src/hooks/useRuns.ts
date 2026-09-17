import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { getAuditEntries, getAuditVerify, getHealth, getRunManifest, getRunStatus, getRuns } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import type {
  AuditEntriesResponse,
  AuditVerifyResponse,
  Health,
  ManifestResponse,
  RunsResponse,
  RunStatusResponse,
} from '@/types/api';

/** Run id list. Always enabled. */
export function useRuns(): UseQueryResult<RunsResponse, Error> {
  return useQuery({
    queryKey: queryKeys.runs.all,
    queryFn: () => getRuns(),
  });
}

/** Manifest for one run. Enabled only when runId is present. */
export function useRunManifest(
  runId: string | undefined,
): UseQueryResult<ManifestResponse, Error> {
  return useQuery({
    queryKey: queryKeys.runs.manifest(runId ?? ''),
    queryFn: () => getRunManifest(runId ?? ''),
    enabled: Boolean(runId),
  });
}

export function useRunStatus(runId: string | undefined): UseQueryResult<RunStatusResponse, Error> {
  const isUploadRun = Boolean(runId?.startsWith('upload-'));
  return useQuery({
    queryKey: queryKeys.runs.status(runId ?? ''),
    queryFn: () => getRunStatus(runId ?? ''),
    enabled: isUploadRun,
    retry: true,
    refetchInterval: (query) => query.state.data?.status === 'complete' || query.state.data?.status === 'failed' ? false : 2000,
  });
}

/** Backend liveness probe. Always enabled. */
export function useHealth(): UseQueryResult<Health, Error> {
  return useQuery({
    queryKey: queryKeys.health.status,
    queryFn: () => getHealth(),
  });
}

/** Ledger verification result. Always enabled. */
export function useAuditVerify(): UseQueryResult<AuditVerifyResponse, Error> {
  return useQuery({
    queryKey: queryKeys.audit.verify,
    queryFn: () => getAuditVerify(),
  });
}

/** Ledger entries, optionally filtered by run. Always enabled. */
export function useAuditEntries(
  runId?: string,
): UseQueryResult<AuditEntriesResponse, Error> {
  return useQuery({
    queryKey: queryKeys.audit.entries(runId),
    queryFn: () => getAuditEntries(runId),
  });
}
