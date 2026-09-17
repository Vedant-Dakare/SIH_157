import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import { ToastProvider, ToastViewport } from '@/components/ui/toaster';
import AuditPage from '@/pages/AuditPage';
import EntityDetailPage from '@/pages/EntityDetailPage';
import FindingDetailPage from '@/pages/FindingDetailPage';
import PortfolioPage from '@/pages/PortfolioPage';
import QueuePage from '@/pages/QueuePage';
import RunsPage from '@/pages/RunsPage';

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

vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: ReactNode }) => (
    <div role="tooltip">{children}</div>
  ),
}));

function renderApp(initialPath: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="/portfolio" element={<PortfolioPage />} />
            <Route path="/entities/:entityId" element={<EntityDetailPage />} />
            <Route path="/findings/:findingId" element={<FindingDetailPage />} />
            <Route path="/queue" element={<QueuePage />} />
            <Route path="/audit" element={<AuditPage />} />
            <Route path="/runs" element={<RunsPage />} />
          </Routes>
        </MemoryRouter>
        <ToastViewport />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe('smoke: portfolio → entity → finding', () => {
  it('walks the full drill-down with all panels rendering', async () => {
    const user = userEvent.setup();
    renderApp('/portfolio?run=demo');
    expect(await screen.findByText('Total Entities')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'View cse_alpha' }));
    expect(await screen.findByRole('tab', { name: 'Findings' })).toBeInTheDocument();

    await user.click(screen.getByRole('tab', { name: 'Findings' }));
    const expanders = await screen.findAllByRole('button', { name: /Expand rationale/ });
    await user.click(expanders[0]);
    await user.click(screen.getByRole('button', { name: 'View Full Finding' }));
    expect(await screen.findByText(/EG-001 would not fire/)).toBeInTheDocument();
    expect(screen.getByText('Peer baseline')).toBeInTheDocument();
  }, 30000);
});

describe('smoke: queue samples', () => {
  it('expands a row to reveal sample IDs', async () => {
    const user = userEvent.setup();
    renderApp('/queue?run=demo');
    expect(await screen.findByText('cse_alpha')).toBeInTheDocument();
    await user.click(screen.getAllByRole('button', { name: /Show sample records/ })[0]);
    expect(screen.getByText('a1')).toBeInTheDocument();
    expect(screen.getByText('c1')).toBeInTheDocument();
  }, 30000);
});

describe('smoke: audit auto-verify', () => {
  it('verifies the chain automatically on load', async () => {
    renderApp('/audit?run=demo');
    expect(await screen.findByText(/Audit chain intact/)).toBeInTheDocument();
  }, 30000);
});

describe('smoke: runs trigger flow', () => {
  it('triggers a run and reports completion', async () => {
    const user = userEvent.setup();
    renderApp('/runs');
    await user.click(await screen.findByRole('button', { name: 'Trigger pipeline run' }));
    expect(await screen.findByText('Run started')).toBeInTheDocument();
    expect(
      await screen.findByText('Run complete — view results', {}, { timeout: 15000 }),
    ).toBeInTheDocument();
  }, 30000);
});
