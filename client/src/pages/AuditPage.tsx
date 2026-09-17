import { useSearchParams } from 'react-router-dom';

import { ErrorState } from '@/components/common/ErrorState';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/layout/PageHeader';
import { LedgerTable } from '@/components/audit/LedgerTable';
import { RunManifest } from '@/components/audit/RunManifest';
import { VerifyResult } from '@/components/audit/VerifyResult';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { useToast } from '@/components/ui/toaster';
import { useAuditEntries, useAuditVerify, useRunManifest, useRuns } from '@/hooks/useRuns';

/** Audit page: auto-verifies on load; manifest and ledger tabs. */
export default function AuditPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const runsQuery = useRuns();
  const runs = runsQuery.data?.runs ?? [];
  const runId = searchParams.get('run') ?? runs[0] ?? '';
  const { toast } = useToast();

  const verifyQuery = useAuditVerify();
  const entriesQuery = useAuditEntries(runId || undefined);
  const manifestQuery = useRunManifest(runId || undefined);

  function selectRun(next: string) {
    const params = new URLSearchParams(searchParams);
    params.set('run', next);
    setSearchParams(params);
  }

  return (
    <div>
      <PageHeader
        title="Audit & Integrity Verification"
        description="Tamper-evident ledger, verified on every page load."
        actions={
          <Select value={runId} onValueChange={selectRun} disabled={runs.length === 0}>
            <SelectTrigger className="h-9 w-44" aria-label="Select run">
              <SelectValue placeholder={runsQuery.isLoading ? 'Loading…' : 'No runs'} />
            </SelectTrigger>
            <SelectContent>
              {runs.map((id) => (
                <SelectItem key={id} value={id}>
                  {id}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      />
      <div className="mb-6">
        {verifyQuery.isLoading ? (
          <VerifyResult result={null} isLoading />
        ) : verifyQuery.error ? (
          <ErrorState
            error={verifyQuery.error instanceof Error ? verifyQuery.error : new Error('Verification failed.')}
            retry={() => void verifyQuery.refetch()}
          />
        ) : (
          <VerifyResult
            result={
              verifyQuery.data
                ? {
                    valid: verifyQuery.data.valid,
                    entry_count: verifyQuery.data.entry_count,
                    merkle_root: verifyQuery.data.merkle_root,
                  }
                : null
            }
            isLoading={false}
            onExportBroken={() => toast({ title: 'Chain exported', description: 'Broken-chain bundle downloaded.' })}
          />
        )}
      </div>
      <Tabs defaultValue="manifest">
        <TabsList aria-label="Audit sections">
          <TabsTrigger value="manifest">Run Manifest</TabsTrigger>
          <TabsTrigger value="ledger">Ledger Entries</TabsTrigger>
        </TabsList>
        <TabsContent forceMount value="manifest">
          <ErrorBoundary label="manifest panel">

          {manifestQuery.isLoading ? (
            <LoadingState rows={6} message="Loading manifest…" />
          ) : manifestQuery.error || !manifestQuery.data ? (
            <ErrorState
              error={manifestQuery.error instanceof Error ? manifestQuery.error : new Error('Manifest unavailable.')}
              retry={() => void manifestQuery.refetch()}
            />
          ) : (
            <RunManifest
              manifest={manifestQuery.data.manifest}
              runId={runId}
              onVerify={() => void verifyQuery.refetch()}
              verifying={verifyQuery.isFetching}
            />
          )}
          </ErrorBoundary>
        </TabsContent>
        <TabsContent forceMount value="ledger">
          <ErrorBoundary label="ledger panel">

          <LedgerTable entries={entriesQuery.data?.entries ?? []} isLoading={entriesQuery.isLoading} />
          </ErrorBoundary>
        </TabsContent>
      </Tabs>
    </div>
  );
}
