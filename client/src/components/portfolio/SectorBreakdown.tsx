import * as React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

import { EmptyState } from '@/components/common/EmptyState';
import { RiskBadge } from '@/components/common/RiskBadge';
import { formatScore } from '@/lib/utils';
import type { Entity } from '@/types/api';

export interface SectorBreakdownProps {
  entities: Entity[];
  topSignals?: Record<string, string>;
}

/** Sector table with expandable entity rows. Derived client-side. */
export function SectorBreakdown({
  entities,
  topSignals = {},
}: SectorBreakdownProps) {
  const [expanded, setExpanded] =
    React.useState<Set<string>>(new Set());

  if (entities.length === 0) {
    return (
      <EmptyState
        title="No sectors"
        description="No entities in this run."
      />
    );
  }

  const groups = new Map<string, Entity[]>();

  for (const entity of entities) {
    const list =
      groups.get(entity.sector) ?? [];

    list.push(entity);
    groups.set(entity.sector, list);
  }

  const sectors = [...groups.entries()].sort(
    (a, b) => a[0].localeCompare(b[0]),
  );

  function toggle(sector: string) {
    setExpanded((previous) => {
      const next = new Set(previous);

      if (next.has(sector)) {
        next.delete(sector);
      } else {
        next.add(sector);
      }

      return next;
    });
  }

  return (
    <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
      <table
        aria-label="Sector breakdown"
        className="w-full text-sm text-slate-900"
      >
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50 text-left">
            <th className="py-3 pl-3 pr-2 font-semibold text-slate-900">
              Sector
            </th>

            <th className="py-3 pr-2 font-semibold text-slate-900">
              Entities
            </th>

            <th className="py-3 pr-2 font-semibold text-slate-900">
              Avg Score
            </th>

            <th className="py-3 pr-2 font-semibold text-slate-900">
              High Risk
            </th>

            <th className="py-3 pr-3 font-semibold text-slate-900">
              Top Signal
            </th>
          </tr>
        </thead>

        <tbody>
          {sectors.map(([sector, members]) => {
            const average =
              members.reduce(
                (sum, entity) =>
                  sum + entity.overall_score,
                0,
              ) / members.length;

            const highCount = members.filter(
              (entity) => entity.band === 'HIGH',
            ).length;

            const open = expanded.has(sector);

            return (
              <React.Fragment key={sector}>
                <tr className="border-b border-slate-200 transition-colors hover:bg-blue-50/40">
                  <td className="py-3 pl-3 pr-2">
                    <button
                      type="button"
                      onClick={() => toggle(sector)}
                      aria-expanded={open}
                      aria-label={`${open ? 'Collapse' : 'Expand'} sector ${sector}`}
                      className="inline-flex items-center gap-1 rounded-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-300"
                    >
                      {open ? (
                        <ChevronDown
                          className="h-3.5 w-3.5 text-slate-700"
                          aria-hidden="true"
                        />
                      ) : (
                        <ChevronRight
                          className="h-3.5 w-3.5 text-slate-700"
                          aria-hidden="true"
                        />
                      )}

                      {sector}
                    </button>
                  </td>

                  <td className="py-3 pr-2 font-medium tabular-nums text-slate-900">
                    {members.length}
                  </td>

                  <td className="py-3 pr-2 font-medium tabular-nums text-slate-900">
                    {formatScore(average)}
                  </td>

                  <td className="py-3 pr-2 font-medium tabular-nums text-slate-900">
                    {highCount}
                  </td>

                  <td className="py-3 pr-3 font-mono text-xs font-medium text-slate-800">
                    {topSignals[sector] ?? '—'}
                  </td>
                </tr>

                {open
                  ? members.map((entity) => (
                      <tr
                        key={entity.entity_id}
                        className="border-b border-slate-100 bg-slate-50/70"
                      >
                        <td className="py-2 pl-9 pr-2 font-mono text-xs font-medium text-slate-800">
                          {entity.entity_id}
                        </td>

                        <td className="py-2 pr-2 text-xs font-medium text-slate-800">
                          {formatScore(
                            entity.overall_score,
                          )}
                        </td>

                        <td
                          colSpan={3}
                          className="py-2"
                        >
                          <RiskBadge
                            band={entity.band}
                            size="sm"
                          />
                        </td>
                      </tr>
                    ))
                  : null}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}