import { Link } from 'react-router-dom';
import { AlertTriangle, Download } from 'lucide-react';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { RiskBadge } from '@/components/common/RiskBadge';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { formatDate, formatScore } from '@/lib/utils';
import type { EntityDetail } from '@/types/api';

export interface EntityHeaderProps {
  entity: EntityDetail;
  runId: string;
  sizeBand?: string;
  peerCohortId?: string;
  isInQueue?: boolean;
}

/** Entity masthead: identity, score, confidence, completeness, actions. */
export function EntityHeader({ entity, runId, sizeBand, peerCohortId, isInQueue = false }: EntityHeaderProps) {
  const lowEvidence = entity.data_completeness < 0.6;

  function downloadReport(): void {
    const blob = new Blob([JSON.stringify(entity, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${entity.entity_id}-${runId}-report.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <code className="mono text-xl font-bold text-slate-50">{entity.entity_id}</code>
            <Badge variant="secondary">{entity.sector}</Badge>
            {sizeBand ? <Badge variant="outline">{sizeBand}</Badge> : null}
            <RiskBadge band={entity.band} size="lg" showIcon />
          </div>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span className="text-slate-400">
              Score{' '}
              <strong className={entity.overall_score >= 75 ? 'text-red-500' : entity.overall_score >= 50 ? 'text-orange-500' : entity.overall_score >= 25 ? 'text-yellow-500' : 'text-green-500'}>
                {formatScore(entity.overall_score)}
              </strong>
            </span>
            <ConfidenceBadge confidence={entity.confidence} reason={entity.confidence_reason} />
            <span className="text-slate-400">
              {entity.n_signals_flagged} signal{entity.n_signals_flagged === 1 ? '' : 's'} flagged
            </span>
          </div>
          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500">
            {peerCohortId ? (
              <div className="flex gap-1">
                <dt>Peer cohort:</dt>
                <dd className="mono text-slate-400">{peerCohortId}</dd>
              </div>
            ) : null}
            <div className="flex gap-1">
              <dt>Window:</dt>
              <dd>{entity.window}</dd>
            </div>
            <div className="flex gap-1">
              <dt>Computed:</dt>
              <dd>{formatDate(entity.computed_at)}</dd>
            </div>
          </dl>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={downloadReport}
            aria-label={`Download ${entity.entity_id} report as JSON`}
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            Download Report
          </Button>
          {isInQueue ? (
            <Link
              to={`/queue?run=${encodeURIComponent(runId)}`}
              className="text-sm text-slate-50 underline underline-offset-4"
              aria-label={`View ${entity.entity_id} in review queue`}
            >
              View in Queue
            </Link>
          ) : null}
        </div>
      </div>
      <div>
        <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
          <span>Data completeness</span>
          <span>{Math.round(entity.data_completeness * 100)}%</span>
        </div>
        <Progress value={Math.round(entity.data_completeness * 100)} aria-label="Data completeness" />
      </div>
      {lowEvidence ? (
        <div
          role="note"
          className="rounded-md border border-yellow-500 bg-yellow-950 px-4 py-3 text-sm text-yellow-500"
        >
          <strong className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            Insufficient evidence
          </strong>
          <p className="mt-1">
            Completeness is below 60%, so confidence is capped at LOW and this entity is
            excluded from the main ranking. Verify the feed before drawing conclusions.
          </p>
        </div>
      ) : null}
    </div>
  );
}
