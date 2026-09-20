import { useNavigate } from 'react-router-dom';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { EmptyState } from '@/components/common/EmptyState';
import { LoadingState } from '@/components/common/LoadingState';
import { RiskBadge } from '@/components/common/RiskBadge';
import { SampleAlertList } from '@/components/queue/SampleAlertList';
import { SignalBadge } from '@/components/common/SignalBadge';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatScore } from '@/lib/utils';
import type { QueueItem, SignalFamily } from '@/types/api';

export interface QueueTableProps {
  items: QueueItem[];
  isLoading: boolean;
  runId: string;
  insufficient: string[];
  onStartReview?: (item: QueueItem) => void;
}

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

function noveltyLabel(weight: number): string {
  return weight < 1 ? 'SEEN BEFORE' : 'NEW';
}

/** Ranked manual-review worklist with samples and a separate low-evidence section. */
export function QueueTable({
  items,
  isLoading,
  runId,
  insufficient,
  onStartReview,
}: QueueTableProps) {
  const navigate = useNavigate();

  function startReview(item: QueueItem): void {
    try {
      window.localStorage.setItem(
        `satsa-in-review-${item.entity_id}`,
        JSON.stringify({
          runId,
          at: new Date().toISOString(),
        }),
      );
    } catch {
      // Session-only marking is best-effort; navigation still works.
    }

    onStartReview?.(item);

    const signals = item.signal_ids
      .map(
        (signal) =>
          `signal=${encodeURIComponent(signal)}`,
      )
      .join('&');

    navigate(
      `/entities/${item.entity_id}?run=${encodeURIComponent(
        runId,
      )}${signals ? `&${signals}` : ''}`,
    );
  }

  function printQueue(): void {
    window.print();
  }

  if (isLoading) {
    return (
      <LoadingState
        rows={6}
        message="Loading review queue…"
      />
    );
  }

  if (
    items.length === 0 &&
    insufficient.length === 0
  ) {
    return (
      <EmptyState
        title="Queue empty"
        description="No entities await review in this run."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={printQueue}
          aria-label="Print review queue"
        >
          Print
        </Button>
      </div>

      {/* Review queue table */}
      <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
        <table
          aria-label="Manual review queue"
          className="w-full text-sm text-slate-900"
        >
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-left">
              <th className="px-3 py-3 font-semibold text-slate-900">
                #
              </th>

              <th className="px-3 py-3 font-semibold text-slate-900">
                Entity
              </th>

              <th className="px-3 py-3 font-semibold text-slate-900">
                Focus Area
              </th>

              <th className="px-3 py-3 font-semibold text-slate-900">
                Signals
              </th>

              <th className="px-3 py-3 font-semibold text-slate-900">
                Minutes
              </th>

              <th className="px-3 py-3 font-semibold text-slate-900">
                Novelty
              </th>

              <th className="px-3 py-3 font-semibold text-slate-900">
                Samples
              </th>

              <th className="px-3 py-3 font-semibold text-slate-900">
                Actions
              </th>
            </tr>
          </thead>

          <tbody>
            {items.map((item) => (
              <tr
                key={item.entity_id}
                className="border-b border-slate-200 align-top transition-colors hover:bg-blue-50/40 last:border-0"
              >
                {/* Rank */}
                <td className="px-3 py-3 text-xl font-bold text-slate-900">
                  {item.rank}
                </td>

                {/* Entity */}
                <td className="px-3 py-3">
                  <div className="flex flex-col gap-1">
                    <span className="mono font-medium text-slate-900">
                      {item.entity_id}
                    </span>

                    <span className="flex items-center gap-1 text-xs font-medium text-slate-700">
                      <RiskBadge
                        band={item.band}
                        size="sm"
                      />

                      <span>
                        {formatScore(
                          item.risk_score,
                        )}
                      </span>
                    </span>

                    <ConfidenceBadge
                      confidence={item.confidence}
                    />
                  </div>
                </td>

                {/* Focus Area */}
                <td className="px-3 py-3 font-medium text-slate-900">
                  {item.focus_area || '—'}
                </td>

                {/* Signals */}
                <td className="px-3 py-3">
                  <div className="flex max-w-64 flex-wrap gap-1">
                    {item.signal_ids
                      .slice(0, 3)
                      .map((signal) => (
                        <SignalBadge
                          key={signal}
                          signalId={signal}
                          family={familyOf(
                            signal,
                          )}
                          size="sm"
                        />
                      ))}

                    {item.signal_ids.length >
                    3 ? (
                      <Badge
                        variant="secondary"
                        className="border border-slate-200 bg-slate-100 text-slate-700"
                      >
                        +
                        {item.signal_ids.length -
                          3}{' '}
                        more
                      </Badge>
                    ) : null}
                  </div>
                </td>

                {/* Minutes */}
                <td className="px-3 py-3 font-medium tabular-nums text-slate-900">
                  {item.expected_review_minutes}
                </td>

                {/* Novelty */}
                <td className="px-3 py-3">
                  <Badge
                    variant={
                      item.novelty_weight < 1
                        ? 'secondary'
                        : 'default'
                    }
                  >
                    {noveltyLabel(
                      item.novelty_weight,
                    )}
                  </Badge>
                </td>

                {/* Samples */}
                <td className="px-3 py-3">
                  <SampleAlertList
                    sampleAlertIds={
                      item.sample_alert_ids
                    }
                    sampleCaseIds={
                      item.sample_case_ids
                    }
                    signalId={
                      item.signal_ids[0] ?? ''
                    }
                  />
                </td>

                {/* Actions */}
                <td className="px-3 py-3">
                  <Button
                    type="button"
                    size="sm"
                    onClick={() =>
                      startReview(item)
                    }
                    aria-label={`Start review of ${item.entity_id}`}
                  >
                    Start Review
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Insufficient evidence */}
      <section
        aria-label="Insufficient evidence"
        className="rounded-md border border-amber-200 bg-amber-50 p-4"
      >
        <h3 className="mb-1 text-sm font-semibold text-amber-900">
          Insufficient Evidence — Pending Feed
          Verification
        </h3>

        <p className="mb-3 text-sm text-slate-700">
          Completeness below 60%: these entities
          are excluded from ranking until their
          feeds are verified. Reviewing them now
          risks false accusation.
        </p>

        {insufficient.length === 0 ? (
          <p className="text-sm text-slate-600">
            None in this run.
          </p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {insufficient.map((entityId) => (
              <li
                key={entityId}
                className="mono rounded-sm border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-800"
              >
                {entityId}
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="text-xs text-slate-500">
        Last reviewed dates live in the audit
        ledger; entities absent from recent runs are
        treated as never reviewed.
      </p>
    </div>
  );
}