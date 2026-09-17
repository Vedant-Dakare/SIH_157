import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LedgerTable } from '@/components/audit/LedgerTable';
import type { AuditEntry } from '@/types/api';

const GENESIS = '0'.repeat(64);
const ENTRY_0: AuditEntry = {
  seq: 0,
  run_id: 'demo',
  ts: '2024-06-01T12:00:00+00:00',
  event_type: 'RUN_START',
  payload: { seed: 42 },
  prev_hash: GENESIS,
  entry_hash: '82c866069564d286068b9e552e5e7d07ec3bae7e661a5644aec508fe4334b04b',
  signature: null,
};
const ENTRY_1: AuditEntry = {
  seq: 1,
  run_id: 'demo',
  ts: '2024-06-01T12:01:00+00:00',
  event_type: 'FINDING',
  payload: { finding_id: 'f1', n: 7, ok: true },
  prev_hash: ENTRY_0.entry_hash,
  entry_hash: '0d71c4a7c04751ac79129f8bfac47bb17297c8c1302aff6d876e84736f4e8911',
  signature: null,
};

describe('LedgerTable', () => {
  it('marks backend-computed entries valid', async () => {
    render(<LedgerTable entries={[ENTRY_0, ENTRY_1]} isLoading={false} />);
    await waitFor(() => {
      expect(screen.getByLabelText('Entry 0 ok')).toBeInTheDocument();
    });
    expect(screen.getByLabelText('Entry 1 ok')).toBeInTheDocument();
  });

  it('marks a tampered entry with a red cross', async () => {
    const tampered = { ...ENTRY_1, payload: { ...ENTRY_1.payload, n: 999 } };
    render(<LedgerTable entries={[ENTRY_0, tampered]} isLoading={false} />);
    await waitFor(() => {
      expect(screen.getByLabelText('Entry 1 tampered')).toBeInTheDocument();
    });
  });

  it('expands a row to show payload JSON', async () => {
    render(<LedgerTable entries={[ENTRY_0]} isLoading={false} />);
    fireEvent.click(screen.getByRole('button', { name: 'Expand entry 0' }));
    expect(await screen.findByText(/"seed": 42/)).toBeInTheDocument();
  });

  it('shows both event types with filter controls present', async () => {
    render(<LedgerTable entries={[ENTRY_0, ENTRY_1]} isLoading={false} />);
    expect(await screen.findByText('RUN_START')).toBeInTheDocument();
    expect(screen.getByText('FINDING')).toBeInTheDocument();
    expect(screen.getByLabelText('Filter by run')).toBeInTheDocument();
    expect(screen.getByLabelText('Filter by event type')).toBeInTheDocument();
  });
});
