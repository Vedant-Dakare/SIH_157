import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  FileSearch,
  Play,
  ShieldAlert,
  Activity,
} from 'lucide-react';

import { RiskBandChart } from '@/components/charts/RiskBandChart';
import { SignalHeatmap } from '@/components/charts/SignalHeatmap';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingState } from '@/components/common/LoadingState';
import { RiskBadge } from '@/components/common/RiskBadge';
import { EntityRankTable } from '@/components/portfolio/EntityRankTable';
import { PortfolioSummary } from '@/components/portfolio/PortfolioSummary';
import { SectorBreakdown } from '@/components/portfolio/SectorBreakdown';
import { TrendPanel } from '@/components/portfolio/TrendPanel';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toaster';
import { useEntities } from '@/hooks/useEntities';
import { useQueue } from '@/hooks/useQueue';
import { useRuns } from '@/hooks/useRuns';
import { triggerRun } from '@/lib/api';
import type { Entity, Finding, RiskBand } from '@/types/api';

/** Portfolio overview: presentation redesigned only; API/data flow is unchanged. */
export default function PortfolioPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const runsQuery = useRuns();
  const runs = runsQuery.data?.runs ?? [];
  const runId = searchParams.get('run') ?? runs[0] ?? '';

  const isUploadRun = runId.startsWith('upload-');
  const { toast } = useToast();

  const entitiesQuery = useEntities(runId || undefined);

  const queueQuery = useQueue(
    entitiesQuery.data ? runId : undefined,
  );

  const entities: Entity[] =
    entitiesQuery.data?.entities ?? [];

  const customEntities = entities.filter(
    (e) =>
      !e.entity_id.startsWith('cse_') &&
      !e.entity_id.startsWith('CSE_'),
  );

  async function onTrigger(): Promise<void> {
    try {
      const result = await triggerRun();

      toast({
        title: 'Pipeline run started',
        description: `Run ${result.run_id} queued.`,
      });
    } catch (error) {
      toast({
        title: 'Failed to trigger run',
        description:
          error instanceof Error
            ? error.message
            : 'Unknown error',
        variant: 'destructive',
      });
    }
  }

  const bandCounts = {
    HIGH: 0,
    ELEVATED: 0,
    MODERATE: 0,
    LOW: 0,
  } as Record<RiskBand, number>;

  for (const entity of entities) {
    bandCounts[entity.band] += 1;
  }

  const queueFindings: Finding[] = [];

  const queueSignals = Array.from(
    new Set(
      (queueQuery.data?.queue ?? []).flatMap(
        (item) => item.signal_ids,
      ),
    ),
  ).sort();

  return (
    <div className="space-y-6">

      {/* Overview heading */}
      <section className="console-card overflow-hidden">
        <div className="border-b border-slate-200 bg-white px-5 py-5 sm:px-6">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <div className="console-label">
                NCIIPC Decision Support
              </div>

              <h1 className="mt-1 text-2xl font-bold tracking-tight text-[#102a56]">
                Security Operations Overview
              </h1>

              <p className="mt-1.5 max-w-3xl text-sm leading-6 text-slate-600">
                Supervisory visibility across security cases,
                standardized findings and cross-CSE patterns.
              </p>
            </div>

            {/* Trigger Run */}
<Button
  type="button"
  variant="outline"
  size="sm"
  onClick={() => void onTrigger()}
  className="border-[#123d73] bg-[#123d73] text-white hover:border-[#bfdbfe] hover:bg-blue-100 hover:text-[#123d73]"
  aria-label="Trigger pipeline run"
>
  <Play
    className="mr-1.5 h-3.5 w-3.5"
    aria-hidden="true"
  />
  Trigger Run
</Button>
          </div>
        </div>

        <div className="bg-[#f8fafc] px-5 py-2.5 text-[11px] text-slate-600 sm:px-6">
          <span className="font-semibold text-[#123d73]">
            Advisory output
          </span>

          <span className="mx-2 text-slate-400">·</span>

          Supervisory decision rests with the human expert.
        </div>
      </section>

      {/* Loading / errors */}
      {isUploadRun && runId && !entitiesQuery.data ? (
        <LoadingState
          rows={4}
          message={`Processing run ${runId}… Scoring custom dataset, computing 30 signals, and building portfolio.`}
        />
      ) : null}

      {runsQuery.error ? (
        <ErrorState
          error={
            runsQuery.error instanceof Error
              ? runsQuery.error
              : new Error('Failed to load runs.')
          }
          retry={() => void runsQuery.refetch()}
        />
      ) : null}

      {!runsQuery.isLoading &&
      !runsQuery.error &&
      runs.length === 0 ? (
        <ErrorState
          error={
            new Error(
              'No pipeline runs are available. Start the API and run the pipeline before opening this view.',
            )
          }
          retry={() => void runsQuery.refetch()}
        />
      ) : null}

      {!isUploadRun &&
      (entitiesQuery.isLoading || queueQuery.isLoading) ? (
        <LoadingState
          rows={6}
          message="Loading portfolio…"
        />
      ) : null}

      {entitiesQuery.error ? (
        <ErrorState
          error={
            entitiesQuery.error instanceof Error
              ? entitiesQuery.error
              : new Error('Failed to load entities.')
          }
          retry={() => void entitiesQuery.refetch()}
        />
      ) : null}

      {Boolean(entitiesQuery.data) ? (
        <div className="space-y-6">

          {/* Existing portfolio summary */}
          <section aria-label="Portfolio statistics">
            <ErrorBoundary label="Portfolio summary">
              <PortfolioSummary
                summary={{
                  entity_count_by_band: bandCounts,
                  top_5_entities_by_risk: [...entities]
                    .sort(
                      (a, b) =>
                        b.overall_score -
                        a.overall_score,
                    )
                    .slice(0, 5)
                    .map(
                      (entity) => entity.entity_id,
                    ),
                  sector_aggregates: {},
                  portfolio_trend: 'STABLE',
                }}
                isLoading={false}
                findingsCount={queueQuery.data?.queue.reduce(
                  (sum, item) =>
                    sum + item.signal_ids.length,
                  0,
                )}
              />
            </ErrorBoundary>
          </section>

          {/* Attention queue / uploaded entities */}
          {customEntities.length > 0 ? (
            <section
              aria-label="Attention queue"
              className="console-card overflow-hidden"
            >
              <div className="console-section-header flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <AlertTriangle
                      className="h-4 w-4 text-amber-600"
                      aria-hidden="true"
                    />

                    <h2 className="font-semibold text-slate-900">
                      Attention Queue
                    </h2>
                  </div>

                  <p className="mt-1 text-xs text-slate-500">
                    Cases and entities surfaced for supervisory
                    review.
                  </p>
                </div>

                <span className="text-xs font-medium text-slate-500">
                  {customEntities.length} available
                </span>
              </div>

              <div className="divide-y divide-slate-200">
                {customEntities.map((entity) => (
                  <button
                    key={entity.entity_id}
                    type="button"
                    onClick={() =>
                      navigate(
                        `/entities/${entity.entity_id}?run=${runId}`,
                      )
                    }
                    className="console-interactive flex w-full flex-col gap-4 px-5 py-4 text-left sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex min-w-0 items-start gap-3">
                      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-slate-50">
                        <FileSearch
                          className="h-4 w-4 text-[#123d73]"
                          aria-hidden="true"
                        />
                      </div>

                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-sm font-semibold text-slate-900">
                            {entity.entity_id}
                          </span>

                          <RiskBadge
                            band={entity.band}
                            size="sm"
                          />
                        </div>

                        <p className="mt-1 text-xs text-slate-500">
                          Supervisory review surface · Risk score{' '}
                          <span className="font-semibold tabular-nums text-slate-700">
                            {entity.overall_score.toFixed(1)}
                          </span>
                        </p>
                      </div>
                    </div>

                    <span className="shrink-0 text-xs font-semibold text-[#123d73]">
                      Review case →
                    </span>
                  </button>
                ))}
              </div>
            </section>
          ) : null}

          {/* Risk distribution and trends */}
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">

            <section
              aria-label="Severity distribution"
              className="console-card overflow-hidden"
            >
              <div className="console-section-header">
                <div className="flex items-center gap-2">
                  <ShieldAlert
                    className="h-4 w-4 text-[#123d73]"
                    aria-hidden="true"
                  />

                  <h2 className="font-semibold text-slate-900">
                    Severity Distribution
                  </h2>
                </div>

                <p className="mt-1 text-xs text-slate-500">
                  Current distribution across monitored entities.
                </p>
              </div>

              <div className="p-5">
                <ErrorBoundary label="Risk band chart">
                  <RiskBandChart
                    data={bandCounts}
                    isLoading={false}
                  />
                </ErrorBoundary>
              </div>
            </section>

            <section
              aria-label="Findings over time"
              className="console-card overflow-hidden xl:col-span-2"
            >
              <div className="console-section-header">
                <div className="flex items-center gap-2">
                  <BarChart3
                    className="h-4 w-4 text-[#123d73]"
                    aria-hidden="true"
                  />

                  <h2 className="font-semibold text-slate-900">
                    Findings Over Time
                  </h2>
                </div>

                <p className="mt-1 text-xs text-slate-500">
                  Trend view for available pipeline runs.
                </p>
              </div>

              <div className="p-5">
                <ErrorBoundary label="Trend panel">
                  <TrendPanel
                    currentRun={runId}
                    trends={[]}
                    hasPriorRun={runs.length > 1}
                  />
                </ErrorBoundary>
              </div>
            </section>
          </div>

          {/* Cross-CSE signal analysis */}
          <section
            aria-label="Cross-CSE pattern analysis"
            className="console-card overflow-hidden"
          >
            <div className="console-section-header">
              <div className="flex items-center gap-2">
                <Activity
                  className="h-4 w-4 text-[#123d73]"
                  aria-hidden="true"
                />

                <h2 className="font-semibold text-slate-900">
                  Cross-CSE Pattern Analysis
                </h2>
              </div>

              <p className="mt-1 text-xs text-slate-500">
                Signal visibility across monitored entities.
                Findings remain reviewable by the supervisor.
              </p>
            </div>

            <div className="p-5">
              <ErrorBoundary label="Signal heatmap">
                {queueQuery.error ? (
                  <ErrorState
                    error={
                      new Error(
                        'Signal data unavailable.',
                      )
                    }
                    retry={() =>
                      void queueQuery.refetch()
                    }
                  />
                ) : (
                  <SignalHeatmap
                    entities={entities}
                    signals={queueSignals}
                    findings={queueFindings}
                  />
                )}
              </ErrorBoundary>
            </div>
          </section>

          {/* Sector comparison + entity comparison */}
          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">

            <section
              aria-label="CSE comparison"
              className="console-card overflow-hidden"
            >
              <div className="console-section-header">
                <div className="flex items-center gap-2">
                  <CheckCircle2
                    className="h-4 w-4 text-[#123d73]"
                    aria-hidden="true"
                  />

                  <h2 className="font-semibold text-slate-900">
                    CSE View
                  </h2>
                </div>

                <p className="mt-1 text-xs text-slate-500">
                  Distribution of monitored entities.
                </p>
              </div>

              <div className="p-5">
                <ErrorBoundary label="Sector breakdown">
                  <SectorBreakdown entities={entities} />
                </ErrorBoundary>
              </div>
            </section>

            <section
              aria-label="Entity ranking"
              className="console-card overflow-hidden xl:col-span-2"
            >
              <div className="console-section-header">
                <div className="flex items-center gap-2">
                  <BarChart3
                    className="h-4 w-4 text-[#123d73]"
                    aria-hidden="true"
                  />

                  <h2 className="font-semibold text-slate-900">
                    Case / Entity Review
                  </h2>
                </div>

                <p className="mt-1 text-xs text-slate-500">
                  Comparative supervisory view for the selected
                  run.
                </p>
              </div>

              <div className="p-5">
                <ErrorBoundary label="Entity rank table">
                  <EntityRankTable
                    entities={entities}
                    isLoading={false}
                    runId={runId}
                  />
                </ErrorBoundary>
              </div>
            </section>
          </div>

          {/* Human decision notice */}
          <section className="rounded-lg border border-blue-200 bg-blue-50 px-5 py-4">
            <div className="flex items-start gap-3">
              <ShieldAlert
                className="mt-0.5 h-5 w-5 shrink-0 text-[#123d73]"
                aria-hidden="true"
              />

              <div>
                <h2 className="text-sm font-semibold text-[#123d73]">
                  Supervisory decision remains with the human expert
                </h2>

                <p className="mt-1 text-xs leading-5 text-blue-900/70">
                  SAT-SA surfaces evidence, standardized findings and
                  patterns for review. It does not independently
                  close, escalate or decide a case.
                </p>
              </div>
            </div>
          </section>

          {/* Footer */}
          <div className="flex flex-col justify-between gap-2 border-t border-slate-200 pt-4 text-[11px] text-slate-500 sm:flex-row">
            <span>
              SAT-SA · SOC Alert Triage & Security Analytics
            </span>

            <span>
              Advisory output · Human supervisory decision
            </span>
          </div>
        </div>
      ) : null}
    </div>
  );
}