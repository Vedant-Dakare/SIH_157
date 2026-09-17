import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { getQueue } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import type { QueueResponse } from '@/types/api';

/** Prioritised review queue. Enabled only when runId is present. */
export function useQueue(
  runId: string | undefined,
  limit = 50,
): UseQueryResult<QueueResponse, Error> {
  return useQuery({
    queryKey: queryKeys.queue.list(runId ?? '', limit),
    queryFn: () => getQueue(runId ?? '', limit),
    enabled: Boolean(runId),
  });
}
