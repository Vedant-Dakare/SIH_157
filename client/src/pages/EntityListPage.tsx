import { useSearchParams } from 'react-router-dom';
import { Download } from 'lucide-react';

import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingState } from '@/components/common/LoadingState';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { RiskBadge } from '@/components/common/RiskBadge';
import { PageHeader } from '@/components/layout/PageHeader';
import { EntityRankTable } from '@/components/portfolio/EntityRankTable';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useEntities } from '@/hooks/useEntities';
import { useRuns } from '@/hooks/useRuns';
import type { Entity, RiskBand } from '@/types/api';

const BANDS: RiskBand[] = ['HIGH', 'ELEVATED', 'MODERATE', 'LOW'];

/** Case Explorer: searchable, filterable entity worklist for one run. */
export default function EntityListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const runsQuery = useRuns();
  const runs = runsQuery.data?.runs ?? [];
  const runId = searchParams.get('run') ?? runs[0] ?? '';

  const entitiesQuery = useEntities(runId || undefined);
  const entities: Entity[] = entitiesQuery.data?.entities ?? [];

  function selectRun(next: string) {
    const params = new URLSearchParams(searchParams);
    params.set('run', next);
    setSearchParams(params);
  }

  function exportCsv(): void {
    const header = 'entity_id,band,sector,overall_score,confidence\n';
    const body = entities
      .map((entity) =>
        [
          entity.entity_id,
          entity.band,
          entity.sector,
          entity.overall_score,
          entity.confidence,
        ].join(','),
      )
      .join('\n');
    const blob = new Blob([header + body], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `entities-${runId || 'norun'}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const bandCounts = Object.fromEntries(
    BANDS.map((band) => [band, 0]),
  ) as Record<RiskBand, number>;
  for (const entity of entities) {
    bandCounts[entity.band] += 1;
  }

  return (
    <div>
      <PageHeader
        title="Case Explorer"
        description={
          runId
            ? `${entities.length} ${entities.length === 1 ? 'entity' : 'entities'} in run ${runId}. Search, filter and open any case for its findings.`
            : 'Browse every entity in the selected run.'
        }
        actions={
          <>
            <Select
              value={runId}
              onValueChange={selectRun}
              disabled={runs.length === 0}
            >
              <SelectTrigger
                className="h-9 w-44 border-[#D9E2EC] bg-white text-xs font-medium text-[#1F2933] hover:border-[#1F5F8B] focus:ring-1 focus:ring-[#1F5F8B]"
                aria-label="Select run"
              >
                <SelectValue
                  placeholder={runsQuery.isLoading ? 'Loading…' : 'No runs'}
                />
              </SelectTrigger>

              <SelectContent className="border-[#D9E2EC] bg-white text-xs">
                {runs.map((id) => (
                  <SelectItem
                    key={id}
                    value={id}
                    className="text-[#1F2933] focus:bg-[#EAF3F8] focus:text-[#123B5D]"
                  >
                    {id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={exportCsv}
              disabled={entities.length === 0}
              aria-label="Export entities as CSV"
              className="border-[#D9E2EC] bg-white text-[#123B5D] hover:bg-[#EAF3F8] hover:border-[#1F5F8B]"
            >
              <Download
                className="h-3.5 w-3.5"
                aria-hidden="true"
              />
              Export CSV
            </Button>
          </>
        }
      />

      {entitiesQuery.isLoading || runsQuery.isLoading ? (
        <LoadingState rows={6} message="Loading entities…" />
      ) : null}

      {entitiesQuery.error ? (
        <ErrorState
          error={
            entitiesQuery.error instanceof Error
              ? entitiesQuery.error
              : new Error('Entities unavailable.')
          }
          retry={() => void entitiesQuery.refetch()}
        />
      ) : null}

      {!entitiesQuery.isLoading && !entitiesQuery.error && !runId ? (
        <EmptyState
          title="No run selected"
          description="Pick a run to browse its entities."
        />
      ) : null}

      {!entitiesQuery.isLoading &&
      !entitiesQuery.error &&
      runId &&
      entities.length === 0 ? (
        <EmptyState
          title="No entities"
          description={`Run ${runId} contains no entities yet.`}
        />
      ) : null}

      {!entitiesQuery.isLoading &&
      !entitiesQuery.error &&
      entities.length > 0 ? (
        <div className="space-y-6">
          <section
            aria-label="Cases by risk band"
            className="console-card overflow-hidden"
          >
            <div className="console-section-header">
              <h2 className="font-semibold text-slate-900">
                Cases by Risk Band
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Distribution of entities in the selected run.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 p-5 sm:grid-cols-4">
              {BANDS.map((band) => (
                <div
                  key={band}
                  className="flex items-center justify-between gap-2 rounded-md border border-[#D9E2EC] bg-[#F8FAFC] px-3 py-2.5"
                >
                  <RiskBadge band={band} size="sm" />

                  <span className="text-xl font-bold tabular-nums text-[#123B5D]">
                    {bandCounts[band]}
                  </span>
                </div>
              ))}
            </div>
          </section>

          <section
            aria-label="All cases"
            className="console-card overflow-hidden"
          >
            <div className="console-section-header">
              <h2 className="font-semibold text-slate-900">
                All Cases
              </h2>

              <p className="mt-1 text-xs text-slate-500">
                Ranked by supervisory risk score. Select a row to open
                the case.
              </p>
            </div>

            <div className="p-5">
              <ErrorBoundary label="Case explorer table">
                <EntityRankTable
                  entities={entities}
                  isLoading={false}
                  runId={runId}
                  error={null}
                  onRetry={() => void entitiesQuery.refetch()}
                />
              </ErrorBoundary>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
