import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { getEntity, getEntityFindings } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import type { EntityDetailResponse, EntityFindingsResponse } from '@/types/api';

/** Single entity detail. Enabled only when entityId and runId are present. */
export function useEntity(
  entityId: string | undefined,
  runId: string | undefined,
): UseQueryResult<EntityDetailResponse, Error> {
  return useQuery({
    queryKey: queryKeys.entities.detail(entityId ?? '', runId ?? ''),
    queryFn: () => getEntity(entityId ?? '', runId ?? ''),
    enabled: Boolean(entityId && runId),
  });
}

/** Findings list for one entity. Enabled only when entityId and runId are present. */
export function useFindings(
  entityId: string | undefined,
  runId: string | undefined,
): UseQueryResult<EntityFindingsResponse, Error> {
  return useQuery({
    queryKey: queryKeys.entities.findings(entityId ?? '', runId ?? ''),
    queryFn: () => getEntityFindings(entityId ?? '', runId ?? ''),
    enabled: Boolean(entityId && runId),
  });
}
