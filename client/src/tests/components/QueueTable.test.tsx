import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { QueueTable } from '@/components/queue/QueueTable';
import { mockQueue } from '@/tests/mocks/data';

function LocationProbe() {
  const location = useLocation();
  return <p>at:{location.pathname}{location.search}</p>;
}

function Harness() {
  return (
    <MemoryRouter initialEntries={['/queue']}>
      <Routes>
        <Route
          path="/queue"
          element={<QueueTable items={mockQueue} isLoading={false} runId="demo" insufficient={['cse_juliet']} />}
        />
        <Route path="/entities/:entityId" element={<LocationProbe />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('QueueTable', () => {
  it('renders all queue items with rank numbers', () => {
    render(<Harness />);
    for (const item of mockQueue) {
      expect(screen.getByText(item.entity_id)).toBeInTheDocument();
    }
    const table = screen.getByRole('table');
    const firstRank = table.querySelector('tbody tr td');
    expect(firstRank?.textContent).toBe('1');
  });

  it('Start Review stores session state and navigates with the signal filter', async () => {
    const user = userEvent.setup();
    const setItem = vi.spyOn(window.localStorage.__proto__, 'setItem');
    render(<Harness />);
    await user.click(screen.getAllByRole('button', { name: /Start review of/ })[0]);
    expect(setItem).toHaveBeenCalledWith(
      'satsa-in-review-cse_alpha',
      expect.stringContaining('demo'),
    );
    setItem.mockRestore();
    expect(await screen.findByText(/^at:\/entities\/cse_alpha/)).toBeInTheDocument();
  });

  it('keeps the insufficient-evidence section separate and labelled', () => {
    render(<Harness />);
    expect(screen.getByText('Insufficient Evidence — Pending Feed Verification')).toBeInTheDocument();
    expect(screen.getByText('cse_juliet')).toBeInTheDocument();
  });

  it('shows a print button', () => {
    render(<Harness />);
    expect(screen.getByRole('button', { name: 'Print review queue' })).toBeInTheDocument();
  });

  it('sample list expands to reveal alert and case ids', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getAllByRole('button', { name: /Show sample records/ })[0]);
    expect(screen.getByText('a1')).toBeInTheDocument();
    expect(screen.getByText('c1')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Copy all sample IDs/ }));
  });
});
