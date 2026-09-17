import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { getEntities, type EntityFilters } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import type { EntitiesResponse } from '@/types/api';

/** Entity list for a run. Enabled only when runId is present. */
export function useEntities(
  runId: string | undefined,
  filters: EntityFilters = {},
): UseQueryResult<EntitiesResponse, Error> {
  const isUploadRun = Boolean(runId?.startsWith('upload-'));
  return useQuery({
    queryKey: queryKeys.entities.all(runId ?? '', filters),
    queryFn: () => getEntities(runId ?? '', filters),
    enabled: Boolean(runId),
    retry: isUploadRun ? true : 1,
    refetchInterval: (query) => isUploadRun && !query.state.data ? 2000 : false,
  });
}
