import type { Counterfactual } from '@/types/api';

export interface CounterfactualPanelProps {
  result: Counterfactual | null;
}

/** Threshold gap when computable; explicit reason otherwise. Never absent. */
export function CounterfactualPanel({
  result,
}: CounterfactualPanelProps) {
  if (result === null || !result.computable) {
    return (
      <p
        role="note"
        className="rounded-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600"
      >
        Counterfactual not available:{' '}
        {result?.reason_if_null ||
          'no counterfactual computed for this finding.'}
      </p>
    );
  }

  const ratio =
    result.required_value /
    Math.max(result.threshold_value, 1e-9);

  const requiredWidth = `${Math.max(
    2,
    Math.min(100, ratio * 100),
  )}%`;

  return (
    <div
      className="rounded-md border border-blue-200 bg-blue-50 px-4 py-4"
      aria-label="Counterfactual"
    >
      <p className="text-sm leading-relaxed text-slate-800">
        {result.plain_language}
      </p>

      <div
        className="mt-4 space-y-3"
        aria-hidden="true"
      >
        <div>
          <div className="mb-1.5 flex justify-between text-xs font-medium text-slate-600">
            <span>
              Observed {result.threshold_value}
            </span>
          </div>

          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full bg-red-500"
              style={{ width: '100%' }}
            />
          </div>
        </div>

        <div>
          <div className="mb-1.5 flex justify-between text-xs font-medium text-slate-600">
            <span>
              Required {result.required_value}{' '}
              ({result.metric_name})
            </span>
          </div>

          <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full bg-emerald-500"
              style={{ width: requiredWidth }}
            />
          </div>
        </div>
      </div>

      <p className="mono mt-3 text-xs font-medium text-slate-600">
        {result.metric_name}: {result.threshold_value} →{' '}
        {result.required_value}
      </p>
    </div>
  );
}