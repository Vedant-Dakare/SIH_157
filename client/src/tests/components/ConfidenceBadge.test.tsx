import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ConfidenceBadge } from '@/components/common/ConfidenceBadge';
import type { ConfidenceLevel } from '@/types/api';

vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: ReactNode }) => (
    <div role="tooltip">{children}</div>
  ),
}));

describe('ConfidenceBadge', () => {
  it('renders all 3 confidence levels', () => {
    const levels: ConfidenceLevel[] = ['HIGH', 'MEDIUM', 'LOW'];
    render(
      <div>
        {levels.map((level) => (
          <ConfidenceBadge key={level} confidence={level} />
        ))}
      </div>,
    );
    for (const level of levels) {
      expect(screen.getByText(level)).toBeInTheDocument();
    }
  });

  it('shows the reason in the tooltip when provided', () => {
    render(<ConfidenceBadge confidence="MEDIUM" reason="Partial feed coverage" />);
    expect(screen.getByRole('tooltip')).toHaveTextContent('Partial feed coverage');
  });

  it('never renders without a visible label', () => {
    render(<ConfidenceBadge confidence="LOW" />);
    const badge = screen.getByLabelText('Confidence LOW');
    expect(badge.textContent ?? '').toContain('LOW');
  });
});
