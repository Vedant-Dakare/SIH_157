import * as React from 'react';
import { ArrowDown, ArrowUp, ChevronDown, ChevronRight } from 'lucide-react';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { EmptyState } from '@/components/common/EmptyState';
import { SignalBadge } from '@/components/common/SignalBadge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { formatScore } from '@/lib/utils';
import type { Finding, SignalFamily } from '@/types/api';

export type FindingRow = Finding & {
  finding_id: string;
  signalName?: string;
  trend?: string;
  sampleSize?: number;
  rationale?: string;
  domain?: string;
};

export interface FindingsTableProps {
  findings: FindingRow[];
  isLoading: boolean;
  onSelect: (finding: FindingRow) => void;
  signalFilter?: string[] | null;
  onClearSignalFilter?: () => void;
}

type SortKey = 'signal_id' | 'severity' | 'score' | 'confidence' | 'sampleSize' | 'window';

const SEVERITY_ORDER: Record<string, number> = { CRITICAL: 5, HIGH: 4, MEDIUM: 3, LOW: 2, INFO: 1 };
const CONFIDENCE_ORDER: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1 };

function familyOf(signalId: string): SignalFamily {
  if (signalId.startsWith('EG-')) {
    return 'execution_gap';
  }
  if (signalId.startsWith('NS-')) {
    return 'negative_space';
  }
  if (signalId.startsWith('COMP-')) {
    return 'composite';
  }
  return 'peer';
}

function cellValue(row: FindingRow, key: SortKey): string | number {
  switch (key) {
    case 'signal_id':
      return row.signal_id;
    case 'severity':
      return SEVERITY_ORDER[row.severity] ?? 0;
    case 'score':
      return row.score;
    case 'confidence':
      return CONFIDENCE_ORDER[row.confidence] ?? 0;
    case 'sampleSize':
      return row.sampleSize ?? 0;
    case 'window':
      return row.window;
  }
}

/** Sortable, filterable findings grid with expandable rationale previews. */
export function FindingsTable({ findings, isLoading, onSelect, signalFilter, onClearSignalFilter }: FindingsTableProps) {
  const [sortKey, setSortKey] = React.useState<SortKey>('score');
  const [sortDesc, setSortDesc] = React.useState(true);
  const [familyFilter, setFamilyFilter] = React.useState('ALL');
  const [severityFilter, setSeverityFilter] = React.useState('ALL');
  const [groupByFamily, setGroupByFamily] = React.useState(false);
  const [expanded, setExpanded] = React.useState<Set<string>>(new Set());

  const families = React.useMemo(
    () => ['ALL', ...Array.from(new Set(findings.map((finding) => familyOf(finding.signal_id))))],
    [findings],
  );
  const severities = React.useMemo(
    () => ['ALL', ...Array.from(new Set(findings.map((finding) => finding.severity)))],
    [findings],
  );

  const visible = React.useMemo(() => {
    const filtered = findings.filter(
      (finding) =>
        (signalFilter === undefined || signalFilter === null || signalFilter.includes(finding.signal_id)) &&
        (familyFilter === 'ALL' || familyOf(finding.signal_id) === familyFilter) &&
        (severityFilter === 'ALL' || finding.severity === severityFilter),
    );
    return [...filtered].sort((a, b) => {
      const left = cellValue(a, sortKey);
      const right = cellValue(b, sortKey);
      const order = typeof left === 'number' && typeof right === 'number' ? left - right : String(left).localeCompare(String(right));
      return sortDesc ? -order : order;
    });
  }, [findings, signalFilter, familyFilter, severityFilter, sortKey, sortDesc]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDesc((previous) => !previous);
    } else {
      setSortKey(key);
      setSortDesc(true);
    }
  }

  function toggleExpanded(findingId: string) {
    setExpanded((previous) => {
      const next = new Set(previous);
      if (next.has(findingId)) {
        next.delete(findingId);
      } else {
        next.add(findingId);
      }
      return next;
    });
  }

  if (isLoading) {
    return <p role="status" className="py-8 text-center text-sm text-slate-400">Loading findings…</p>;
  }
  if (findings.length === 0) {
    return <EmptyState title="No findings" description="No findings for this entity in the selected run." />;
  }

  const headers: Array<{ key: SortKey; label: string }> = [
    { key: 'signal_id', label: 'Signal' },
    { key: 'severity', label: 'Severity' },
    { key: 'score', label: 'Score' },
    { key: 'confidence', label: 'Confidence' },
    { key: 'sampleSize', label: 'Sample' },
    { key: 'window', label: 'Window' },
  ];

  let lastGroup = '';
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Select value={familyFilter} onValueChange={setFamilyFilter}>
          <SelectTrigger className="h-8 w-44" aria-label="Filter by family">
            <SelectValue placeholder="Family" />
          </SelectTrigger>
          <SelectContent>
            {families.map((family) => (
              <SelectItem key={family} value={family}>
                {family}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={severityFilter} onValueChange={setSeverityFilter}>
          <SelectTrigger className="h-8 w-40" aria-label="Filter by severity">
            <SelectValue placeholder="Severity" />
          </SelectTrigger>
          <SelectContent>
            {severities.map((severity) => (
              <SelectItem key={severity} value={severity}>
                {severity}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          type="button"
          variant={groupByFamily ? 'default' : 'outline'}
          size="sm"
          aria-pressed={groupByFamily}
          onClick={() => setGroupByFamily((previous) => !previous)}
        >
          Group by family
        </Button>
        {signalFilter && signalFilter.length > 0 ? (
          <Button type="button" variant="ghost" size="sm" onClick={onClearSignalFilter}>
            Clear domain filter ({signalFilter.length} signals) ×
          </Button>
        ) : null}
      </div>
      {visible.length === 0 ? (
        <EmptyState title="No matches" description="No findings match the current filters." />
      ) : (
        <div className="overflow-x-auto rounded-md border border-slate-700">
          <table aria-label="Findings table" className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="w-8" aria-label="Expand" />
                {headers.map((header) => (
                  <th key={header.key} className="px-2 py-2 text-left font-medium text-slate-400">
                    <button
                      type="button"
                      onClick={() => toggleSort(header.key)}
                      aria-label={`Sort by ${header.label}`}
                      className="inline-flex items-center gap-1 rounded-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                    >
                      {header.label}
                      {sortKey === header.key ? (
                        sortDesc ? (
                          <ArrowDown className="h-3 w-3" aria-hidden="true" />
                        ) : (
                          <ArrowUp className="h-3 w-3" aria-hidden="true" />
                        )
                      ) : null}
                    </button>
                  </th>
                ))}
                <th className="px-2 py-2 text-left font-medium text-slate-400">Name</th>
                <th className="px-2 py-2 text-left font-medium text-slate-400">Trend</th>
                <th className="px-2 py-2 text-left font-medium text-slate-400">Actions</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((finding) => {
                const key = `${finding.entity_id}|${finding.signal_id}`;
                const group = familyOf(finding.signal_id);
                const groupRow = groupByFamily && group !== lastGroup;
                lastGroup = group;
                const open = expanded.has(key);
                const rationale = finding.rationale ?? finding.plain_language;
                return (
                  <React.Fragment key={key}>
                    {groupRow ? (
                      <tr className="border-b border-slate-800 bg-slate-900">
                        <td colSpan={10} className="px-2 py-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {group.replace('_', ' ')}
                        </td>
                      </tr>
                    ) : null}
                    <tr
                      className={`border-b border-slate-700 transition-colors hover:bg-slate-800/50 ${finding.severity === 'CRITICAL' ? 'bg-red-950/40' : ''}`}
                    >
                      <td className="px-2 py-2">
                        <button
                          type="button"
                          onClick={() => toggleExpanded(key)}
                          aria-expanded={open}
                          aria-label={`${open ? 'Collapse' : 'Expand'} rationale for ${finding.signal_id}`}
                          className="rounded-sm p-1 text-slate-400 hover:text-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400"
                        >
                          {open ? (
                            <ChevronDown className="h-4 w-4" aria-hidden="true" />
                          ) : (
                            <ChevronRight className="h-4 w-4" aria-hidden="true" />
                          )}
                        </button>
                      </td>
                      <td className="px-2 py-2">
                        <SignalBadge signalId={finding.signal_id} family={group} size="sm" />
                      </td>
                      <td className="px-2 py-2 text-slate-50">{finding.severity}</td>
                      <td className="px-2 py-2 text-slate-50">{formatScore(finding.score)}</td>
                      <td className="px-2 py-2">
                        <ConfidenceBadge confidence={finding.confidence as Finding['confidence']} />
                      </td>
                      <td className="px-2 py-2 text-slate-400">{finding.sampleSize ?? '—'}</td>
                      <td className="px-2 py-2 font-mono text-xs text-slate-400">{finding.window}</td>
                      <td className="max-w-48 truncate px-2 py-2 text-slate-400" title={finding.signalName ?? finding.label}>
                        {finding.signalName ?? finding.label}
                      </td>
                      <td className="px-2 py-2 text-slate-400">{finding.trend ?? '—'}</td>
                      <td className="px-2 py-2">
                        <Button type="button" variant="ghost" size="sm" onClick={() => onSelect(finding)} aria-label={`View full finding ${finding.signal_id}`}>
                          View →
                        </Button>
                      </td>
                    </tr>
                    {open ? (
                      <tr className="border-b border-slate-700 bg-slate-900/60">
                        <td />
                        <td colSpan={9} className="px-2 py-2">
                          <p className="line-clamp-2 text-sm text-slate-400">{rationale}</p>
                          <Button type="button" variant="link" size="sm" className="px-0" onClick={() => onSelect(finding)}>
                            View Full Finding
                          </Button>
                        </td>
                      </tr>
                    ) : null}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
