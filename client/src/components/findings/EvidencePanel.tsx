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
    <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
      <table aria-label={caption} className="w-full text-xs">
        <thead>
          <tr className="border-b border-slate-200 bg-slate-50">
            {columns.map((column) => (
              <th key={column} className="px-2 py-2 text-left font-medium text-slate-600">
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
                  className="rounded-sm focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  {column} {sortKey === column ? (sortDesc ? '↓' : '↑') : ''}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, index) => (
            <tr key={index} className="border-b border-slate-100 last:border-0 hover:bg-blue-50/40">
              {columns.map((column) => (
                <td key={column} className="mono max-w-64 truncate px-2 py-1.5 text-slate-800" title={String(row[column] ?? '')}>
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
      <div role="tablist" aria-label="Evidence tabs" className="mb-3 inline-flex gap-1 rounded-md border border-slate-200 bg-slate-100 p-1">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'supporting'}
          onClick={() => setTab('supporting')}
          className={`rounded-sm px-3 py-1.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-200 ${tab === 'supporting' ? 'bg-white text-[#123D73] shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
        >
          Supporting Evidence ({supportingRows.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'counter'}
          onClick={() => setTab('counter')}
          className={`rounded-sm px-3 py-1.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-200 ${tab === 'counter' ? 'bg-white text-[#123D73] shadow-sm' : 'text-slate-600 hover:text-slate-900'}`}
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
        <p role="note" className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
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
