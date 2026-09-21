import * as React from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { TrendLine } from '@/components/charts/TrendLine';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingState } from '@/components/common/LoadingState';
import { DataQualityCard } from '@/components/entity/DataQualityCard';
import { DomainScorePanel } from '@/components/entity/DomainScorePanel';
import { EntityHeader } from '@/components/entity/EntityHeader';
import { FindingsTable, type FindingRow } from '@/components/entity/FindingsTable';
import { NegativeSpaceMap } from '@/components/entity/NegativeSpaceMap';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { useEntity, useFindings } from '@/hooks/useFindings';
import { useQueue } from '@/hooks/useQueue';

/** Entity deep-dive: header, tabbed overview/findings/coverage/quality. */
export default function EntityDetailPage() {
  const { entityId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const runId = searchParams.get('run') ?? '';
  const [signalFilter, setSignalFilter] = React.useState<string[] | null>(null);

  const entityQuery = useEntity(entityId, runId || undefined);
  const findingsQuery = useFindings(entityId, runId || undefined);
  const queueQuery = useQueue(runId || undefined);

  if (!entityId || !runId) {
    return (
      <EmptyState
        title="No entity selected"
        description="Choose an entity from the portfolio with a run selected."
      />
    );
  }
  if (entityQuery.isLoading || findingsQuery.isLoading) {
    return <LoadingState rows={8} message="Loading entity…" />;
  }
  if (entityQuery.error || !entityQuery.data) {
    return (
      <ErrorState
        error={entityQuery.error instanceof Error ? entityQuery.error : new Error('Entity not found.')}
        retry={() => void entityQuery.refetch()}
      />
    );
  }
  const entity = entityQuery.data.entity;
  const rows: FindingRow[] = (findingsQuery.data?.findings ?? []).map((summary) => ({
    finding_id: summary.finding_id,
    entity_id: summary.entity_id,
    signal_id: summary.signal_id,
    observed: 0,
    threshold: 0,
    severity: summary.severity,
    confidence: summary.confidence,
    score: 0,
    band: entity.band,
    window: entity.window,
    label: summary.signal_id,
    plain_language: '',
    peer_baseline: {},
    supporting_rows: [],
    counter_rows: [],
    counter_absent_reason: '',
    evidence_id: '',
    audit_ref: '',
    is_flagged: true,
    confidence_reason: '',
  }));

  const inQueue = (queueQuery.data?.queue ?? []).some((item) => item.entity_id === entityId);
  const backTo = `/portfolio${runId ? `?run=${encodeURIComponent(runId)}` : ''}`;

  return (
    <div className="space-y-6">
      <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-xs text-[#52606D]">
        <Link
          to={backTo}
          className="rounded border border-[#D9E2EC] bg-white px-2.5 py-1 text-xs font-medium text-[#123B5D] hover:bg-[#EAF3F8] hover:border-[#1F5F8B] transition-colors"
        >
          Portfolio
        </Link>
        <span aria-hidden="true" className="text-slate-400">›</span>
        <span className="mono font-semibold text-[#1F2933]">{entityId}</span>
        <button
          type="button"
          onClick={() => navigate(backTo)}
          className="ml-2 inline-flex items-center gap-1 rounded border border-[#D9E2EC] bg-white px-2.5 py-1 text-xs font-medium text-[#123B5D] hover:bg-[#EAF3F8] hover:border-[#1F5F8B] transition-colors focus:outline-none focus:ring-2 focus:ring-[#1F5F8B]"
        >
          Back
        </button>
      </nav>

      <EntityHeader entity={entity} runId={runId} isInQueue={inQueue} />

      <Tabs defaultValue="overview">
        <TabsList aria-label="Entity sections">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="findings">Findings</TabsTrigger>
          <TabsTrigger value="coverage">Coverage</TabsTrigger>
          <TabsTrigger value="quality">Data Quality</TabsTrigger>
        </TabsList>
        <TabsContent forceMount value="overview">
          <ErrorBoundary label="overview panel">

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-5">
              <div className="console-card p-4 xl:col-span-3 sm:p-5">
                <DomainScorePanel
                  domainScores={Object.entries(entity.domain_scores).map(([domain, score]) => ({
                    domain,
                    score,
                    contribution: entity.domain_contributions[domain] ?? 0,
                    signals: entity.domain_members[domain] ?? [],
                  }))}
                  overallScore={entity.overall_score}
                  selectedSignals={signalFilter}
                  onSelectDomain={(_domain, signals) => setSignalFilter(signals)}
                />
              </div>
              <div className="console-card p-4 xl:col-span-2 sm:p-5">
                <TrendLine data={[]} entityId={entityId} isLoading={false} />
              </div>
            </div>
          </ErrorBoundary>
        </TabsContent>
        <TabsContent forceMount value="findings">
          <ErrorBoundary label="findings panel">

            <FindingsTable
              findings={rows}
              isLoading={false}
              signalFilter={signalFilter}
              onClearSignalFilter={() => setSignalFilter(null)}
              onSelect={(finding) =>
                navigate(`/findings/${finding.finding_id}?run=${encodeURIComponent(runId)}`)
              }
            />
          </ErrorBoundary>
        </TabsContent>
        <TabsContent forceMount value="coverage">
          <ErrorBoundary label="coverage panel">

            <NegativeSpaceMap entityId={entityId} runId={runId} />
          </ErrorBoundary>
        </TabsContent>
        <TabsContent forceMount value="quality">
          <ErrorBoundary label="quality panel">

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <div className="console-card p-4 sm:p-5">
                <DataQualityCard cseId={entityId} runId={runId} />
              </div>
              <div className="console-card p-4 sm:p-5">
                <h3 className="mb-2 text-sm font-semibold text-slate-900">Quarantine breakdown</h3>
                <p className="text-sm text-slate-600">
                  Completeness {Math.round(entity.data_completeness * 100)}%
                  {entity.capped_by_completeness ? ' — capped due to completeness threshold.' : '.'}
                </p>
              </div>
            </div>
          </ErrorBoundary>
        </TabsContent>
      </Tabs>
    </div>
  );
}
