import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { getFinding, getFindingCounterfactual, getFindingEvidence } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import type {
  CounterfactualResponse,
  EvidenceResponse,
  FindingDetailResponse,
} from '@/types/api';

/** Full finding record. Enabled only when findingId is present. */
export function useFinding(
  findingId: string | undefined,
  runId?: string,
): UseQueryResult<FindingDetailResponse, Error> {
  return useQuery({
    queryKey: queryKeys.findings.detail(findingId ?? '', runId),
    queryFn: () => getFinding(findingId ?? '', runId),
    enabled: Boolean(findingId),
  });
}

/** Supporting + counter evidence rows. Enabled only when findingId is present. */
export function useEvidence(
  findingId: string | undefined,
  runId?: string,
): UseQueryResult<EvidenceResponse, Error> {
  return useQuery({
    queryKey: queryKeys.findings.evidence(findingId ?? '', runId),
    queryFn: () => getFindingEvidence(findingId ?? '', runId),
    enabled: Boolean(findingId),
  });
}

/** Counterfactual for one finding. Enabled only when findingId is present. */
export function useCounterfactual(
  findingId: string | undefined,
  runId?: string,
): UseQueryResult<CounterfactualResponse, Error> {
  return useQuery({
    queryKey: queryKeys.findings.counterfactual(findingId ?? '', runId),
    queryFn: () => getFindingCounterfactual(findingId ?? '', runId),
    enabled: Boolean(findingId),
  });
}
