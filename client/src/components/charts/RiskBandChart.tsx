import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts';

import { LoadingState } from '@/components/common/LoadingState';
import { EmptyState } from '@/components/common/EmptyState';
import { RISK_BAND_STYLES } from '@/lib/constants';
import { formatPercent } from '@/lib/utils';
import type { RiskBand } from '@/types/api';

export interface RiskBandChartProps {
  data: Record<RiskBand, number>;
  isLoading: boolean;
}

const BANDS: RiskBand[] = ['HIGH', 'ELEVATED', 'MODERATE', 'LOW'];

const FILL: Record<RiskBand, string> = {
  HIGH: '#ef4444',
  ELEVATED: '#f97316',
  MODERATE: '#eab308',
  LOW: '#22c55e',
};

/** Donut of entity counts by risk band with total in the centre. */
export function RiskBandChart({ data, isLoading }: RiskBandChartProps) {
  if (isLoading) {
    return <LoadingState rows={3} message="Loading risk bands…" />;
  }
  const total = BANDS.reduce((sum, band) => sum + (data[band] ?? 0), 0);
  if (total === 0) {
    return <EmptyState title="No entities" description="No entities in this run." />;
  }
  const slices = BANDS.map((band) => ({ band, count: data[band] ?? 0 })).filter(
    (slice) => slice.count > 0,
  );
  return (
    <div aria-label="Risk band distribution chart" className="w-full">
      <div className="relative h-56 w-full">
        <div aria-hidden="true" className="h-full w-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={slices} dataKey="count" nameKey="band" innerRadius="60%" outerRadius="85%" isAnimationActive={false}>
                {slices.map((slice) => (
                  <Cell key={slice.band} fill={FILL[slice.band]} stroke="#020617" strokeWidth={2} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #334155' }}
                formatter={(value, name) => [`${String(value ?? 0)} entities in ${String(name)} band`, '']}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-slate-50">{total}</span>
          <span className="text-xs text-slate-400">entities</span>
        </div>
      </div>
      <ul aria-label="Risk band legend" className="mt-3 space-y-1.5">
        {BANDS.map((band) => (
          <li key={band} className="flex items-center gap-2 text-sm">
            <span
              aria-hidden="true"
              className={`h-2.5 w-2.5 rounded-sm ${RISK_BAND_STYLES[band].dot}`}
            />
            <span className="text-slate-50">{band}</span>
            <span className="ml-auto text-slate-400">
              {data[band] ?? 0} ({formatPercent(total > 0 ? (data[band] ?? 0) / total : 0)})
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
