import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { RunManifest } from '@/components/audit/RunManifest';
import { ToastProvider } from '@/components/ui/toaster';
import { mockManifest } from '@/tests/mocks/data';

describe('RunManifest', () => {
  it('renders all manifest fields', () => {
    render(
      <ToastProvider>
        <RunManifest manifest={mockManifest} runId="demo" onVerify={() => undefined} />
      </ToastProvider>,
    );
    expect(screen.getByText('demo')).toBeInTheDocument();
    expect(screen.getByText(/5 \/ 10 \/ 10/)).toBeInTheDocument();
    expect(screen.getByText('phase2-registry')).toBeInTheDocument();
    expect(screen.getByText('m'.repeat(64))).toBeInTheDocument();
  });

  it('verify button triggers verification', async () => {
    const user = userEvent.setup();
    const onVerify = vi.fn();
    render(
      <ToastProvider>
        <RunManifest manifest={mockManifest} runId="demo" onVerify={onVerify} />
      </ToastProvider>,
    );
    await user.click(screen.getByRole('button', { name: 'Verify audit chain' }));
    expect(onVerify).toHaveBeenCalledOnce();
  });

  it('warns when a run recorded zero findings', () => {
    render(
      <ToastProvider>
        <RunManifest
          manifest={{ ...mockManifest, finding_count: 0 }}
          runId="demo"
          onVerify={() => undefined}
        />
      </ToastProvider>,
    );
    expect(screen.getByText(/recorded no findings/)).toBeInTheDocument();
  });
});
