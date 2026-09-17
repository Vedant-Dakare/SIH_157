import { Link, useParams, useSearchParams } from 'react-router-dom';

import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { ErrorState } from '@/components/common/ErrorState';
import { LoadingState } from '@/components/common/LoadingState';
import { FindingDetail } from '@/components/findings/FindingDetail';
import { useCounterfactual, useEvidence, useFinding } from '@/hooks/useEvidence';

/** Finding detail: parallel fetch, 7-section view, clear 404. */
export default function FindingDetailPage() {
  const { findingId } = useParams();
  const [searchParams] = useSearchParams();
  const runId = searchParams.get('run') ?? '';

  const findingQuery = useFinding(findingId);
  const evidenceQuery = useEvidence(findingId);
  const counterfactualQuery = useCounterfactual(findingId);

  if (!findingId) {
    return (
      <div className="space-y-4 text-center">
        <h2 className="text-lg font-semibold text-slate-50">Finding not found</h2>
        <p className="text-sm text-slate-400">No finding id in the URL.</p>
        <Link to="/portfolio" className="text-sm text-slate-50 underline underline-offset-4">
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
          <Link to="/portfolio" className="text-sm text-slate-50 underline underline-offset-4">
            Back to portfolio
          </Link>
        </p>
      </div>
    );
  }

  const evidence = evidenceQuery.data;
  return (
    <div className="space-y-4">
      <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm text-slate-400">
        <Link to={`/portfolio${runId ? `?run=${encodeURIComponent(runId)}` : ''}`} className="underline underline-offset-4 hover:text-slate-50">
          Portfolio
        </Link>
        <span aria-hidden="true">›</span>
        <Link
          to={`/entities/${finding.entity_id}${runId ? `?run=${encodeURIComponent(runId)}` : ''}`}
          className="mono underline underline-offset-4 hover:text-slate-50"
        >
          {finding.entity_id}
        </Link>
        <span aria-hidden="true">›</span>
        <span className="mono text-slate-50">{finding.signal_id}</span>
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
