import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ColumnDef } from '@tanstack/react-table';
import { describe, expect, it, vi } from 'vitest';

import { DataTable } from '@/components/common/DataTable';

interface Row {
  id: string;
  score: number;
}

const COLUMNS: ColumnDef<Row>[] = [
  { accessorKey: 'id', header: 'ID' },
  { accessorKey: 'score', header: 'Score' },
];

const ROWS: Row[] = [
  { id: 'c', score: 30 },
  { id: 'a', score: 10 },
  { id: 'b', score: 20 },
];

function cellTexts(): string[] {
  const table = screen.getByRole('table');
  return within(table).getAllByRole('row').slice(1).map((row) => row.textContent ?? '');
}

describe('DataTable', () => {
  it('renders data with the correct row count', () => {
    render(<DataTable columns={COLUMNS} data={ROWS} isLoading={false} error={null} />);
    expect(cellTexts()).toHaveLength(3);
  });

  it('renders skeleton rows while loading', () => {
    render(<DataTable columns={COLUMNS} data={[]} isLoading error={null} />);
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders the empty message when there is no data', () => {
    render(
      <DataTable
        columns={COLUMNS}
        data={[]}
        isLoading={false}
        error={null}
        emptyTitle="Nothing here"
        emptyDescription="No rows at all."
      />,
    );
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });

  it('renders the error message with a retry button', async () => {
    const user = userEvent.setup();
    const retry = vi.fn();
    render(<DataTable columns={COLUMNS} data={[]} isLoading={false} error={new Error('boom')} onRetry={retry} />);
    expect(screen.getByText('boom')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Retry request' }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it('sorts rows when the header is clicked', async () => {
    const user = userEvent.setup();
    render(<DataTable columns={COLUMNS} data={ROWS} isLoading={false} error={null} />);
    expect(cellTexts()[0]).toContain('c');
    // Numeric columns sort descending first, then ascending.
    await user.click(screen.getByRole('button', { name: 'Sort by score' }));
    expect(cellTexts()[0]).toContain('c');
    expect(cellTexts()[2]).toContain('a');
    await user.click(screen.getByRole('button', { name: 'Sort by score' }));
    expect(cellTexts()[0]).toContain('a');
    expect(cellTexts()[2]).toContain('c');
  });

  it('filters rows as the user types', async () => {
    const user = userEvent.setup();
    render(<DataTable columns={COLUMNS} data={ROWS} isLoading={false} error={null} />);
    await user.type(screen.getByRole('searchbox'), 'b');
    const rows = cellTexts();
    expect(rows).toHaveLength(1);
    expect(rows[0]).toContain('b');
  });
});
