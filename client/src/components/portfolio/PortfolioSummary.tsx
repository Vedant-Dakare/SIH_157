import { ArrowDown, ArrowUp, Minus } from 'lucide-react';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { formatPercent } from '@/lib/utils';
import type { PortfolioSummary } from '@/types/api';

export interface StatDelta {
  value: number;
  label: string;
}

export interface PortfolioSummaryProps {
  summary: PortfolioSummary;
  isLoading: boolean;
  findingsCount?: number;
  avgCompleteness?: number;
  deltas?: {
    entities?: StatDelta;
    high?: StatDelta;
    findings?: StatDelta;
    quality?: StatDelta;
  };
}

function Delta({ delta }: { delta?: StatDelta }) {
  if (!delta) {
    return null;
  }

  const Icon =
    delta.value > 0
      ? ArrowUp
      : delta.value < 0
        ? ArrowDown
        : Minus;

  const colour =
    delta.value > 0
      ? 'text-red-600'
      : delta.value < 0
        ? 'text-green-700'
        : 'text-slate-500';

  return (
    <p
      className={`mt-1 flex items-center gap-1 text-xs ${colour}`}
    >
      <Icon
        className="h-3 w-3"
        aria-hidden="true"
      />

      {delta.value > 0 ? '+' : ''}
      {delta.value} {delta.label}
    </p>
  );
}

/** Four portfolio stat cards with deltas and confidence. */
export function PortfolioSummary({
  summary,
  isLoading,
  findingsCount,
  avgCompleteness,
  deltas,
}: PortfolioSummaryProps) {
  if (isLoading) {
    return (
      <div
        className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Loading summary"
      >
        {[0, 1, 2, 3].map((index) => (
          <Card key={index}>
            <CardHeader>
              <Skeleton className="h-4 w-24" />
            </CardHeader>

            <CardContent>
              <Skeleton className="h-8 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const total = Object.values(
    summary.entity_count_by_band,
  ).reduce((sum, count) => sum + count, 0);

  const high =
    summary.entity_count_by_band.HIGH ?? 0;

  const cardClass =
    'border-[#D9E2EC] bg-white text-[#1F2933] shadow-xs';

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <Card className={cardClass}>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-bold uppercase tracking-wider text-[#52606D]">
            Total Entities
          </CardTitle>
        </CardHeader>

        <CardContent>
          <p className="text-2xl font-bold text-[#123B5D]">
            {total}
          </p>

          <Delta delta={deltas?.entities} />
        </CardContent>
      </Card>

      <Card className={cardClass}>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-bold uppercase tracking-wider text-[#52606D]">
            HIGH Risk Entities
          </CardTitle>
        </CardHeader>

        <CardContent>
          <p className={`text-2xl font-bold ${high > 0 ? 'text-red-500' : 'text-[#123B5D]'}`}>
            {high}
          </p>

          <Delta delta={deltas?.high} />
        </CardContent>
      </Card>

      <Card className={cardClass}>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-bold uppercase tracking-wider text-[#52606D]">
            Active Findings
          </CardTitle>
        </CardHeader>

        <CardContent>
          <p className="text-2xl font-bold text-[#123B5D]">
            {findingsCount ?? '—'}
          </p>

          <Delta delta={deltas?.findings} />
        </CardContent>
      </Card>

      <Card className={cardClass}>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs font-bold uppercase tracking-wider text-[#52606D]">
            Data Quality
          </CardTitle>
        </CardHeader>

        <CardContent>
          <p
            className={`text-2xl font-bold ${
              (avgCompleteness ?? 1) >= 0.9
                ? 'text-green-700'
                : (avgCompleteness ?? 1) >= 0.7
                  ? 'text-amber-600'
                  : 'text-red-600'
            }`}
          >
            {avgCompleteness === undefined
              ? '—'
              : formatPercent(avgCompleteness)}
          </p>

          <Delta delta={deltas?.quality} />

          <div className="mt-2">
            <ConfidenceBadge
              confidence={
                high > 0 ? 'MEDIUM' : 'HIGH'
              }
              reason="Portfolio-level aggregate confidence"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}