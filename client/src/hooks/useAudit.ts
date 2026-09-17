import { useAuditEntries, useAuditVerify } from '@/hooks/useRuns';

/** Combined audit view: verification result plus entry list. */
export function useAudit(runId?: string) {
  const verification = useAuditVerify();
  const entries = useAuditEntries(runId);
  return {
    verification: verification.data,
    entries: entries.data?.entries ?? [],
    isLoading: verification.isLoading || entries.isLoading,
    error: verification.error ?? entries.error ?? null,
    refetch: () => {
      void verification.refetch();
      void entries.refetch();
    },
  };
}
