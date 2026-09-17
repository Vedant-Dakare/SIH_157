import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

import PortfolioPage from '@/pages/PortfolioPage';
import { ToastProvider, ToastViewport } from '@/components/ui/toaster';
import { server } from '@/tests/mocks/handlers';
import { http, HttpResponse } from 'msw';

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

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/portfolio?run=demo']}>
          <PortfolioPage />
        </MemoryRouter>
        <ToastViewport />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe('PortfolioPage', () => {
  it('renders with MSW data, run selector and working trigger button', async () => {
    const user = userEvent.setup();
    renderPage();
    expect(await screen.findByText('Total Entities')).toBeInTheDocument();
    expect(screen.getAllByText('cse_alpha').length).toBeGreaterThan(0);
    expect(await screen.findByDisplayValue('demo')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Trigger pipeline run' }));
    await waitFor(() => {
      expect(screen.getByText('Pipeline run started')).toBeInTheDocument();
    });
  });

  it('run selector switches the run param', async () => {
    renderPage();
    const select = await screen.findByDisplayValue('demo');
    fireEvent.change(select, { target: { value: 'e2e' } });
    expect(await screen.findByDisplayValue('e2e')).toBeInTheDocument();
  });

  it('a queue error does not crash the entity sections', async () => {
    server.use(
      http.get('http://127.0.0.1:8080/queue', () =>
        HttpResponse.json({ run_id: 'demo', generated_at: '', error: 'down' }, { status: 500 }),
      ),
    );
    renderPage();
    expect(await screen.findByText('Signal data unavailable.')).toBeInTheDocument();
    expect(screen.getAllByText('cse_alpha').length).toBeGreaterThan(0);
  });
});
