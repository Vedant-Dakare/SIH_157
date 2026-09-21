import { useSearchParams } from 'react-router-dom';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/layout/PageHeader';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { QueueTable } from '@/components/queue/QueueTable';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useQueue } from '@/hooks/useQueue';
import { useRuns } from '@/hooks/useRuns';

const LIMITS = [10, 25, 50];

/** Manual review queue page with run/limit selectors and CSV export. */
export default function QueuePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const runsQuery = useRuns();
  const runs = runsQuery.data?.runs ?? [];
  const runId = searchParams.get('run') ?? runs[0] ?? '';
  const limit = Number(searchParams.get('limit') ?? 25) || 25;
  const queueQuery = useQueue(runId || undefined, limit);

  function selectRun(next: string) {
    const params = new URLSearchParams(searchParams);
    params.set('run', next);
    setSearchParams(params);
  }

  function selectLimit(next: string) {
    const params = new URLSearchParams(searchParams);
    params.set('limit', next);
    setSearchParams(params);
  }

  function exportCsv(): void {
    const rows = queueQuery.data?.queue ?? [];
    const header = 'rank,entity_id,priority,risk_score,band,confidence,focus_area,signals,minutes\n';
    const body = rows
      .map((item) =>
        [
          item.rank,
          item.entity_id,
          item.priority,
          item.risk_score,
          item.band,
          item.confidence,
          item.focus_area,
          item.signal_ids.join('|'),
          item.expected_review_minutes,
        ].join(','),
      )
      .join('\n');
    const blob = new Blob([header + body], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `queue-${runId}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div>
      <PageHeader
        title="Manual Review Queue"
        description={
          queueQuery.data
            ? `Ranked worklist for run ${runId}, generated ${queueQuery.data.generated_at}. Start at the top.`
            : 'Ranked worklist of entities awaiting human review.'
        }
        actions={
          <>
            <Select value={runId} onValueChange={selectRun} disabled={runs.length === 0}>
              <SelectTrigger className="h-9 w-40 border-[#D9E2EC] bg-white text-xs font-medium text-[#1F2933] hover:border-[#1F5F8B] focus:ring-1 focus:ring-[#1F5F8B]" aria-label="Select run">
                <SelectValue placeholder="Run" />
              </SelectTrigger>
              <SelectContent className="border-[#D9E2EC] bg-white text-xs">
                {runs.map((id) => (
                  <SelectItem key={id} value={id} className="text-xs text-[#1F2933] focus:bg-[#EAF3F8] focus:text-[#123B5D]">
                    {id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={String(limit)} onValueChange={selectLimit}>
              <SelectTrigger className="h-9 w-24 border-[#D9E2EC] bg-white text-xs font-medium text-[#1F2933] hover:border-[#1F5F8B] focus:ring-1 focus:ring-[#1F5F8B]" aria-label="Select queue limit">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-[#D9E2EC] bg-white text-xs">
                {LIMITS.map((value) => (
                  <SelectItem key={value} value={String(value)} className="text-xs text-[#1F2933] focus:bg-[#EAF3F8] focus:text-[#123B5D]">
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={exportCsv}
              aria-label="Export queue as CSV"
              className="border-[#D9E2EC] bg-white text-[#123B5D] hover:bg-[#EAF3F8] hover:border-[#1F5F8B]"
            >
              Export CSV
            </Button>
          </>
        }
      />
      {queueQuery.isLoading ? <LoadingState rows={6} message="Loading queue…" /> : null}
      {queueQuery.error ? (
        <ErrorState
          error={queueQuery.error instanceof Error ? queueQuery.error : new Error('Queue unavailable.')}
          retry={() => void queueQuery.refetch()}
        />
      ) : null}
      {!queueQuery.isLoading && !queueQuery.error && !runId ? (
        <EmptyState title="No run selected" description="Pick a run to load its review queue." />
      ) : null}
      {!queueQuery.isLoading && !queueQuery.error && runId ? (
        <ErrorBoundary label="Review queue table">
          <QueueTable
            items={queueQuery.data?.queue ?? []}
            isLoading={false}
            runId={runId}
            insufficient={queueQuery.data?.insufficient_queue ?? []}
          />
        </ErrorBoundary>
      ) : null}
    </div>
  );
}
