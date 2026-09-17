import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { EvidencePanel } from '@/components/findings/EvidencePanel';
import { mockEvidence } from '@/tests/mocks/data';

describe('EvidencePanel', () => {
  it('supporting tab shows the correct row count', () => {
    render(
      <EvidencePanel
        supportingRows={mockEvidence.supporting_rows}
        counterRows={mockEvidence.counter_rows}
        counterAbsentReason={mockEvidence.counter_rows_absent_reason}
        evidenceId={mockEvidence.evidence_id}
      />,
    );
    expect(screen.getByRole('tab', { name: /Supporting Evidence \(2\)/ })).toBeInTheDocument();
    expect(screen.getByText('c1')).toBeInTheDocument();
    expect(screen.getByText('c2')).toBeInTheDocument();
  });

  it('counter tab exists even when counter rows are empty, with the reason', () => {
    render(
      <EvidencePanel
        supportingRows={mockEvidence.supporting_rows}
        counterRows={[]}
        counterAbsentReason="no counter-examples in window"
        evidenceId={mockEvidence.evidence_id}
      />,
    );
    fireEvent.click(screen.getByRole('tab', { name: /Counter-Evidence \(0\)/ }));
    expect(screen.getByText(/no counter-examples in window/)).toBeInTheDocument();
  });

  it('renders the evidence id hash display', () => {
    render(
      <EvidencePanel
        supportingRows={mockEvidence.supporting_rows}
        counterRows={mockEvidence.counter_rows}
        counterAbsentReason=""
        evidenceId={mockEvidence.evidence_id}
      />,
    );
    expect(screen.getByLabelText(/evidence_id e1e2e3e4/)).toBeInTheDocument();
  });
});
