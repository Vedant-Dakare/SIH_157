import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RiskBandChart } from '@/components/charts/RiskBandChart';
import type { RiskBand } from '@/types/api';

const DATA: Record<RiskBand, number> = { HIGH: 2, ELEVATED: 1, MODERATE: 1, LOW: 6 };

describe('RiskBandChart', () => {
  it('renders without crashing on valid data', () => {
    const { container } = render(<RiskBandChart data={DATA} isLoading={false} />);
    expect(container.querySelector('svg')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('lists all 4 bands in the legend', () => {
    render(<RiskBandChart data={DATA} isLoading={false} />);
    const legend = screen.getByLabelText('Risk band legend');
    for (const band of ['HIGH', 'ELEVATED', 'MODERATE', 'LOW'] as const) {
      expect(legend).toHaveTextContent(band);
    }
  });

  it('shows a skeleton while loading', () => {
    render(<RiskBandChart data={DATA} isLoading />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });
});
