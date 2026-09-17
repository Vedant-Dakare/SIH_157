import type { ReactNode } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { FindingsTable, type FindingRow } from '@/components/entity/FindingsTable';
import { mockFindings } from '@/tests/mocks/data';

vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: ReactNode }) => (
    <div role="tooltip">{children}</div>
  ),
}));

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

const ROWS: FindingRow[] = mockFindings.slice(0, 6).map((finding, index) => ({
  ...finding,
  finding_id: `fx-${index}`,
  signalName: finding.label,
  trend: index % 2 === 0 ? 'NEW' : 'PERSISTENT',
  sampleSize: 12,
  rationale: `Rationale preview number ${index} with enough words.`,
}));

function renderTable(rows: FindingRow[] = ROWS) {
  return render(
    <FindingsTable findings={rows} isLoading={false} onSelect={() => undefined} />,
  );
}

describe('FindingsTable', () => {
  it('renders all findings', () => {
    renderTable();
    for (const row of ROWS) {
      expect(
        screen.getByLabelText(new RegExp(`^Signal ${row.signal_id},`)),
      ).toBeInTheDocument();
    }
  });

  it('severity filter reduces rows to CRITICAL-adjacent matches', () => {
    renderTable();
    const selects = screen.getAllByLabelText('mocked select');
    fireEvent.change(selects[1], { target: { value: 'HIGH' } });
    expect(screen.getByLabelText(/^Signal EG-001,/)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^Signal NS-005,/)).not.toBeInTheDocument();
  });

  it('group toggle inserts family group rows', () => {
    renderTable();
    expect(screen.queryByText('execution gap')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Group by family' }));
    expect(screen.getByText('execution gap')).toBeInTheDocument();
  });

  it('expanding a row shows the rationale preview', async () => {
    const user = userEvent.setup();
    renderTable();
    await user.click(screen.getAllByLabelText(/rationale for EG-001/)[0]);
    expect(screen.getByText(/Rationale preview number 0/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'View Full Finding' })).toBeInTheDocument();
  });

  it('empty state renders when findings are empty', () => {
    renderTable([]);
    expect(screen.getByText('No findings')).toBeInTheDocument();
  });
});
