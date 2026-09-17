import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { RiskBadge } from '@/components/common/RiskBadge';
import { BAND_DESCRIPTIONS } from '@/lib/constants';
import type { RiskBand } from '@/types/api';

vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: ReactNode }) => (
    <div role="tooltip">{children}</div>
  ),
}));

describe('RiskBadge', () => {
  it('renders HIGH in red with correct label', () => {
    render(<RiskBadge band="HIGH" />);
    const label = screen.getByText('HIGH');
    expect(label).toBeInTheDocument();
    expect(label.className).toMatch(/red-500/);
    expect(screen.getByRole('tooltip')).toHaveTextContent(/Score ≥ 75/);
  });

  it('renders all 4 bands without error', () => {
    const bands: RiskBand[] = ['HIGH', 'ELEVATED', 'MODERATE', 'LOW'];
    render(
      <div>
        {bands.map((band) => (
          <RiskBadge key={band} band={band} />
        ))}
      </div>,
    );
    for (const band of bands) {
      expect(screen.getByText(band)).toBeInTheDocument();
    }
  });

  it('wires the band description into the tooltip', () => {
    render(<RiskBadge band="LOW" />);
    expect(screen.getByRole('tooltip')).toHaveTextContent(BAND_DESCRIPTIONS.LOW);
  });
});
