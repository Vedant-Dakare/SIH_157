import * as React from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { ReasonCode } from '@/types/api';

export type CompositeReasonCode = ReasonCode & {
  expression?: string;
  expression_tree?: unknown;
  leaf_codes?: ReasonCode[];
};

export interface ReasonCodeDisplayProps {
  code: ReasonCode | CompositeReasonCode;
  onLeafSelect?: (code: ReasonCode) => void;
}

function isComposite(code: ReasonCode | CompositeReasonCode): code is CompositeReasonCode {
  return 'expression_tree' in code && code.expression_tree !== undefined;
}

function TreeNode({ node, onLeafSelect }: { node: unknown; onLeafSelect?: (code: ReasonCode) => void }) {
  const [open, setOpen] = React.useState(true);
  if (typeof node === 'string') {
    return <span className="mono text-xs text-cyan-700">{node}</span>;
  }
  if (node !== null && typeof node === 'object' && !Array.isArray(node)) {
    const entries = Object.entries(node as Record<string, unknown>);
    if (entries.length === 0) {
      return <span className="text-xs text-slate-500">(empty)</span>;
    }
    const [operator, branches] = entries[0] as [string, unknown[]];
    return (
      <div className="ml-2 border-l border-slate-200 pl-2">
        <button
          type="button"
          onClick={() => setOpen((previous) => !previous)}
          aria-expanded={open}
          aria-label={`${open ? 'Collapse' : 'Expand'} ${operator} branch`}
          className="inline-flex items-center gap-1 rounded-sm text-xs font-bold text-[#123D73] focus:outline-none focus:ring-2 focus:ring-blue-200"
        >
          {open ? <ChevronDown className="h-3 w-3" aria-hidden="true" /> : <ChevronRight className="h-3 w-3" aria-hidden="true" />}
          {operator}
        </button>
        {open ? (
          <ul className="mt-1 space-y-1">
            {(Array.isArray(branches) ? branches : []).map((branch, index) => (
              <li key={index}>
                <TreeNode node={branch} onLeafSelect={onLeafSelect} />
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    );
  }
  return <span className="text-xs text-slate-500">—</span>;
}

/** Structured reason code with peer baseline and expandable composite trees. */
export function ReasonCodeDisplay({ code, onLeafSelect }: ReasonCodeDisplayProps) {
  const baseline = code.peer_baseline;
  return (
    <div className="space-y-3" aria-label={`Reason code ${code.code}`}>
      <p className="text-2xl font-bold text-[#102A56]">
        {String(code.observed)}{' '}
        <span className="text-base font-normal text-slate-500">{code.comparator}</span>{' '}
        {String(code.threshold)}
      </p>
      <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
        <div className="rounded-md border border-slate-200 bg-slate-50 p-2">
          <dt className="text-xs text-slate-500">Peer median</dt>
          <dd className="font-medium text-slate-900">{baseline.median}</dd>
        </div>
        <div className="rounded-md border border-slate-200 bg-slate-50 p-2">
          <dt className="text-xs text-slate-500">Peer p95</dt>
          <dd className="font-medium text-slate-900">{baseline.p95}</dd>
        </div>
        <div className="rounded-md border border-slate-200 bg-slate-50 p-2">
          <dt className="text-xs text-slate-500">Cohort n</dt>
          <dd className="font-medium text-slate-900">{baseline.n}</dd>
        </div>
        <div className="rounded-md border border-slate-200 bg-slate-50 p-2">
          <dt className="text-xs text-slate-500">Window</dt>
          <dd className="mono text-xs font-medium text-slate-900">{code.window}</dd>
        </div>
      </dl>
      <p className="rounded-md border border-blue-200 bg-blue-50 p-3 text-base leading-relaxed text-slate-800">
        {code.plain_language}
      </p>
      {isComposite(code) ? (
        <div className="rounded-md border border-slate-200 bg-white p-3">
          <p className="mono mb-2 text-xs text-slate-500">{code.expression ?? code.code}</p>
          <TreeNode node={code.expression_tree} onLeafSelect={onLeafSelect} />
          {code.leaf_codes && code.leaf_codes.length > 0 ? (
            <ul className="mt-3 space-y-1 border-t border-slate-200 pt-2">
              {code.leaf_codes.map((leaf) => (
                <li key={leaf.code}>
                  <button
                    type="button"
                    onClick={() => onLeafSelect?.(leaf)}
                    aria-label={`Inspect leaf reason code ${leaf.code}`}
                    className="w-full rounded-sm p-1 text-left font-mono text-xs text-cyan-700 hover:bg-cyan-50 focus:outline-none focus:ring-2 focus:ring-blue-200"
                  >
                    {leaf.code} — {leaf.label}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
