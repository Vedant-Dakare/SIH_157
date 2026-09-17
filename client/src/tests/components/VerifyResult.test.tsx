import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { VerifyResult } from '@/components/audit/VerifyResult';

describe('VerifyResult', () => {
  it('shows green intact state when valid', () => {
    render(<VerifyResult result={{ valid: true, entry_count: 10, merkle_root: 'm'.repeat(64) }} isLoading={false} />);
    expect(screen.getByText(/Audit chain intact/)).toBeInTheDocument();
    expect(screen.getByText('10 entries verified.')).toBeInTheDocument();
  });

  it('shows the broken sequence number when invalid', () => {
    render(
      <VerifyResult
        result={{ valid: false, entry_count: 10, merkle_root: 'x', first_broken_seq: 4 }}
        isLoading={false}
      />,
    );
    expect(screen.getByText(/Chain broken at entry #4/)).toBeInTheDocument();
  });

  it('shows a spinner while loading', () => {
    render(<VerifyResult result={null} isLoading />);
    expect(screen.getByLabelText('Verification in progress')).toBeInTheDocument();
  });

  it('shows instructions when no result exists yet', () => {
    render(<VerifyResult result={null} isLoading={false} />);
    expect(screen.getByText(/Run verification to check the audit chain/)).toBeInTheDocument();
  });

  it('export button fires for broken chains', async () => {
    const user = userEvent.setup();
    const onExport = vi.fn();
    render(
      <VerifyResult
        result={{ valid: false, entry_count: 3, merkle_root: 'x', first_broken_seq: 1 }}
        isLoading={false}
        onExportBroken={onExport}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'Export broken chain' }));
    expect(onExport).toHaveBeenCalledOnce();
  });
});
