import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { FindingDetail } from '@/components/findings/FindingDetail';
import { mockCounterfactual, mockEvidence, mockFindings } from '@/tests/mocks/data';
import type { CompositeReasonCode } from '@/components/findings/ReasonCodeDisplay';

vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: ReactNode }) => (
    <div role="tooltip">{children}</div>
  ),
}));

const NARRATED = {
  ...mockFindings[0],
  rationale: 'Two rushed closures with identical dispositions were observed.',
  what_we_observed: 'Premature rate 1.0 vs threshold 0.2.',
  why_it_matters: 'Cursory triage hides unresolved risk.',
  peer_context: 'Peers sit near 0.1.',
  confidence_statement: 'Medium confidence on 12 records.',
  suggested_review_focus: 'Walk through the cited rows and confirm practice vs coverage.',
  generated_by: 'template',
};

const COMPOSITE: CompositeReasonCode = {
  code: 'COMP-001',
  label: 'Superficial compliance',
  observed: 3,
  threshold: 3,
  comparator: '>=',
  peer_baseline: { median: 0, p95: 0, n: 0, cohort_id: 'unknown' },
  window: 'w',
  severity: 'HIGH',
  confidence: 'MEDIUM',
  plain_language: 'Composite pattern observed.',
  expression: '(EG-003 AND EG-013) AND (NS-005 OR NS-006)',
  expression_tree: { AND: ['EG-003', { OR: ['NS-005', 'NS-006'] }, 'EG-013'] },
  leaf_codes: [
    {
      code: 'EG-003',
      label: 'Escalation bypass',
      observed: 1,
      threshold: 0.9,
      comparator: '>=',
      peer_baseline: { median: 0, p95: 0, n: 0, cohort_id: 'unknown' },
      window: 'w',
      severity: 'HIGH',
      confidence: 'MEDIUM',
      plain_language: 'Leaf observed.',
    },
  ],
};

function renderDetail() {
  return render(
    <MemoryRouter>
      <FindingDetail finding={NARRATED} evidence={mockEvidence} counterfactual={mockCounterfactual} />
    </MemoryRouter>,
  );
}

describe('FindingDetail', () => {
  it('renders all 7 sections', () => {
    renderDetail();
    for (const section of [
      'Finding header',
      'Reason code',
      'Narrative',
      'Evidence',
      'Counterfactual',
      'Peer baseline',
      'Audit reference',
    ]) {
      expect(screen.getByLabelText(section, { selector: 'section' })).toBeInTheDocument();
    }
  });

  it('highlights the review focus and labels the generator', () => {
    renderDetail();
    expect(screen.getByText(/Walk through the cited rows/)).toBeInTheDocument();
    expect(screen.getByText('template')).toBeInTheDocument();
  });

  it('renders an expandable composite tree with clickable leaves', async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <FindingDetail
          finding={NARRATED}
          evidence={mockEvidence}
          counterfactual={mockCounterfactual}
          reasonCode={COMPOSITE}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText(/EG-003 AND EG-013/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Inspect leaf reason code EG-003/ }));
    expect(screen.getByText('Leaf observed.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Back to composite reason' })).toBeInTheDocument();
  });
});
