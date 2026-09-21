import { Link, useParams, useSearchParams } from 'react-router-dom';

import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingState } from '@/components/common/LoadingState';
import { FindingDetail } from '@/components/findings/FindingDetail';
import { useCounterfactual, useEvidence, useFinding } from '@/hooks/useEvidence';
import { useRuns } from '@/hooks/useRuns';

/** Finding detail: parallel fetch, 7-section view, clear 404. */
export default function FindingDetailPage() {
  const { findingId } = useParams();
  const [searchParams] = useSearchParams();
  const runsQuery = useRuns();
  const runs = runsQuery.data?.runs ?? [];
  const runId = searchParams.get('run') || runs[0] || '';

  const findingQuery = useFinding(findingId, runId);
  const evidenceQuery = useEvidence(findingId, runId);
  const counterfactualQuery = useCounterfactual(findingId, runId);

  if (!findingId) {
    return (
      <div className="space-y-4 text-center">
        <h2 className="text-lg font-semibold text-slate-900">Finding not found</h2>
        <p className="text-sm text-slate-600">No finding id in the URL.</p>
        <Link to="/portfolio" className="text-sm font-medium text-[#2563A8] underline underline-offset-4 hover:text-[#123D73]">
          Back to portfolio
        </Link>
      </div>
    );
  }

  const loading = findingQuery.isLoading || evidenceQuery.isLoading || counterfactualQuery.isLoading;
  if (loading) {
    return <LoadingState rows={10} message="Loading finding…" />;
  }
  const error = findingQuery.error ?? evidenceQuery.error ?? counterfactualQuery.error;
  const finding = findingQuery.data?.finding;
  if (error || !finding) {
    return (
      <div className="space-y-4">
        <ErrorState
          error={error instanceof Error ? error : new Error(`Finding ${findingId} not found.`)}
          retry={() => {
            void findingQuery.refetch();
            void evidenceQuery.refetch();
            void counterfactualQuery.refetch();
          }}
        />
        <p className="text-center">
          <Link to="/portfolio" className="text-sm font-medium text-[#2563A8] underline underline-offset-4 hover:text-[#123D73]">
            Back to portfolio
          </Link>
        </p>
      </div>
    );
  }

  const evidence = evidenceQuery.data;
  return (
    <div className="space-y-4">
      <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-xs text-[#52606D]">
        <Link
          to={`/portfolio${runId ? `?run=${encodeURIComponent(runId)}` : ''}`}
          className="rounded border border-[#D9E2EC] bg-white px-2.5 py-1 text-xs font-medium text-[#123B5D] hover:bg-[#EAF3F8] hover:border-[#1F5F8B] transition-colors"
        >
          Portfolio
        </Link>
        <span aria-hidden="true" className="text-slate-400">›</span>
        <Link
          to={`/entities/${finding.entity_id}${runId ? `?run=${encodeURIComponent(runId)}` : ''}`}
          className="mono rounded border border-[#D9E2EC] bg-white px-2.5 py-1 text-xs font-medium text-[#123B5D] hover:bg-[#EAF3F8] hover:border-[#1F5F8B] transition-colors"
        >
          {finding.entity_id}
        </Link>
        <span aria-hidden="true" className="text-slate-400">›</span>
        <span className="mono font-semibold text-[#1F2933]">{finding.signal_id}</span>
      </nav>
      <ErrorBoundary label="Finding detail">
        <FindingDetail
          finding={finding}
          evidence={
            evidence
              ? {
                  finding_id: findingId,
                  evidence_id: evidence.provenance.evidence_id,
                  supporting_rows: evidence.supporting_rows,
                  counter_rows: evidence.counter_rows,
                  counter_rows_absent_reason: evidence.counter_rows_absent_reason,
                  cohort_comparison: {},
                  retrieved_at: '',
                }
              : {
                  finding_id: findingId,
                  evidence_id: '',
                  supporting_rows: [],
                  counter_rows: [],
                  counter_rows_absent_reason: 'Evidence unavailable.',
                  cohort_comparison: {},
                  retrieved_at: '',
                }
          }
          counterfactual={counterfactualQuery.data?.counterfactual ?? null}
        />
      </ErrorBoundary>
    </div>
  );
}
