import { Link } from 'react-router-dom';
import { Play } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toaster';
import { getHealth, getRunManifest, triggerRun } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/utils';
import { useRunManifest, useRuns } from '@/hooks/useRuns';

/** One run row, enriched from its manifest when available. */
function RunRow({ runId }: { runId: string }) {
  const manifestQuery = useRunManifest(runId);
  const manifest = manifestQuery.data?.manifest;
  const complete = manifest !== undefined;
  return (
    <tr className="border-b border-slate-700 last:border-0">
      <td className="mono px-3 py-2 text-slate-50">{runId}</td>
      <td className="px-3 py-2 text-slate-400">{manifest ? formatDate(manifest.created_at) : '—'}</td>
      <td className="px-3 py-2 text-slate-400">—</td>
      <td className="px-3 py-2 text-slate-400">—</td>
      <td className="px-3 py-2">
        {manifestQuery.isLoading ? (
          <span className="text-slate-500">…</span>
        ) : (
          <Badge variant={complete ? 'default' : 'secondary'}>{complete ? 'COMPLETE' : 'UNKNOWN'}</Badge>
        )}
      </td>
      <td className="px-3 py-2 text-slate-50">{manifest?.entity_count ?? '—'}</td>
      <td className="px-3 py-2 text-slate-50">{manifest?.finding_count ?? '—'}</td>
      <td className="px-3 py-2">
        <Link to={`/audit?run=${encodeURIComponent(runId)}`} className="text-slate-50 underline underline-offset-4">
          Manifest
        </Link>
      </td>
      <td className="px-3 py-2">
        <div className="flex gap-3">
          <Link to={`/portfolio?run=${encodeURIComponent(runId)}`} className="text-slate-50 underline underline-offset-4">
            Portfolio
          </Link>
          <Link to={`/audit?run=${encodeURIComponent(runId)}`} className="text-slate-50 underline underline-offset-4">
            Audit
          </Link>
        </div>
      </td>
    </tr>
  );
}

/** Run history with trigger, health polling and toasts. */
export default function RunsPage() {
  const runsQuery = useRuns();
  const { toast } = useToast();
  const runs = runsQuery.data?.runs ?? [];

  useQuery({
    queryKey: [...queryKeys.health.status, 'poll'],
    queryFn: () => getHealth(),
    refetchInterval: 5000,
  });

  async function onTrigger(): Promise<void> {
    try {
      const result = await triggerRun();
      toast({ title: 'Run started', description: `Run ${result.run_id} queued. Watch manifests appear below.` });
      await runsQuery.refetch();
      for (let attempt = 0; attempt < 12; attempt += 1) {
        await new Promise((resolve) => {
          setTimeout(resolve, 5000);
        });
        try {
          await getRunManifest(result.run_id);
          toast({ title: 'Run complete — view results', description: `Manifest for ${result.run_id} is ready.` });
          await runsQuery.refetch();
          return;
        } catch {
          // Manifest not yet written; keep polling.
        }
      }
    } catch (error) {
      toast({
        title: 'Failed to trigger run',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  }

  return (
    <div>
      <PageHeader
        title="Run History"
        description="Every pipeline run. Health is polled every 5 seconds."
        actions={
          <Button type="button" onClick={() => void onTrigger()} aria-label="Trigger pipeline run" size="lg">
            <Play className="h-4 w-4" aria-hidden="true" />
            Trigger Run
          </Button>
        }
      />
      {runsQuery.isLoading ? <LoadingState rows={4} message="Loading runs…" /> : null}
      {runsQuery.error ? (
        <ErrorState
          error={runsQuery.error instanceof Error ? runsQuery.error : new Error('Runs unavailable.')}
          retry={() => void runsQuery.refetch()}
        />
      ) : null}
      {!runsQuery.isLoading && !runsQuery.error && runs.length === 0 ? (
        <EmptyState title="No runs yet" description="Trigger the first run to get started." />
      ) : null}
      {!runsQuery.isLoading && !runsQuery.error && runs.length > 0 ? (
        <ErrorBoundary label="Run history table">
          <div className="overflow-x-auto rounded-md border border-slate-700">
          <table aria-label="Pipeline runs" className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-slate-400">
                {['Run ID', 'Started', 'Finished', 'Duration', 'Status', 'Entities', 'Findings', 'Manifest', 'Actions'].map(
                  (header) => (
                    <th key={header} className="px-3 py-2 font-medium">
                      {header}
                    </th>
                  ),
                )}
              </tr>
            </thead>
            <tbody>
              {runs.map((runId) => (
                <RunRow key={runId} runId={runId} />
              ))}
            </tbody>
          </table>
          </div>
        </ErrorBoundary>
      ) : null}
    </div>
  );
}
