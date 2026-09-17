import * as React from 'react';
import { Check, ChevronDown, ChevronRight, X } from 'lucide-react';

import { EmptyState } from '@/components/common/EmptyState';
import { LoadingState } from '@/components/common/LoadingState';
import { HashDisplay } from '@/components/common/HashDisplay';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { formatDate } from '@/lib/utils';
import { verifyEntry } from '@/lib/ledgerHash';
import type { AuditEntry } from '@/types/api';

export interface LedgerTableProps {
  entries: AuditEntry[];
  isLoading: boolean;
}

type Verdict = 'pending' | 'ok' | 'tampered' | 'unavailable';

/** Ledger with client-side hash re-computation, filters and payload expand. */
export function LedgerTable({ entries, isLoading }: LedgerTableProps) {
  const [runFilter, setRunFilter] = React.useState('ALL');
  const [typeFilter, setTypeFilter] = React.useState('ALL');
  const [expanded, setExpanded] = React.useState<Set<number>>(new Set());
  const [verdicts, setVerdicts] = React.useState<Record<number, Verdict>>({});

  const runIds = React.useMemo(() => ['ALL', ...Array.from(new Set(entries.map((e) => e.run_id)))], [entries]);
  const eventTypes = React.useMemo(
    () => ['ALL', ...Array.from(new Set(entries.map((e) => e.event_type)))],
    [entries],
  );
  const visible = entries.filter(
    (entry) =>
      (runFilter === 'ALL' || entry.run_id === runFilter) &&
      (typeFilter === 'ALL' || entry.event_type === typeFilter),
  );

  React.useEffect(() => {
    let cancelled = false;
    async function verifyAll() {
      const next: Record<number, Verdict> = {};
      const ordered = [...entries].sort((a, b) => a.seq - b.seq);
      for (const entry of ordered) {
        const previous = ordered.find((candidate) => candidate.seq === entry.seq - 1);
        const expectedPrev = entry.seq === 0 ? '0'.repeat(64) : (previous?.entry_hash ?? '');
        try {
          const { hashOk, linkOk } = await verifyEntry(entry, expectedPrev);
          next[entry.seq] = hashOk && linkOk ? 'ok' : 'tampered';
        } catch {
          next[entry.seq] = 'unavailable';
        }
        if (cancelled) {
          return;
        }
      }
      if (!cancelled) {
        setVerdicts(next);
      }
    }
    if (entries.length > 0) {
      void verifyAll();
    }
    return () => {
      cancelled = true;
    };
  }, [entries]);

  function toggle(seq: number) {
    setExpanded((previous) => {
      const next = new Set(previous);
      if (next.has(seq)) {
        next.delete(seq);
      } else {
        next.add(seq);
      }
      return next;
    });
  }

  if (isLoading) {
    return <LoadingState rows={6} message="Loading ledger…" />;
  }
  if (entries.length === 0) {
    return <EmptyState title="No entries" description="The audit ledger is empty." />;
  }

  return (
    <div className="max-h-[480px] space-y-3 overflow-y-auto">
      <div className="sticky top-0 flex flex-wrap gap-2 bg-slate-950 py-2">
        <Select value={runFilter} onValueChange={setRunFilter}>
          <SelectTrigger className="h-8 w-40" aria-label="Filter by run">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {runIds.map((id) => (
              <SelectItem key={id} value={id}>
                {id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="h-8 w-44" aria-label="Filter by event type">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {eventTypes.map((type) => (
              <SelectItem key={type} value={type}>
                {type}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="overflow-x-auto rounded-md border border-slate-700">
        <table aria-label="Audit ledger" className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-700 text-left text-slate-400">
              <th className="w-8" aria-label="Expand" />
              <th className="px-2 py-2 font-medium">Seq</th>
              <th className="px-2 py-2 font-medium">Run ID</th>
              <th className="px-2 py-2 font-medium">Timestamp</th>
              <th className="px-2 py-2 font-medium">Event Type</th>
              <th className="px-2 py-2 font-medium">Entry Hash</th>
              <th className="px-2 py-2 font-medium">Prev Hash</th>
              <th className="px-2 py-2 font-medium">Valid</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((entry) => {
              const verdict = verdicts[entry.seq] ?? 'pending';
              const open = expanded.has(entry.seq);
              return (
                <React.Fragment key={entry.seq}>
                  <tr className="border-b border-slate-800">
                    <td className="px-2 py-1.5">
                      <button
                        type="button"
                        onClick={() => toggle(entry.seq)}
                        aria-expanded={open}
                        aria-label={`${open ? 'Collapse' : 'Expand'} entry ${entry.seq}`}
                        className="rounded-sm p-1 text-slate-400 hover:text-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400"
                      >
                        {open ? <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" /> : <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />}
                      </button>
                    </td>
                    <td className="px-2 py-1.5 text-slate-50">{entry.seq}</td>
                    <td className="mono max-w-32 truncate px-2 py-1.5 text-slate-400" title={entry.run_id}>
                      {entry.run_id}
                    </td>
                    <td className="whitespace-nowrap px-2 py-1.5 text-slate-400">{formatDate(entry.ts)}</td>
                    <td className="px-2 py-1.5">
                      <Badge variant="secondary">{entry.event_type}</Badge>
                    </td>
                    <td className="px-2 py-1.5">
                      <HashDisplay hash={entry.entry_hash} />
                    </td>
                    <td className="px-2 py-1.5">
                      <HashDisplay hash={entry.prev_hash} />
                    </td>
                    <td className="px-2 py-1.5" aria-label={`Entry ${entry.seq} ${verdict}`}>
                      {verdict === 'ok' ? (
                        <Check className="h-4 w-4 text-green-500" aria-hidden="true" />
                      ) : verdict === 'tampered' ? (
                        <X className="h-4 w-4 text-red-500" aria-hidden="true" />
                      ) : (
                        <span className="text-slate-500">…</span>
                      )}
                    </td>
                  </tr>
                  {open ? (
                    <tr className="border-b border-slate-700 bg-slate-900/60">
                      <td />
                      <td colSpan={7} className="px-2 py-2">
                        <pre className="mono max-h-48 overflow-auto whitespace-pre-wrap text-xs text-slate-50">
                          {JSON.stringify(entry.payload, null, 2)}
                        </pre>
                      </td>
                    </tr>
                  ) : null}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
