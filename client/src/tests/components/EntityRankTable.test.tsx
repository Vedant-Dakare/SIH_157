import type { ReactNode } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { EntityRankTable } from '@/components/portfolio/EntityRankTable';
import { mockEntities } from '@/tests/mocks/data';

vi.mock('@/components/ui/select', () => ({
  Select: ({
    value,
    onValueChange,
    children,
  }: {
    value: string;
    onValueChange: (value: string) => void;
    children: ReactNode;
  }) => (
    <select aria-label="mocked select" value={value} onChange={(event) => onValueChange(event.target.value)}>
      {children}
    </select>
  ),
  SelectTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  SelectValue: () => null,
  SelectContent: ({ children }: { children: ReactNode }) => <>{children}</>,
  SelectItem: ({ value, children }: { value: string; children: ReactNode }) => (
    <option value={value}>{children}</option>
  ),
}));

const SUPPLEMENT = {
  cse_alpha: { signalsFired: 2, trend: 'NEW', dataCompleteness: 0.97 },
  cse_bravo: { signalsFired: 1, trend: 'PERSISTENT', dataCompleteness: 0.95 },
  cse_charlie: { signalsFired: 1, trend: 'NEW', dataCompleteness: 0.9 },
  cse_delta: { signalsFired: 0, trend: '—', dataCompleteness: 0.93 },
  cse_echo: { signalsFired: 0, trend: '—', dataCompleteness: 0.42 },
};

function DetailProbe() {
  const { entityId } = useParams();
  return <p>detail-{entityId}</p>;
}

function Harness() {
  return (
    <MemoryRouter initialEntries={['/entities']}>
      <Routes>
        <Route
          path="/entities"
          element={<EntityRankTable entities={mockEntities} isLoading={false} runId="demo" supplement={SUPPLEMENT} />}
        />
        <Route path="/entities/:entityId" element={<DetailProbe />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('EntityRankTable', () => {
  it('renders all entities from mock data', () => {
    render(<Harness />);
    for (const entity of mockEntities) {
      expect(screen.getByText(entity.entity_id)).toBeInTheDocument();
    }
  });

  it('paints HIGH band rows with a red background class', () => {
    const { container } = render(<Harness />);
    const highRow = screen.getByText('cse_alpha').closest('tr');
    expect(highRow?.className ?? container.innerHTML).toMatch(/red-950/);
  });

  it('separates insufficient-evidence entities with an explanation', () => {
    render(<Harness />);
    expect(screen.getByText(/not ranked/i)).toBeInTheDocument();
    expect(screen.getByText('cse_echo')).toBeInTheDocument();
  });

  it('sorts by score when the header is clicked twice', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    // Numeric columns sort descending first (no visible change), then ascending.
    // cse_echo sits in the separate insufficient-evidence table, so the main
    // table ascending order starts with cse_delta.
    await user.click(screen.getAllByRole('button', { name: 'Sort by overall_score' })[0]);
    await user.click(screen.getAllByRole('button', { name: 'Sort by overall_score' })[0]);
    const table = screen.getAllByRole('table')[0];
    const firstRow = table.querySelector('tbody tr');
    expect(firstRow?.textContent ?? '').toContain('cse_delta');
  });

  it('filtering to band HIGH reduces the visible rows', () => {
    render(<Harness />);
    const selects = screen.getAllByLabelText('mocked select');
    fireEvent.change(selects[0], { target: { value: 'HIGH' } });
    expect(screen.getByText('cse_alpha')).toBeInTheDocument();
    expect(screen.queryByText('cse_bravo')).not.toBeInTheDocument();
  });

  it('row click navigates to the entity URL', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByText('cse_bravo'));
    expect(await screen.findByText('detail-cse_bravo')).toBeInTheDocument();
  });
});
