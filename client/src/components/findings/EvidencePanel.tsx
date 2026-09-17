import * as React from 'react';

import { EmptyState } from '@/components/common/EmptyState';
import { HashDisplay } from '@/components/common/HashDisplay';

export interface EvidencePanelProps {
  supportingRows: Array<Record<string, unknown>>;
  counterRows: Array<Record<string, unknown>>;
  counterAbsentReason: string;
  evidenceId: string;
}

function columnsOf(rows: Array<Record<string, unknown>>): string[] {
  const keys = new Set<string>();
  for (const row of rows.slice(0, 50)) {
    for (const key of Object.keys(row)) {
      keys.add(key);
    }
  }
  return [...keys].slice(0, 8);
}

function RowTable({ rows, caption }: { rows: Array<Record<string, unknown>>; caption: string }) {
  const [sortKey, setSortKey] = React.useState<string | null>(null);
  const [sortDesc, setSortDesc] = React.useState(true);
  const columns = columnsOf(rows);
  const visible = rows.slice(0, 50);
  const sorted = React.useMemo(() => {
    if (!sortKey) {
      return visible;
    }
    return [...visible].sort((a, b) => {
      const left = String(a[sortKey] ?? '');
      const right = String(b[sortKey] ?? '');
      const order = left.localeCompare(right, undefined, { numeric: true });
      return sortDesc ? -order : order;
    });
  }, [visible, sortKey, sortDesc]);

  if (visible.length === 0) {
    return null;
  }
  return (
    <div className="overflow-x-auto rounded-md border border-slate-700">
      <table aria-label={caption} className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-700">
            {columns.map((column) => (
              <th key={column} className="px-2 py-2 text-left font-medium text-slate-400">
                <button
                  type="button"
                  onClick={() => {
                    if (sortKey === column) {
                      setSortDesc((previous) => !previous);
                    } else {
                      setSortKey(column);
                      setSortDesc(true);
                    }
                  }}
                  aria-label={`Sort evidence by ${column}`}
                  className="rounded-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                >
                  {column} {sortKey === column ? (sortDesc ? '↓' : '↑') : ''}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, index) => (
            <tr key={index} className="border-b border-slate-800 last:border-0">
              {columns.map((column) => (
                <td key={column} className="mono max-w-64 truncate px-2 py-1.5 text-slate-50" title={String(row[column] ?? '')}>
                  {String(row[column] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Supporting vs counter evidence tabs. Counter section never hidden. */
export function EvidencePanel({ supportingRows, counterRows, counterAbsentReason, evidenceId }: EvidencePanelProps) {
  const [tab, setTab] = React.useState<'supporting' | 'counter'>('supporting');
  return (
    <div>
      <div role="tablist" aria-label="Evidence tabs" className="mb-3 flex gap-1">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'supporting'}
          onClick={() => setTab('supporting')}
          className={`rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 ${tab === 'supporting' ? 'bg-slate-800 text-slate-50' : 'text-slate-400 hover:text-slate-50'}`}
        >
          Supporting Evidence ({supportingRows.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'counter'}
          onClick={() => setTab('counter')}
          className={`rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 ${tab === 'counter' ? 'bg-slate-800 text-slate-50' : 'text-slate-400 hover:text-slate-50'}`}
        >
          Counter-Evidence ({counterRows.length})
        </button>
      </div>
      {tab === 'supporting' ? (
        supportingRows.length === 0 ? (
          <EmptyState title="No supporting rows" description="This finding recorded no supporting rows." />
        ) : (
          <RowTable rows={supportingRows} caption="Supporting evidence rows" />
        )
      ) : counterRows.length === 0 ? (
        <p role="note" className="rounded-md border border-yellow-500 bg-yellow-950 px-4 py-3 text-sm text-yellow-500">
          No counter-evidence on record: {counterAbsentReason || 'no reason recorded.'}
        </p>
      ) : (
        <RowTable rows={counterRows} caption="Counter-evidence rows" />
      )}
      <p className="mt-2 text-xs text-slate-500">Showing up to 50 rows. Full history lives in DuckDB.</p>
      <div className="mt-2">
        <HashDisplay hash={evidenceId} label="evidence_id" />
      </div>
    </div>
  );
}
