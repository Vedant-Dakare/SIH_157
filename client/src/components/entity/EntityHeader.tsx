import { Link } from 'react-router-dom';
import { Download } from 'lucide-react';

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
            <code className="mono text-xl font-bold text-[#123B5D]">{entity.entity_id}</code>
            <Badge variant="secondary">{entity.sector}</Badge>
            {sizeBand ? <Badge variant="outline">{sizeBand}</Badge> : null}
            <RiskBadge band={entity.band} size="lg" showIcon />
          </div>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <span className="text-[#52606D]">
              Score{' '}
              <strong className={entity.overall_score >= 75 ? 'text-red-600' : entity.overall_score >= 50 ? 'text-orange-600' : entity.overall_score >= 25 ? 'text-yellow-700' : 'text-green-700'}>
                {formatScore(entity.overall_score)}
              </strong>
            </span>
            <ConfidenceBadge confidence={entity.confidence} reason={entity.confidence_reason} />
            <span className="text-[#52606D]">
              {entity.n_signals_flagged} signal{entity.n_signals_flagged === 1 ? '' : 's'} flagged
            </span>
          </div>
          <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-[#52606D]">
            {peerCohortId ? (
              <div className="flex gap-1">
                <dt>Peer cohort:</dt>
                <dd className="mono text-[#1F2933]">{peerCohortId}</dd>
              </div>
            ) : null}
            <div className="flex gap-1">
              <dt>Window:</dt>
              <dd className="text-[#1F2933]">{entity.window}</dd>
            </div>
            <div className="flex gap-1">
              <dt>Computed:</dt>
              <dd className="text-[#1F2933]">{formatDate(entity.computed_at)}</dd>
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
            className="border-[#D9E2EC] bg-white text-[#123B5D] hover:bg-[#EAF3F8] hover:border-[#1F5F8B]"
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            Download Report
          </Button>
          {isInQueue ? (
            <Link
              to={`/queue?run=${encodeURIComponent(runId)}`}
              className="text-xs font-semibold text-[#1F5F8B] underline underline-offset-4 hover:text-[#123B5D]"
              aria-label={`View ${entity.entity_id} in review queue`}
            >
              View in Queue
            </Link>
          ) : null}
        </div>
      </div>
      <div>
        <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
          <span>Data completeness</span>
          <span>{Math.round(entity.data_completeness * 100)}%</span>
        </div>
        <Progress value={Math.round(entity.data_completeness * 100)} aria-label="Data completeness" />
      </div>

    </div>
  );
}
