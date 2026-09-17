import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import ValidationPage, { ValidationSections } from '@/pages/ValidationPage';
import { ToastProvider } from '@/components/ui/toaster';
import type { ValidationReport } from '@/types/api';

const REPORT: ValidationReport = {
  run_id: 'demo',
  generated_at: '2024-06-01T12:00:00Z',
  label_source: 'synthetic',
  precision_at_k: { '5': 0.8, '10': 0.7, '20': 0.6 },
  recall_by_scenario: { S1: 1.0, S2: 1.0 },
  overall_recall: 0.8,
  overall_precision: 0.44,
  f1_by_family: { execution_gap: 0.5 },
  cohens_kappa: 0.83,
  krippendorffs_alpha: 0.81,
  coverage_rate: 0.8,
  n_expected: 10,
  n_flagged: 18,
  n_hits: 8,
};

const ABLATION = [
  {
    family_name: 'execution_gap',
    signals_disabled: ['EG-001'],
    baseline_recall: 0.8,
    ablated_recall: 0.1,
    recall_drop: 0.7,
    relative_contribution_pct: 87.5,
  },
  {
    family_name: 'negative_space',
    signals_disabled: ['NS-001'],
    baseline_recall: 0.8,
    ablated_recall: 0.7,
    recall_drop: 0.1,
    relative_contribution_pct: 12.5,
  },
];

function renderSections() {
  return render(
    <ToastProvider>
      <MemoryRouter>
        <ValidationSections
          report={REPORT}
          extras={{
            ablation: ABLATION,
            disagreements: [
              {
                entity_id: 'cse_x',
                signal_id: 'EG-001',
                sat_sa_flagged: true,
                expert_flagged: false,
                kind: 'SAT-SA only',
                finding_id: 'f1',
              },
            ],
          }}
        />
      </MemoryRouter>
    </ToastProvider>,
  );
}

describe('ValidationPage', () => {
  it('renders 4 metric cards with values', () => {
    renderSections();
    expect(screen.getByText('Precision@10')).toBeInTheDocument();
    // 0.700 appears on the card and on the matching precision bar.
    expect(screen.getAllByText('0.700')).toHaveLength(2);
    expect(screen.getByText("Cohen's Kappa")).toBeInTheDocument();
    expect(screen.getByText('0.830')).toBeInTheDocument();
  });

  it('ablation tab lists contributions sorted descending', async () => {
    const user = userEvent.setup();
    renderSections();
    await user.click(screen.getByRole('tab', { name: 'Ablation' }));
    const rows = screen.getAllByRole('row');
    expect(rows[1]?.textContent ?? '').toContain('execution_gap');
    expect(rows[2]?.textContent ?? '').toContain('negative_space');
  });

  it('disagreement export button downloads a CSV', async () => {
    const user = userEvent.setup();
    renderSections();
    await user.click(screen.getByRole('tab', { name: 'Disagreements' }));
    expect(screen.getByRole('button', { name: 'Export disagreements as CSV' })).toBeInTheDocument();
    expect(screen.getByText('cse_x')).toBeInTheDocument();
  });

  it('page without a report endpoint shows artefact guidance', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/validation?run=demo']}>
          <ValidationPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText('No validation report')).toBeInTheDocument();
  });
});
