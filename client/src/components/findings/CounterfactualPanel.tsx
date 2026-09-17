import type { Counterfactual } from '@/types/api';

export interface CounterfactualPanelProps {
  result: Counterfactual | null;
}

/** Threshold gap when computable; explicit reason otherwise. Never absent. */
export function CounterfactualPanel({ result }: CounterfactualPanelProps) {
  if (result === null || !result.computable) {
    return (
      <p role="note" className="rounded-md border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-slate-400">
        Counterfactual not available:{' '}
        {result?.reason_if_null || 'no counterfactual computed for this finding.'}
      </p>
    );
  }
  const ratio = result.required_value / Math.max(result.threshold_value, 1e-9);
  const requiredWidth = `${Math.max(2, Math.min(100, ratio * 100))}%`;
  return (
    <div className="rounded-md border border-blue-500 bg-blue-950 px-4 py-3" aria-label="Counterfactual">
      <p className="text-sm leading-relaxed text-slate-50">{result.plain_language}</p>
      <div className="mt-3 space-y-2" aria-hidden="true">
        <div>
          <div className="mb-1 flex justify-between text-xs text-slate-400">
            <span>Observed {result.threshold_value}</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
            <div className="h-full bg-red-500" style={{ width: '100%' }} />
          </div>
        </div>
        <div>
          <div className="mb-1 flex justify-between text-xs text-slate-400">
            <span>
              Required {result.required_value} ({result.metric_name})
            </span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
            <div className="h-full bg-green-500" style={{ width: requiredWidth }} />
          </div>
        </div>
      </div>
      <p className="mono mt-2 text-xs text-slate-400">
        {result.metric_name}: {result.threshold_value} → {result.required_value}
      </p>
    </div>
  );
}
