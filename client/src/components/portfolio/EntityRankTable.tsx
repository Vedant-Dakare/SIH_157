import * as React from 'react';
import { useNavigate } from 'react-router-dom';
import type { ColumnDef } from '@tanstack/react-table';
import { ArrowRight } from 'lucide-react';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { DataTable } from '@/components/common/DataTable';
import { RiskBadge } from '@/components/common/RiskBadge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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

const BANDS: Array<RiskBand | 'ALL'> = [
  'ALL',
  'HIGH',
  'ELEVATED',
  'MODERATE',
  'LOW',
];

/** Ranked entity table with band/sector filters and a separated low-evidence section. */
export function EntityRankTable({
  entities,
  isLoading,
  runId,
  error,
  onRetry,
  supplement = {},
}: EntityRankTableProps) {
  const navigate = useNavigate();
  const [bandFilter, setBandFilter] = React.useState<string>('ALL');
  const [sectorFilter, setSectorFilter] = React.useState<string>('ALL');
  const [onlyCustom, setOnlyCustom] = React.useState<boolean>(false);

  void runId;

  const sectors = React.useMemo(
    () => [
      'ALL',
      ...Array.from(
        new Set(entities.map((entity) => entity.sector)),
      ).sort(),
    ],
    [entities],
  );

  const customCount = React.useMemo(
    () =>
      entities.filter(
        (e) =>
          !e.entity_id.startsWith('cse_') &&
          !e.entity_id.startsWith('CSE_'),
      ).length,
    [entities],
  );

  const rows: RankRow[] = React.useMemo(() => {
    const filtered = entities.filter(
      (entity) =>
        (bandFilter === 'ALL' || entity.band === bandFilter) &&
        (sectorFilter === 'ALL' ||
          entity.sector === sectorFilter) &&
        (!onlyCustom ||
          (!entity.entity_id.startsWith('cse_') &&
            !entity.entity_id.startsWith('CSE_'))),
    );

    const sorted = [...filtered].sort(
      (a, b) => b.overall_score - a.overall_score,
    );

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
  }, [
    entities,
    bandFilter,
    sectorFilter,
    onlyCustom,
    supplement,
  ]);

  const mainRows = rows.filter(
    (row) =>
      row.dataCompleteness === null ||
      row.dataCompleteness >= 0.6,
  );

  const insufficientRows = rows.filter(
    (row) =>
      row.dataCompleteness !== null &&
      row.dataCompleteness < 0.6,
  );

  const columns: ColumnDef<RankRow>[] = React.useMemo(
    () => [
      {
        accessorKey: 'rank',
        header: '#',
        cell: (info) => (
          <span className="font-medium text-slate-900">
            {info.getValue<number>()}
          </span>
        ),
      },
      {
        accessorKey: 'entity_id',
        header: 'Entity ID',
        cell: (info) => {
          const id = info.getValue<string>();

          const isCustom =
            !id.startsWith('cse_') &&
            !id.startsWith('CSE_');

          return (
            <div className="flex items-center gap-2">
              <span className="mono font-semibold text-slate-900">
                {id}
              </span>

              {isCustom ? (
                <span className="inline-flex items-center rounded border border-blue-200 bg-blue-50 px-1.5 py-0.5 text-[10px] font-semibold text-[#2563A8]">
                  Custom Upload
                </span>
              ) : null}
            </div>
          );
        },
      },
      {
        accessorKey: 'sector',
        header: 'Sector',
        cell: (info) => (
          <span className="font-medium text-slate-900">
            {info.getValue<string>()}
          </span>
        ),
      },
      {
        accessorKey: 'band',
        header: 'Risk Band',
        cell: (info) => (
          <RiskBadge
            band={info.getValue<RankRow['band']>()}
            size="sm"
          />
        ),
      },
      {
        accessorKey: 'overall_score',
        header: 'Score',
        cell: (info) => (
          <span className="tabular-nums font-medium text-slate-900">
            {formatScore(info.getValue<number>())}
          </span>
        ),
      },
      {
        accessorKey: 'confidence',
        header: 'Confidence',
        cell: (info) => (
          <ConfidenceBadge
            confidence={info.getValue<RankRow['confidence']>()}
          />
        ),
      },
      {
        accessorKey: 'signalsFired',
        header: 'Signals Fired',
        cell: (info) => {
          const value =
            info.getValue<number | null>();

          return (
            <span className="text-slate-900">
              {value === null ? '—' : String(value)}
            </span>
          );
        },
      },
      {
        accessorKey: 'trend',
        header: 'Trend',
        cell: (info) => (
          <span className="text-slate-900">
            {info.getValue<string>()}
          </span>
        ),
      },
      {
        accessorKey: 'dataCompleteness',
        header: 'Data Completeness',
        cell: (info) => {
          const value =
            info.getValue<number | null>();

          return (
            <span className="text-slate-900">
              {value === null
                ? '—'
                : formatPercent(value)}
            </span>
          );
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
            className="text-[#123D73] hover:bg-blue-50 hover:text-[#123D73]"
            aria-label={`View ${info.row.original.entity_id}`}
            onClick={(event) => {
              event.stopPropagation();

              navigate(
                `/entities/${info.row.original.entity_id}?run=${runId}`,
              );
            }}
          >
            View
            
          </Button>
        ),
      },
    ],
    [navigate, runId],
  );

  return (
    <div className="space-y-6 text-slate-900">
      {/* Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <label
            htmlFor="band-filter"
            className="text-xs font-medium text-slate-900"
          >
            Band
          </label>

          <Select
            value={bandFilter}
            onValueChange={setBandFilter}
          >
            <SelectTrigger
              id="band-filter"
              className="h-8 w-36 border-slate-300 bg-white text-slate-900"
              aria-label="Filter by risk band"
            >
              <SelectValue />
            </SelectTrigger>

            <SelectContent>
              {BANDS.map((band) => (
                <SelectItem
                  key={band}
                  value={band}
                >
                  {band}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <label
            htmlFor="sector-filter"
            className="text-xs font-medium text-slate-900"
          >
            Sector
          </label>

          <Select
            value={sectorFilter}
            onValueChange={setSectorFilter}
          >
            <SelectTrigger
              id="sector-filter"
              className="h-8 w-40 border-slate-300 bg-white text-slate-900"
              aria-label="Filter by sector"
            >
              <SelectValue />
            </SelectTrigger>

            <SelectContent>
              {sectors.map((sector) => (
                <SelectItem
                  key={sector}
                  value={sector}
                >
                  {sector}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {customCount > 0 ? (
          <div className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 p-1">
            <button
              type="button"
              onClick={() => setOnlyCustom(false)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                !onlyCustom
                  ? 'bg-[#123D73] text-white shadow-sm'
                  : 'text-slate-700 hover:bg-white hover:text-slate-900'
              }`}
            >
              All Entities ({entities.length})
            </button>

            <button
              type="button"
              onClick={() => setOnlyCustom(true)}
              className={`rounded px-2.5 py-1 text-xs font-medium transition-colors ${
                onlyCustom
                  ? 'bg-[#123D73] text-white shadow-sm'
                  : 'text-slate-700 hover:bg-white hover:text-slate-900'
              }`}
            >
              Custom Uploads ({customCount})
            </button>
          </div>
        ) : null}
      </div>

      {/* Main table */}
      <DataTable
        columns={columns}
        data={mainRows}
        isLoading={isLoading}
        error={error ?? null}
        onRetry={onRetry}
        onRowClick={(row) =>
          navigate(
            `/entities/${row.entity_id}?run=${runId}`,
          )
        }
        getRowClassName={(row) =>
          row.band === 'HIGH'
            ? 'bg-blue-50/50'
            : ''
        }
      />

      {/* Insufficient evidence */}
      {insufficientRows.length > 0 ? (
        <section aria-label="Insufficient evidence entities">
          <div
            role="note"
            className="mb-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-slate-900"
          >
            These entities are{' '}
            <strong>not ranked</strong>: data
            completeness below 60% means scores could
            falsely accuse. Verify the feed before
            reviewing.
          </div>

          <DataTable
            columns={columns}
            data={insufficientRows}
            isLoading={false}
            error={null}
            onRowClick={(row) =>
              navigate(
                `/entities/${row.entity_id}?run=${runId}`,
              )
            }
          />
        </section>
      ) : null}
    </div>
  );
}