import * as React from 'react';
import { Check, ChevronDown, ChevronRight, X } from 'lucide-react';

import { EmptyState } from '@/components/common/EmptyState';
import { LoadingState } from '@/components/common/LoadingState';
import { HashDisplay } from '@/components/common/HashDisplay';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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

  const runIds = React.useMemo(
    () => ['ALL', ...Array.from(new Set(entries.map((e) => e.run_id)))],
    [entries],
  );

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
        const previous = ordered.find(
          (candidate) => candidate.seq === entry.seq - 1,
        );

        const expectedPrev =
          entry.seq === 0 ? '0'.repeat(64) : (previous?.entry_hash ?? '');

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
    return (
      <EmptyState
        title="No entries"
        description="The audit ledger is empty."
      />
    );
  }

  return (
    <div className="max-h-[480px] space-y-3 overflow-y-auto">
      {/* Filters */}
      <div className="sticky top-0 flex flex-wrap gap-2 border border-[#BFDBFE] bg-[#EFF6FF] px-2 py-2">
        <Select value={runFilter} onValueChange={setRunFilter}>
          <SelectTrigger
            className="h-8 w-40 border-[#BFDBFE] bg-white text-[#123D73] hover:bg-blue-50"
            aria-label="Filter by run"
          >
            <SelectValue />
          </SelectTrigger>

          <SelectContent className="border-[#BFDBFE] bg-white">
            {runIds.map((id) => (
              <SelectItem
                key={id}
                value={id}
                className="text-[#123D73] focus:bg-blue-50 focus:text-[#123D73]"
              >
                {id}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger
            className="h-8 w-44 border-[#BFDBFE] bg-white text-[#123D73] hover:bg-blue-50"
            aria-label="Filter by event type"
          >
            <SelectValue />
          </SelectTrigger>

          <SelectContent className="border-[#BFDBFE] bg-white">
            {eventTypes.map((type) => (
              <SelectItem
                key={type}
                value={type}
                className="text-[#123D73] focus:bg-blue-50 focus:text-[#123D73]"
              >
                {type}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Ledger table */}
      <div className="overflow-x-auto rounded-md border border-[#BFDBFE] bg-white">
        <table
          aria-label="Audit ledger"
          className="w-full text-xs"
        >
          <thead>
            <tr className="border-b border-[#CBD5E1] bg-[#EFF6FF] text-left text-[#123D73]">
              <th className="w-8" aria-label="Expand" />

              <th className="px-2 py-2 font-semibold">
                Seq
              </th>

              <th className="px-2 py-2 font-semibold">
                Run ID
              </th>

              <th className="px-2 py-2 font-semibold">
                Timestamp
              </th>

              <th className="px-2 py-2 font-semibold">
                Event Type
              </th>

              <th className="px-2 py-2 font-semibold">
                Entry Hash
              </th>

              <th className="px-2 py-2 font-semibold">
                Prev Hash
              </th>

              <th className="px-2 py-2 font-semibold">
                Valid
              </th>
            </tr>
          </thead>

          <tbody>
            {visible.map((entry) => {
              const verdict = verdicts[entry.seq] ?? 'pending';
              const open = expanded.has(entry.seq);

              return (
                <React.Fragment key={entry.seq}>
                  <tr className="border-b border-slate-200 bg-white transition-colors hover:bg-blue-50">
                    <td className="px-2 py-1.5">
                      <button
                        type="button"
                        onClick={() => toggle(entry.seq)}
                        aria-expanded={open}
                        aria-label={`${open ? 'Collapse' : 'Expand'} entry ${entry.seq}`}
                        className="rounded-sm p-1 text-[#123D73] hover:bg-blue-100 hover:text-[#082B57] focus:outline-none focus:ring-2 focus:ring-blue-300"
                      >
                        {open ? (
                          <ChevronDown
                            className="h-3.5 w-3.5"
                            aria-hidden="true"
                          />
                        ) : (
                          <ChevronRight
                            className="h-3.5 w-3.5"
                            aria-hidden="true"
                          />
                        )}
                      </button>
                    </td>

                    <td className="px-2 py-1.5 font-medium text-[#334155]">
                      {entry.seq}
                    </td>

                    <td
                      className="mono max-w-32 truncate px-2 py-1.5 text-[#334155]"
                      title={entry.run_id}
                    >
                      {entry.run_id}
                    </td>

                    <td className="whitespace-nowrap px-2 py-1.5 text-[#475569]">
                      {formatDate(entry.ts)}
                    </td>

                    <td className="px-2 py-1.5">
                      <Badge
                        variant="secondary"
                        className="border border-[#BFDBFE] bg-[#E0EEFF] font-medium text-[#123D73]"
                      >
                        {entry.event_type}
                      </Badge>
                    </td>

                    <td className="px-2 py-1.5">
                      <HashDisplay hash={entry.entry_hash} />
                    </td>

                    <td className="px-2 py-1.5">
                      <HashDisplay hash={entry.prev_hash} />
                    </td>

                    <td
                      className="px-2 py-1.5"
                      aria-label={`Entry ${entry.seq} ${verdict}`}
                    >
                      {verdict === 'ok' ? (
                        <span
                          className="inline-flex items-center justify-center rounded-full bg-emerald-50 p-1"
                          title="Valid"
                        >
                          <Check
                            className="h-4 w-4 text-green-600"
                            aria-hidden="true"
                          />
                        </span>
                      ) : verdict === 'tampered' ? (
                        <span
                          className="inline-flex items-center justify-center rounded-full bg-red-50 p-1"
                          title="Tampered"
                        >
                          <X
                            className="h-4 w-4 text-red-600"
                            aria-hidden="true"
                          />
                        </span>
                      ) : (
                        <span className="text-slate-500">…</span>
                      )}
                    </td>
                  </tr>

                  {open ? (
                    <tr className="border-b border-[#BFDBFE] bg-[#F8FAFF]">
                      <td />

                      <td colSpan={7} className="px-2 py-2">
                        <pre className="mono max-h-48 overflow-auto whitespace-pre-wrap rounded-md border border-[#BFDBFE] bg-[#EFF6FF] p-3 text-xs text-[#334155]">
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