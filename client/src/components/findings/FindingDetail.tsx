import * as React from 'react';
import { Link } from 'react-router-dom';
import { HelpCircle } from 'lucide-react';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import { HashDisplay } from '@/components/common/HashDisplay';
import { RiskBadge } from '@/components/common/RiskBadge';
import { SignalBadge } from '@/components/common/SignalBadge';
import { CounterfactualPanel } from '@/components/findings/CounterfactualPanel';
import { EvidencePanel } from '@/components/findings/EvidencePanel';
import { PeerBaselinePanel, type PeerBaseline } from '@/components/findings/PeerBaselinePanel';
import { ReasonCodeDisplay, type CompositeReasonCode } from '@/components/findings/ReasonCodeDisplay';
import { Badge } from '@/components/ui/badge';
import { formatDate } from '@/lib/utils';
import type {
  Counterfactual,
  EvidenceBundle,
  Finding,
  ReasonCode,
  RiskBand,
  SignalFamily,
} from '@/types/api';

export interface FindingNarrative {
  rationale?: string;
  what_we_observed?: string;
  why_it_matters?: string;
  peer_context?: string;
  confidence_statement?: string;
  suggested_review_focus?: string;
  generated_by?: string;
}

export interface FindingDetailProps {
  finding: Finding & Partial<FindingNarrative>;
  evidence: EvidenceBundle;
  counterfactual: Counterfactual | null;
  reasonCode?: ReasonCode | CompositeReasonCode;
  peerBaseline?: PeerBaseline;
  computedAt?: string;
  auditSeq?: number | null;
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

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section aria-label={title} className="console-card p-4 sm:p-5">
      <h3 className="console-label mb-3">{title}</h3>
      {children}
    </section>
  );
}

/** Full finding view: header, reason, narrative, evidence, counterfactual, peer, audit. */
export function FindingDetail({
  finding,
  evidence,
  counterfactual,
  reasonCode,
  peerBaseline,
  computedAt,
  auditSeq,
}: FindingDetailProps) {
  const [selectedLeaf, setSelectedLeaf] = React.useState<ReasonCode | null>(null);
  const code: ReasonCode | CompositeReasonCode = reasonCode ?? {
    code: finding.signal_id,
    label: finding.label,
    observed: finding.observed,
    threshold: finding.threshold,
    comparator: '>=',
    peer_baseline: { median: 0, p95: 0, n: 0, cohort_id: 'unknown' },
    window: finding.window,
    severity: finding.severity,
    confidence: finding.confidence,
    plain_language: finding.plain_language,
  };
  const baseline: PeerBaseline = peerBaseline ?? {
    median: Number(finding.peer_baseline.median ?? 0),
    p95: Number(finding.peer_baseline.p95 ?? 0),
    cohort_n: Number(finding.peer_baseline.n ?? 0),
    cohort_id: String(finding.peer_baseline.cohort_id ?? 'unknown'),
    entity_value: Number(finding.observed ?? 0),
  };

  return (
    <div className="space-y-4">
      <Section title="Finding header">
        <div className="flex flex-wrap items-center gap-2">
          <span className="mono text-lg font-bold text-[#102A56]">{finding.signal_id}</span>
          <SignalBadge signalId={finding.signal_id} family={familyOf(finding.signal_id)} />
          <Badge variant="outline">{finding.severity}</Badge>
          <ConfidenceBadge confidence={finding.confidence} reason={finding.confidence_reason} />
          <RiskBadge band={(finding.band ?? 'LOW') as RiskBand} size="sm" />
        </div>
        <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-500">
          <div className="flex gap-1">
            <dt>Sample size:</dt>
            <dd className="font-medium text-slate-700">{finding.is_flagged ? 'flagged' : 'not flagged'}</dd>
          </div>
          <div className="flex gap-1">
            <dt>Window:</dt>
            <dd className="mono">{finding.window}</dd>
          </div>
          {computedAt ? (
            <div className="flex gap-1">
              <dt>Computed at:</dt>
              <dd>{formatDate(computedAt)}</dd>
            </div>
          ) : null}
        </dl>
      </Section>

      <Section title="Reason code">
        <ReasonCodeDisplay code={selectedLeaf ?? code} onLeafSelect={setSelectedLeaf} />
        {selectedLeaf ? (
          <button
            type="button"
            onClick={() => setSelectedLeaf(null)}
            className="mt-2 text-xs font-medium text-[#2563A8] underline underline-offset-4 hover:text-[#123D73]"
          >
            Back to composite reason
          </button>
        ) : null}
      </Section>

      <Section title="Narrative">
        <p className="text-base leading-relaxed text-slate-800">
          {finding.rationale ?? finding.plain_language}
        </p>
        <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-3">
          {(
            [
              ['Observed', finding.what_we_observed],
              ['Why it matters', finding.why_it_matters],
              ['Peer context', finding.peer_context ?? baseline.cohort_id],
            ] as Array<[string, string | undefined]>
          ).map(([label, text]) =>
            text ? (
              <details key={label} className="rounded-md border border-slate-200 bg-slate-50 p-2">
                <summary className="cursor-pointer text-xs font-semibold text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-200">
                  {label}
                </summary>
                <p className="mt-1 text-sm text-slate-800">{text}</p>
              </details>
            ) : null,
          )}
        </div>
        <p className="mt-3 text-sm italic text-slate-500">
          {finding.confidence_statement ?? `Confidence ${finding.confidence}.`}
        </p>
        {finding.suggested_review_focus ? (
            <p className="mt-2 flex gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            <HelpCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            {finding.suggested_review_focus}
          </p>
        ) : null}
        <p className="mt-2 text-xs text-slate-500">
          Generated by: <span className="mono">{finding.generated_by ?? 'template'}</span>
        </p>
      </Section>

      <Section title="Evidence">
        <EvidencePanel
          supportingRows={evidence.supporting_rows}
          counterRows={evidence.counter_rows}
          counterAbsentReason={evidence.counter_rows_absent_reason}
          evidenceId={evidence.evidence_id}
        />
      </Section>

      <Section title="Counterfactual">
        <CounterfactualPanel result={counterfactual} />
      </Section>

      <Section title="Peer baseline">
        <PeerBaselinePanel baseline={baseline} />
      </Section>

      <Section title="Audit reference">
        {auditSeq !== null && auditSeq !== undefined ? (
          <p className="text-sm text-slate-600">
            Ledger entry seq {auditSeq} —{' '}
            <Link to="/audit" className="font-medium text-[#2563A8] underline underline-offset-4 hover:text-[#123D73]">
              open audit ledger
            </Link>
          </p>
        ) : (
          <p className="text-sm text-slate-500">Not yet recorded in the audit ledger.</p>
        )}
        <div className="mt-2">
          <HashDisplay hash={evidence.evidence_id} label="evidence_id" />
        </div>
      </Section>
    </div>
  );
}
