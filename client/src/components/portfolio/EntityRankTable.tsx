import * as React from 'react';
import { useNavigate } from 'react-router-dom';
import type { ColumnDef } from '@tanstack/react-table';
import { ArrowRight } from 'lucide-react';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { DataTable } from '@/components/common/DataTable';
import { RiskBadge } from '@/components/common/RiskBadge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { formatPercent, formatScore } from '@/lib/utils';
import type { Entity, RiskBand } from '@/types/api';

export interface EntityRankSupplement {
  signalsFired?: number;
  trend?: string;
  dataCompleteness?: number;
}

export interface EntityRankTableProps {
  entities: Entity[];
  isLoading: boolean;
  runId: string;
  error?: Error | null;
  onRetry?: () => void;
  supplement?: Record<string, EntityRankSupplement>;
}

interface RankRow extends Entity {
  rank: number;
  signalsFired: number | null;
  trend: string;
  dataCompleteness: number | null;
}

const BANDS: Array<RiskBand | 'ALL'> = ['ALL', 'HIGH', 'ELEVATED', 'MODERATE', 'LOW'];

/** Ranked entity table with band/sector filters and a separated low-evidence section. */
export function EntityRankTable({ entities, isLoading, runId, error, onRetry, supplement = {} }: EntityRankTableProps) {
  const navigate = useNavigate();
  const [bandFilter, setBandFilter] = React.useState<string>('ALL');
  const [sectorFilter, setSectorFilter] = React.useState<string>('ALL');
  const [onlyCustom, setOnlyCustom] = React.useState<boolean>(false);
  void runId;

  const sectors = React.useMemo(
    () => ['ALL', ...Array.from(new Set(entities.map((entity) => entity.sector))).sort()],
    [entities],
  );

  const customCount = React.useMemo(
    () => entities.filter((e) => !e.entity_id.startsWith('cse_') && !e.entity_id.startsWith('CSE_')).length,
    [entities],
  );

  const rows: RankRow[] = React.useMemo(() => {
    const filtered = entities.filter(
      (entity) =>
        (bandFilter === 'ALL' || entity.band === bandFilter) &&
        (sectorFilter === 'ALL' || entity.sector === sectorFilter) &&
        (!onlyCustom || (!entity.entity_id.startsWith('cse_') && !entity.entity_id.startsWith('CSE_'))),
    );
    const sorted = [...filtered].sort((a, b) => b.overall_score - a.overall_score);
    return sorted.map((entity, index) => {
      const extra = supplement[entity.entity_id];
      return {
        ...entity,
        rank: index + 1,
        signalsFired: extra?.signalsFired ?? null,
        trend: extra?.trend ?? '—',
        dataCompleteness: extra?.dataCompleteness ?? null,
      };
    });
  }, [entities, bandFilter, sectorFilter, onlyCustom, supplement]);

  const mainRows = rows.filter((row) => row.dataCompleteness === null || row.dataCompleteness >= 0.6);
  const insufficientRows = rows.filter(
    (row) => row.dataCompleteness !== null && row.dataCompleteness < 0.6,
  );

  const columns: ColumnDef<RankRow>[] = React.useMemo(
    () => [
      { accessorKey: 'rank', header: '#' },
      {
        accessorKey: 'entity_id',
        header: 'Entity ID',
        cell: (info) => {
          const id = info.getValue<string>();
          const isCustom = !id.startsWith('cse_') && !id.startsWith('CSE_');
          return (
            <div className="flex items-center gap-2">
              <span className="mono font-semibold text-slate-100">{id}</span>
              {isCustom ? (
                <span className="inline-flex items-center rounded border border-indigo-500/40 bg-indigo-950/80 px-1.5 py-0.5 text-[10px] font-semibold text-indigo-300">
                  Custom Upload
                </span>
              ) : null}
            </div>
          );
        },
      },
      { accessorKey: 'sector', header: 'Sector' },
      {
        accessorKey: 'band',
        header: 'Risk Band',
        cell: (info) => <RiskBadge band={info.getValue<RankRow['band']>()} size="sm" />,
      },
      {
        accessorKey: 'overall_score',
        header: 'Score',
        cell: (info) => formatScore(info.getValue<number>()),
      },
      {
        accessorKey: 'confidence',
        header: 'Confidence',
        cell: (info) => <ConfidenceBadge confidence={info.getValue<RankRow['confidence']>()} />,
      },
      {
        accessorKey: 'signalsFired',
        header: 'Signals Fired',
        cell: (info) => {
          const value = info.getValue<number | null>();
          return value === null ? '—' : String(value);
        },
      },
      { accessorKey: 'trend', header: 'Trend' },
      {
        accessorKey: 'dataCompleteness',
        header: 'Data Completeness',
        cell: (info) => {
          const value = info.getValue<number | null>();
          return value === null ? '—' : formatPercent(value);
        },
      },
      {
        id: 'actions',
        header: 'Actions',
        cell: (info) => (
          <Button
            type="button"
            variant="ghost"
            size="sm"
            aria-label={`View ${info.row.original.entity_id}`}
            onClick={(event) => {
              event.stopPropagation();
              navigate(`/entities/${info.row.original.entity_id}?run=${runId}`);
            }}
          >
            View <ArrowRight className="h-3 w-3" aria-hidden="true" />
          </Button>
        ),
      },
    ],
    [navigate, runId],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor="band-filter" className="text-xs text-slate-500">
            Band
          </label>
          <Select value={bandFilter} onValueChange={setBandFilter}>
            <SelectTrigger id="band-filter" className="h-8 w-36" aria-label="Filter by risk band">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {BANDS.map((band) => (
                <SelectItem key={band} value={band}>
                  {band}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <label htmlFor="sector-filter" className="text-xs text-slate-500">
            Sector
          </label>
          <Select value={sectorFilter} onValueChange={setSectorFilter}>
            <SelectTrigger id="sector-filter" className="h-8 w-40" aria-label="Filter by sector">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {sectors.map((sector) => (
                <SelectItem key={sector} value={sector}>
                  {sector}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {customCount > 0 ? (
          <div className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/80 p-1">
            <button
              type="button"
              onClick={() => setOnlyCustom(false)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                !onlyCustom ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All Entities ({entities.length})
            </button>
            <button
              type="button"
              onClick={() => setOnlyCustom(true)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                onlyCustom ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Custom Uploads ({customCount})
            </button>
          </div>
        ) : null}
      </div>
      <DataTable
        columns={columns}
        data={mainRows}
        isLoading={isLoading}
        error={error ?? null}
        onRetry={onRetry}
        onRowClick={(row) => navigate(`/entities/${row.entity_id}?run=${runId}`)}
        getRowClassName={(row) => (row.band === 'HIGH' ? 'bg-red-950/40' : '')}
      />
      {insufficientRows.length > 0 ? (
        <section aria-label="Insufficient evidence entities">
          <div role="note" className="mb-3 rounded-md border border-yellow-500 bg-yellow-950 px-4 py-3 text-sm text-yellow-500">
            These entities are <strong>not ranked</strong>: data completeness below 60% means
            scores could falsely accuse. Verify the feed before reviewing.
          </div>
          <DataTable
            columns={columns}
            data={insufficientRows}
            isLoading={false}
            error={null}
            onRowClick={(row) => navigate(`/entities/${row.entity_id}?run=${runId}`)}
          />
        </section>
      ) : null}
    </div>
  );
}
