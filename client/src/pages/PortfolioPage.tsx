import { useSearchParams } from 'react-router-dom';
import { Play } from 'lucide-react';

import { RiskBandChart } from '@/components/charts/RiskBandChart';
import { SignalHeatmap } from '@/components/charts/SignalHeatmap';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/layout/PageHeader';
import { EntityRankTable } from '@/components/portfolio/EntityRankTable';
import { PortfolioSummary } from '@/components/portfolio/PortfolioSummary';
import { SectorBreakdown } from '@/components/portfolio/SectorBreakdown';
import { TrendPanel } from '@/components/portfolio/TrendPanel';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useToast } from '@/components/ui/toaster';
import { useEntities } from '@/hooks/useEntities';
import { useQueue } from '@/hooks/useQueue';
import { useRuns } from '@/hooks/useRuns';
import { triggerRun } from '@/lib/api';
import type { Entity, Finding, RiskBand } from '@/types/api';

/** Portfolio overview: summary, bands, trends, heatmap, sectors, ranking. */
export default function PortfolioPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const runsQuery = useRuns();
  const runs = runsQuery.data?.runs ?? [];
  const runId = searchParams.get('run') ?? runs[0] ?? '';
  const isUploadRun = runId.startsWith('upload-');
  const { toast } = useToast();

  const entitiesQuery = useEntities(runId || undefined);
  const queueQuery = useQueue(entitiesQuery.data ? runId : undefined);
  const entities: Entity[] = entitiesQuery.data?.entities ?? [];

  function selectRun(next: string) {
    const params = new URLSearchParams(searchParams);
    params.set('run', next);
    setSearchParams(params);
  }

  async function onTrigger(): Promise<void> {
    try {
      const result = await triggerRun();
      toast({ title: 'Pipeline run started', description: `Run ${result.run_id} queued.` });
    } catch (error) {
      toast({
        title: 'Failed to trigger run',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  }

  const bandCounts = { HIGH: 0, ELEVATED: 0, MODERATE: 0, LOW: 0 } as Record<RiskBand, number>;
  for (const entity of entities) {
    bandCounts[entity.band] += 1;
  }
  const queueFindings: Finding[] = [];
  const queueSignals = Array.from(
    new Set((queueQuery.data?.queue ?? []).flatMap((item) => item.signal_ids)),
  ).sort();

  return (
    <div>
      <PageHeader
        title="Portfolio Overview"
        description={runId ? `Run ${runId}` : 'Select a run to begin.'}
        actions={
          <>
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
            <Button type="button" variant="outline" size="sm" onClick={() => void onTrigger()} aria-label="Trigger pipeline run">
              <Play className="h-3.5 w-3.5" aria-hidden="true" />
              Trigger Run
            </Button>
          </>
        }
      />
      {isUploadRun && runId && !entitiesQuery.data && !entitiesQuery.error ? (
        <LoadingState rows={3} message={`Processing run ${runId}…`} />
      ) : null}
      {runsQuery.error ? (
        <ErrorState
          error={runsQuery.error instanceof Error ? runsQuery.error : new Error('Failed to load runs.')}
          retry={() => void runsQuery.refetch()}
        />
      ) : null}
      {!runsQuery.isLoading && !runsQuery.error && runs.length === 0 ? (
        <ErrorState
          error={new Error('No pipeline runs are available. Start the API and run the pipeline before opening this view.')}
          retry={() => void runsQuery.refetch()}
        />
      ) : null}
      {entitiesQuery.isLoading || queueQuery.isLoading ? <LoadingState rows={6} message="Loading portfolio…" /> : null}
      {entitiesQuery.error ? (
        <ErrorState
          error={entitiesQuery.error instanceof Error ? entitiesQuery.error : new Error('Failed to load entities.')}
          retry={() => void entitiesQuery.refetch()}
        />
      ) : null}
      {!runsQuery.isLoading && !runsQuery.error && Boolean(entitiesQuery.data) && !entitiesQuery.isLoading && !entitiesQuery.error ? (
        <div className="space-y-6">
          <ErrorBoundary label="Portfolio summary">
            <PortfolioSummary
              summary={{
                entity_count_by_band: bandCounts,
                top_5_entities_by_risk: [...entities]
                  .sort((a, b) => b.overall_score - a.overall_score)
                  .slice(0, 5)
                  .map((entity) => entity.entity_id),
                sector_aggregates: {},
                portfolio_trend: 'STABLE',
              }}
              isLoading={false}
              findingsCount={queueQuery.data?.queue.reduce((sum, item) => sum + item.signal_ids.length, 0)}
            />
          </ErrorBoundary>
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <section aria-label="Risk bands" className="rounded-md border border-slate-700 bg-slate-900 p-4">
              <ErrorBoundary label="Risk band chart">
                <RiskBandChart data={bandCounts} isLoading={false} />
              </ErrorBoundary>
            </section>
            <section aria-label="Trends" className="rounded-md border border-slate-700 bg-slate-900 p-4 xl:col-span-2">
              <ErrorBoundary label="Trend panel">
                <TrendPanel currentRun={runId} trends={[]} hasPriorRun={runs.length > 1} />
              </ErrorBoundary>
            </section>
          </div>
          <section aria-label="Signal heatmap" className="rounded-md border border-slate-700 bg-slate-900 p-4">
            <ErrorBoundary label="Signal heatmap">
              {queueQuery.error ? (
                <ErrorState
                  error={new Error('Signal data unavailable.')}
                  retry={() => void queueQuery.refetch()}
                />
              ) : (
                <SignalHeatmap entities={entities} signals={queueSignals} findings={queueFindings} />
              )}
            </ErrorBoundary>
          </section>
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <section aria-label="Sectors" className="rounded-md border border-slate-700 bg-slate-900 p-4">
              <ErrorBoundary label="Sector breakdown">
                <SectorBreakdown entities={entities} />
              </ErrorBoundary>
            </section>
            <section aria-label="Entity ranking" className="rounded-md border border-slate-700 bg-slate-900 p-4 xl:col-span-2">
              <ErrorBoundary label="Entity rank table">
                <EntityRankTable entities={entities} isLoading={false} runId={runId} />
              </ErrorBoundary>
            </section>
          </div>
        </div>
      ) : null}
    </div>
  );
}
