import { AlertTriangle } from 'lucide-react';

export interface PeerBaseline {
  cohort_id?: string;
  cohort_n?: number;
  median?: number;
  p25?: number;
  p75?: number;
  p95?: number;
  entity_value?: number;
  cohort_too_small?: boolean;
}

export interface PeerBaselinePanelProps {
  baseline: PeerBaseline;
}

/** Cohort distribution with the entity value marked; small-cohort warning. */
export function PeerBaselinePanel({
  baseline,
}: PeerBaselinePanelProps) {
  const points = [
    baseline.p25,
    baseline.median,
    baseline.p75,
    baseline.p95,
    baseline.entity_value,
  ].filter(
    (value): value is number =>
      typeof value === 'number' &&
      Number.isFinite(value),
  );

  const min =
    points.length > 0 ? Math.min(...points) : 0;

  const max =
    points.length > 0 ? Math.max(...points) : 1;

  const span = Math.max(max - min, 1e-9);

  const position = (value: number | undefined) =>
    value === undefined
      ? undefined
      : `${((value - min) / span) * 100}%`;

  function Marker({
    value,
    colour,
    label,
  }: {
    value: number | undefined;
    colour: string;
    label: string;
  }) {
    const left = position(value);

    if (left === undefined) {
      return null;
    }

    return (
      <div
        className="absolute top-0 h-full"
        style={{ left }}
        title={`${label}: ${value}`}
      >
        <div className={`h-full w-0.5 ${colour}`} />
      </div>
    );
  }

  return (
    <div
      className="space-y-3"
      aria-label="Peer baseline"
    >
      <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
        <div className="rounded-md border border-slate-200 bg-white p-3">
          <dt className="text-xs font-medium text-slate-500">
            Cohort
          </dt>
          <dd className="mono mt-1 text-xs font-medium text-slate-900">
            {baseline.cohort_id ?? '—'}
          </dd>
        </div>

        <div className="rounded-md border border-slate-200 bg-white p-3">
          <dt className="text-xs font-medium text-slate-500">
            Cohort n
          </dt>
          <dd className="mt-1 font-medium text-slate-900">
            {baseline.cohort_n ?? '—'}
          </dd>
        </div>

        <div className="rounded-md border border-slate-200 bg-white p-3">
          <dt className="text-xs font-medium text-slate-500">
            Median
          </dt>
          <dd className="mt-1 font-medium text-slate-900">
            {baseline.median ?? '—'}
          </dd>
        </div>

        <div className="rounded-md border border-blue-200 bg-blue-50 p-3">
          <dt className="text-xs font-medium text-slate-500">
            Entity value
          </dt>
          <dd className="mt-1 font-bold text-[#123d73]">
            {baseline.entity_value ?? '—'}
          </dd>
        </div>
      </dl>

      <div>
        <div
          className="relative h-8 rounded-md border border-slate-200 bg-slate-100"
          role="img"
          aria-label="Cohort distribution with entity value marked"
        >
          <div
            className="absolute top-1/4 h-1/2 rounded-sm bg-slate-300"
            style={{
              left:
                position(
                  baseline.p25 ?? min,
                ) ?? '0%',
              width: `calc(${
                position(
                  baseline.p75 ?? max,
                ) ?? '100%'
              } - ${
                position(
                  baseline.p25 ?? min,
                ) ?? '0%'
              })`,
            }}
          />

          <Marker
            value={baseline.median}
            colour="bg-slate-700"
            label="Median"
          />

          <Marker
            value={baseline.p95}
            colour="bg-slate-400"
            label="p95"
          />

          <Marker
            value={baseline.entity_value}
            colour="bg-[#2563a8]"
            label="Entity"
          />
        </div>

        <div className="mt-1 flex justify-between text-[11px] font-medium text-slate-500">
          <span>
            p25 {baseline.p25 ?? '—'}
          </span>

          <span>
            p75 {baseline.p75 ?? '—'}
          </span>
        </div>
      </div>

      {baseline.cohort_too_small ? (
        <p
          role="note"
          className="flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900"
        >
          <AlertTriangle
            className="h-4 w-4 shrink-0 text-amber-700"
            aria-hidden="true"
          />

          Small cohort (n=
          {baseline.cohort_n ?? 0}) — global baseline
          used, confidence penalised.
        </p>
      ) : null}
    </div>
  );
}