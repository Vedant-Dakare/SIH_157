import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PortfolioSummary } from '@/components/portfolio/PortfolioSummary';
import { mockEntities } from '@/tests/mocks/data';
import type { PortfolioSummary as Summary } from '@/types/api';

const SUMMARY: Summary = {
  entity_count_by_band: { HIGH: 1, ELEVATED: 1, MODERATE: 1, LOW: 2 },
  top_5_entities_by_risk: mockEntities.map((entity) => entity.entity_id),
  sector_aggregates: { finance: 71.7 },
  portfolio_trend: 'STABLE',
};

describe('PortfolioSummary', () => {
  it('renders 4 stat cards with mock data', () => {
    render(
      <PortfolioSummary summary={SUMMARY} isLoading={false} findingsCount={12} avgCompleteness={0.95} />,
    );
    expect(screen.getByText('Total Entities')).toBeInTheDocument();
    expect(screen.getByText('HIGH Risk Entities')).toBeInTheDocument();
    expect(screen.getByText('Active Findings')).toBeInTheDocument();
    expect(screen.getByText('Data Quality')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('highlights the HIGH card in red when count is above zero', () => {
    render(<PortfolioSummary summary={SUMMARY} isLoading={false} />);
    const value = screen.getByText('1', { selector: 'p.text-2xl' });
    expect(value.className).toMatch(/red-500/);
  });

  it('shows skeletons while loading', () => {
    render(<PortfolioSummary summary={SUMMARY} isLoading />);
    expect(screen.getByLabelText('Loading summary')).toBeInTheDocument();
  });

  it('points delta arrows in the correct direction', () => {
    render(
      <PortfolioSummary
        summary={SUMMARY}
        isLoading={false}
        deltas={{ high: { value: 2, label: 'vs prior' }, findings: { value: -1, label: 'vs prior' } }}
      />,
    );
    expect(screen.getByText('+2 vs prior')).toBeInTheDocument();
    expect(screen.getByText('-1 vs prior')).toBeInTheDocument();
  });
});
