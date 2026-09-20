import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { LoadingState } from '@/components/common/LoadingState';
import { EmptyState } from '@/components/common/EmptyState';
import type { RiskBand } from '@/types/api';

export interface TrendPoint {
  window: string;
  score: number;
  band: RiskBand;
}

export interface TrendLineProps {
  data: TrendPoint[];
  entityId: string;
  isLoading: boolean;
}

const BAND_LIMITS = [25, 50, 75];

/** Score colour interpolated green (LOW) → red (HIGH). */
export function scoreColour(score: number): string {
  const clamped = Math.max(0, Math.min(100, score));
  const red = Math.round(34 + (clamped / 100) * (239 - 34));
  const green = Math.round(197 - (clamped / 100) * (197 - 68));
  return `rgb(${red}, ${green}, 80)`;
}

function shortWindow(window: string): string {
  const date = new Date(window);
  if (!Number.isNaN(date.getTime())) {
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', timeZone: 'UTC' });
  }
  return window.length > 12 ? window.slice(0, 12) : window;
}

/** Entity risk score over windows with band zones and thresholds. */
export function TrendLine({ data, entityId, isLoading }: TrendLineProps) {
  if (isLoading) {
    return <LoadingState rows={3} message="Loading trend…" />;
  }
  if (data.length === 0) {
    return (
      <EmptyState title="No trend data" description={`${entityId} has no scored windows yet.`} />
    );
  }
  const mean = data.reduce((sum, point) => sum + point.score, 0) / data.length;
  const rows = data.map((point) => ({ ...point, short: shortWindow(point.window) }));
  return (
    <div aria-label={`Score trend for ${entityId}`} className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
          <ReferenceArea y1={0} y2={25} fill="#22c55e" fillOpacity={0.07} />
          <ReferenceArea y1={25} y2={50} fill="#eab308" fillOpacity={0.07} />
          <ReferenceArea y1={50} y2={75} fill="#f97316" fillOpacity={0.07} />
          <ReferenceArea y1={75} y2={100} fill="#ef4444" fillOpacity={0.07} />
          {BAND_LIMITS.map((limit) => (
            <ReferenceLine key={limit} y={limit} stroke="#94a3b8" strokeDasharray="4 4" />
          ))}
          <XAxis dataKey="short" tick={{ fill: '#64748b', fontSize: 11 }} stroke="#cbd5e1" />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: '#64748b', fontSize: 11 }}
            stroke="#cbd5e1"
            width={36}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#ffffff', border: '1px solid #dbe3ec', borderRadius: '8px' }}
            labelStyle={{ color: '#123d73', fontWeight: 600 }}
            itemStyle={{ color: '#475569' }}
            formatter={(value, _name, props) => {
              const payload = (props as { payload?: TrendPoint }).payload;
              return [`Score ${String(value ?? '—')} (${payload?.band ?? '—'})`, payload?.window ?? ''];
            }}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke={scoreColour(mean)}
            strokeWidth={2}
            dot={{ fill: scoreColour(mean), r: 3 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
