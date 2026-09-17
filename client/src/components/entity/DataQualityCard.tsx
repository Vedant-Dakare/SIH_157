import * as React from 'react';
import { AlertTriangle } from 'lucide-react';

import { EmptyState } from '@/components/common/EmptyState';
import { LoadingState } from '@/components/common/LoadingState';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { formatPercent } from '@/lib/utils';

export interface DataQualityStats {
  total: number;
  valid: number;
  quarantined: number;
  quarantineRate: number;
  topReasons: Array<{ reason: string; count: number }>;
  trend: number[];
}

export interface DataQualityCardProps {
  cseId: string;
  runId: string;
  quality?: DataQualityStats;
  quarantineRecords?: Array<Record<string, unknown>>;
  isLoading?: boolean;
}

/** Ingestion scorecard with quarantine dialog. Empty when the run has no data. */
export function DataQualityCard({ cseId, runId, quality, quarantineRecords = [], isLoading = false }: DataQualityCardProps) {
  void runId;
  const [dialogOpen, setDialogOpen] = React.useState(false);
  if (isLoading) {
    return <LoadingState rows={4} message="Loading data quality…" />;
  }
  if (!quality) {
    return (
      <EmptyState
        title="No ingestion data"
        description={`${cseId} has no ingestion scorecard in this run.`}
      />
    );
  }
  const maxReason = Math.max(1, ...quality.topReasons.map((entry) => entry.count));
  const elevated = quality.quarantineRate > 0.1;
  return (
    <div className="space-y-4" aria-label={`Data quality for ${cseId}`}>
      <dl className="grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <dt className="text-xs text-slate-500">Total received</dt>
          <dd className="text-xl font-bold text-slate-50">{quality.total}</dd>
        </div>
        <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <dt className="text-xs text-slate-500">Valid</dt>
          <dd className="text-xl font-bold text-green-500">{quality.valid}</dd>
        </div>
        <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <dt className="text-xs text-slate-500">Quarantined</dt>
          <dd className={`text-xl font-bold ${elevated ? 'text-red-500' : 'text-slate-50'}`}>
            {quality.quarantined}
          </dd>
        </div>
        <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
          <dt className="text-xs text-slate-500">Quarantine rate</dt>
          <dd className={`text-xl font-bold ${elevated ? 'text-red-500' : 'text-slate-50'}`}>
            {formatPercent(quality.quarantineRate)}
          </dd>
        </div>
      </dl>
      {elevated ? (
        <p role="note" className="flex items-center gap-2 rounded-md border border-red-500 bg-red-950 px-3 py-2 text-sm text-red-500">
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          Quarantine rate above 10% — verify the feed before trusting scores.
        </p>
      ) : null}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Top quarantine reasons
        </h4>
        {quality.topReasons.length === 0 ? (
          <p className="text-sm text-slate-500">No quarantine reasons recorded.</p>
        ) : (
          <ul className="space-y-2">
            {quality.topReasons.slice(0, 3).map((entry) => (
              <li key={entry.reason}>
                <div className="mb-1 flex justify-between text-xs text-slate-400">
                  <span className="font-mono">{entry.reason}</span>
                  <span>{entry.count}</span>
                </div>
                <div
                  role="progressbar"
                  aria-valuenow={entry.count}
                  aria-valuemin={0}
                  aria-valuemax={maxReason}
                  aria-label={`${entry.reason} count`}
                  className="h-2 w-full overflow-hidden rounded-full bg-slate-800"
                >
                  <div className="h-full bg-yellow-500" style={{ width: `${(entry.count / maxReason) * 100}%` }} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Feed health (last 3 runs)
        </h4>
        {quality.trend.length === 0 ? (
          <p className="text-sm text-slate-500">No trend history yet.</p>
        ) : (
          <svg role="img" aria-label="Feed health sparkline" width="180" height="36" className="overflow-visible">
            <polyline
              points={quality.trend
                .map((value, index) => {
                  const x = quality.trend.length === 1 ? 90 : (index / (quality.trend.length - 1)) * 176 + 2;
                  const y = 34 - Math.max(0, Math.min(1, value)) * 32;
                  return `${x.toFixed(1)},${y.toFixed(1)}`;
                })
                .join(' ')}
              fill="none"
              stroke="#22c55e"
              strokeWidth="2"
            />
          </svg>
        )}
      </div>
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogTrigger asChild>
          <Button type="button" variant="outline" size="sm">
            View Quarantine Details
          </Button>
        </DialogTrigger>
        <DialogContent aria-label="Quarantine records">
          <DialogHeader>
            <DialogTitle>Quarantine records for {cseId}</DialogTitle>
          </DialogHeader>
          {quarantineRecords.length === 0 ? (
            <p className="text-sm text-slate-400">No quarantine records in this run.</p>
          ) : (
            <ul className="max-h-96 space-y-2 overflow-y-auto">
              {quarantineRecords.map((record, index) => (
                <li key={index} className="mono rounded-sm bg-slate-800 p-2 text-xs text-slate-50">
                  {JSON.stringify(record)}
                </li>
              ))}
            </ul>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
