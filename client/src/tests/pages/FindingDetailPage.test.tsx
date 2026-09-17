import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import FindingDetailPage from '@/pages/FindingDetailPage';
import { ToastProvider } from '@/components/ui/toaster';
import { server } from '@/tests/mocks/handlers';
import { HttpResponse, http } from 'msw';

vi.mock('@/components/ui/tooltip', () => ({
  TooltipProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  Tooltip: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipTrigger: ({ children }: { children: ReactNode }) => <>{children}</>,
  TooltipContent: ({ children }: { children: ReactNode }) => (
    <div role="tooltip">{children}</div>
  ),
}));

function renderPage(findingId = 'f-eg1') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={[`/findings/${findingId}?run=demo`]}>
          <Routes>
            <Route path="/findings/:findingId" element={<FindingDetailPage />} />
            <Route path="/portfolio" element={<p>portfolio landing</p>} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe('FindingDetailPage', () => {
  it('fetches finding, evidence and counterfactual in parallel', async () => {
    renderPage();
    expect(await screen.findByLabelText('Signal EG-001, Execution Gap')).toBeInTheDocument();
    expect(screen.getAllByText('Critical cases closed implausibly fast.').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('c1')).toBeInTheDocument();
    expect(screen.getByText(/EG-001 would not fire/)).toBeInTheDocument();
  });

  it('shows a skeleton while loading', () => {
    renderPage();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows a clear 404 with a back link for unknown findings', async () => {
    server.use(
      http.get('http://127.0.0.1:8080/findings/:findingId', () =>
        HttpResponse.json({ run_id: 'demo', generated_at: '', error: 'gone' }, { status: 404 }),
      ),
    );
    renderPage('missing-id');
    expect(await screen.findByText('Request failed')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Back to portfolio' })).toBeInTheDocument();
  });
});
