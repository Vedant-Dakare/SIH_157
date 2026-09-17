import { ArrowUp, Equal, Plus } from 'lucide-react';

import { EmptyState } from '@/components/common/EmptyState';

export type TrendKind = 'NEW' | 'RESOLVED' | 'PERSISTENT' | 'IMPROVING';

export interface TrendDatum {
  kind: TrendKind;
  entityId: string;
  signalId?: string;
  label: string;
}

export interface TrendPanelProps {
  currentRun: string;
  trends: TrendDatum[];
  hasPriorRun?: boolean;
}

const KIND_STYLE: Record<TrendKind, { icon: typeof Plus; colour: string; prefix: string }> = {
  NEW: { icon: Plus, colour: 'text-green-500', prefix: '+' },
  RESOLVED: { icon: Equal, colour: 'text-slate-500', prefix: '−' },
  PERSISTENT: { icon: Equal, colour: 'text-yellow-500', prefix: '=' },
  IMPROVING: { icon: ArrowUp, colour: 'text-green-500', prefix: '↑' },
};

/** Current-vs-prior run comparison grouped by trend kind. */
export function TrendPanel({ currentRun, trends, hasPriorRun = true }: TrendPanelProps) {
  if (!hasPriorRun) {
    return (
      <EmptyState
        title="No prior run"
        description="No prior run available for trend comparison."
      />
    );
  }
  const groups: Record<TrendKind, TrendDatum[]> = { NEW: [], RESOLVED: [], PERSISTENT: [], IMPROVING: [] };
  for (const trend of trends) {
    groups[trend.kind].push(trend);
  }
  if (trends.length === 0) {
    return (
      <EmptyState
        title="No changes"
        description={`${currentRun} matches the prior run exactly.`}
      />
    );
  }
  const order: TrendKind[] = ['NEW', 'IMPROVING', 'PERSISTENT', 'RESOLVED'];
  return (
    <div aria-label={`Trend comparison for ${currentRun}`} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      {order.map((kind) => {
        const Icon = KIND_STYLE[kind].icon;
        return (
          <div key={kind} className="rounded-md border border-slate-700 bg-slate-900 p-3">
            <h4 className={`mb-2 flex items-center gap-1.5 text-xs font-semibold ${KIND_STYLE[kind].colour}`}>
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              {kind} ({groups[kind].length})
            </h4>
            {groups[kind].length === 0 ? (
              <p className="text-xs text-slate-500">None</p>
            ) : (
              <ul className="space-y-1">
                {groups[kind].map((trend, index) => (
                  <li key={`${trend.entityId}-${trend.signalId ?? index}`} className="font-mono text-xs text-slate-400">
                    {trend.label}
                  </li>
                ))}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}
