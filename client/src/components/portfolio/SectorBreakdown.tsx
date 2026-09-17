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
export function SectorBreakdown({ entities, topSignals = {} }: SectorBreakdownProps) {
  const [expanded, setExpanded] = React.useState<Set<string>>(new Set());
  if (entities.length === 0) {
    return <EmptyState title="No sectors" description="No entities in this run." />;
  }
  const groups = new Map<string, Entity[]>();
  for (const entity of entities) {
    const list = groups.get(entity.sector) ?? [];
    list.push(entity);
    groups.set(entity.sector, list);
  }
  const sectors = [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));

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
    <table aria-label="Sector breakdown" className="w-full text-sm">
      <thead>
        <tr className="border-b border-slate-700 text-left text-slate-400">
          <th className="py-2 pr-2 font-medium">Sector</th>
          <th className="py-2 pr-2 font-medium">Entities</th>
          <th className="py-2 pr-2 font-medium">Avg Score</th>
          <th className="py-2 pr-2 font-medium">High Risk</th>
          <th className="py-2 font-medium">Top Signal</th>
        </tr>
      </thead>
      <tbody>
        {sectors.map(([sector, members]) => {
          const average = members.reduce((sum, entity) => sum + entity.overall_score, 0) / members.length;
          const highCount = members.filter((entity) => entity.band === 'HIGH').length;
          const open = expanded.has(sector);
          return (
            <React.Fragment key={sector}>
              <tr className="border-b border-slate-700">
                <td className="py-2 pr-2">
                  <button
                    type="button"
                    onClick={() => toggle(sector)}
                    aria-expanded={open}
                    aria-label={`${open ? 'Collapse' : 'Expand'} sector ${sector}`}
                    className="inline-flex items-center gap-1 rounded-sm text-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400"
                  >
                    {open ? (
                      <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                    ) : (
                      <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                    )}
                    {sector}
                  </button>
                </td>
                <td className="py-2 pr-2 text-slate-50">{members.length}</td>
                <td className="py-2 pr-2 text-slate-50">{formatScore(average)}</td>
                <td className="py-2 pr-2 text-slate-50">{highCount}</td>
                <td className="py-2 font-mono text-xs text-slate-400">{topSignals[sector] ?? '—'}</td>
              </tr>
              {open
                ? members.map((entity) => (
                    <tr key={entity.entity_id} className="border-b border-slate-800 bg-slate-900/50">
                      <td className="py-1.5 pl-8 pr-2 font-mono text-xs text-slate-400">
                        {entity.entity_id}
                      </td>
                      <td className="py-1.5 pr-2 text-xs text-slate-400">{formatScore(entity.overall_score)}</td>
                      <td colSpan={3} className="py-1.5">
                        <RiskBadge band={entity.band} size="sm" />
                      </td>
                    </tr>
                  ))
                : null}
            </React.Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
