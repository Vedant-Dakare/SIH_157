import type { ReactNode } from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { EntityHeader } from '@/components/entity/EntityHeader';
import { mockEntityDetail } from '@/tests/mocks/data';

vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: ReactNode }) => (
    <div role="tooltip">{children}</div>
  ),
}));

const LOW_DETAIL = { ...mockEntityDetail, data_completeness: 0.42, capped_by_completeness: true };

describe('EntityHeader', () => {
  it('renders the entity id in monospace', () => {
    render(
      <MemoryRouter>
        <EntityHeader entity={mockEntityDetail} runId="demo" />
      </MemoryRouter>,
    );
    const id = screen.getByText('cse_alpha');
    expect(id.tagName).toBe('CODE');
    expect(id.className).toMatch(/mono/);
  });

  it('does not display intrusive yellow warning banner when completeness is low', () => {
    render(
      <MemoryRouter>
        <EntityHeader entity={LOW_DETAIL} runId="demo" />
      </MemoryRouter>,
    );
    expect(screen.getByText('Data completeness')).toBeInTheDocument();
    expect(screen.queryByText('Insufficient evidence')).not.toBeInTheDocument();
  });

  it('risk badge matches the band in mock data', () => {
    render(
      <MemoryRouter>
        <EntityHeader entity={mockEntityDetail} runId="demo" />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText('Risk band HIGH')).toBeInTheDocument();
  });

  it('confidence badge carries the reason in its tooltip', () => {
    render(
      <MemoryRouter>
        <EntityHeader entity={mockEntityDetail} runId="demo" />
      </MemoryRouter>,
    );
    const tips = screen.getAllByRole('tooltip');
    expect(tips.some((tip) => tip.textContent?.includes('Data completeness 0.97'))).toBe(true);
  });
});
