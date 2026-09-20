import * as React from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '@/components/common/EmptyState';
import { LoadingState } from '@/components/common/LoadingState';
import { cn } from '@/lib/utils';

export type CoverageState = 'COVERED' | 'PARTIAL' | 'ABSENT' | 'NA';

export interface CoverageCell {
  assetType: string;
  sourceType: string;
  state: CoverageState;
  critical: boolean;
  signalId?: string;
  findingId?: string;
}

export interface NegativeSpaceMapProps {
  entityId: string;
  runId: string;
  cells?: CoverageCell[];
  isLoading?: boolean;
}

const STATE_STYLE: Record<CoverageState, { bg: string; glyph: string; label: string }> = {
  COVERED: { bg: 'bg-emerald-100 text-emerald-900', glyph: '✓', label: 'Covered' },
  PARTIAL: { bg: 'bg-amber-100 text-amber-900', glyph: '⚠', label: 'Partial' },
  ABSENT: { bg: 'bg-red-100 text-red-900', glyph: '✗', label: 'Absent' },
  NA: { bg: 'bg-slate-100 text-slate-500', glyph: '—', label: 'Not applicable' },
};

/** Asset × source coverage grid derived from NS findings (or explicit cells). */
export function NegativeSpaceMap({ entityId, runId, cells, isLoading = false }: NegativeSpaceMapProps) {
  const [criticalOnly, setCriticalOnly] = React.useState(false);
  void runId;
  if (isLoading) {
    return <LoadingState rows={4} message="Loading coverage map…" />;
  }
  const all = cells ?? [];
  if (all.length === 0) {
    return (
      <EmptyState
        title="No coverage data"
        description={`${entityId} has no negative-space findings in this run, so there is no gap map to show.`}
      />
    );
  }
  const visible = criticalOnly ? all.filter((cell) => cell.critical) : all;
  const assetTypes = Array.from(new Set(visible.map((cell) => cell.assetType))).sort();
  const sourceTypes = Array.from(new Set(visible.map((cell) => cell.sourceType))).sort();
  const byCell = new Map(visible.map((cell) => [`${cell.assetType}|${cell.sourceType}`, cell]));

  function average(filter: (cell: CoverageCell) => boolean): string {
    const subset = visible.filter(filter);
    if (subset.length === 0) {
      return '—';
    }
    const scored = subset.filter((cell) => cell.state !== 'NA');
    if (scored.length === 0) {
      return '—';
    }
    const points = scored.reduce((sum, cell) => sum + (cell.state === 'COVERED' ? 1 : cell.state === 'PARTIAL' ? 0.5 : 0), 0);
    return `${Math.round((points / scored.length) * 100)}%`;
  }

  return (
    <div className="space-y-3">
      <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
        <input
          type="checkbox"
          checked={criticalOnly}
          onChange={(event) => setCriticalOnly(event.target.checked)}
          className="h-4 w-4 accent-[#123D73]"
        />
        Show only CRITICAL assets
      </label>
      <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
        <table aria-label={`Coverage map for ${entityId}`} className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="p-2 text-left font-medium text-slate-600">Asset \ Source</th>
              {sourceTypes.map((source) => (
                <th key={source} className="p-2 font-mono text-xs font-medium text-slate-600">
                  {source}
                </th>
              ))}
              <th className="p-2 font-medium text-slate-600">Row score</th>
            </tr>
          </thead>
          <tbody>
            {assetTypes.map((asset) => (
              <tr key={asset} className="border-b border-slate-100 last:border-0">
                <th className="p-2 text-left font-mono text-xs font-medium text-slate-800">{asset}</th>
                {sourceTypes.map((source) => {
                  const cell = byCell.get(`${asset}|${source}`);
                  const state = cell?.state ?? 'NA';
                  const style = STATE_STYLE[state];
                  const inner = (
                    <span aria-hidden="true">
                      {style.glyph} {style.label}
                    </span>
                  );
                  return (
                    <td key={source} className={cn('border border-white p-2 text-center text-xs font-medium', style.bg)}>
                      {cell?.findingId ? (
                        <Link
                          to={`/findings/${cell.findingId}`}
                          aria-label={`${asset} ${source}: ${style.label}${cell.signalId ? `, covered by ${cell.signalId}` : ''}. Open finding.`}
                          className="underline underline-offset-2 focus:outline-none focus:ring-2 focus:ring-blue-300"
                        >
                          {inner}
                        </Link>
                      ) : (
                        <span aria-label={`${asset} ${source}: ${style.label}`}>{inner}</span>
                      )}
                    </td>
                  );
                })}
                <td className="p-2 text-center text-xs text-slate-500">
                  {average((cell) => cell.assetType === asset)}
                </td>
              </tr>
            ))}
            <tr className="border-t border-slate-200 bg-slate-50">
              <th className="p-2 text-left text-xs font-medium text-slate-600">Column score</th>
              {sourceTypes.map((source) => (
                <td key={source} className="p-2 text-center text-xs text-slate-500">
                  {average((cell) => cell.sourceType === source)}
                </td>
              ))}
              <td />
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
