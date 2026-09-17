import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { ToastProvider, ToastViewport } from '@/components/ui/toaster';
import RunsPage from '@/pages/RunsPage';
import { server } from '@/tests/mocks/handlers';
import { HttpResponse, http } from 'msw';

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/runs']}>
          <RunsPage />
        </MemoryRouter>
        <ToastViewport />
      </ToastProvider>
    </QueryClientProvider>,
  );
}

describe('RunsPage', () => {
  it('lists all runs with manifest-backed status', async () => {
    renderPage();
    expect(await screen.findByText('demo')).toBeInTheDocument();
    expect(screen.getByText('e2e')).toBeInTheDocument();
    expect((await screen.findAllByText('COMPLETE')).length).toBeGreaterThan(0);
  });

  it('trigger run posts and toasts, then polls to completion', async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Trigger pipeline run' }));
    expect(await screen.findByText('Run started')).toBeInTheDocument();
    expect(
      await screen.findByText('Run complete — view results', {}, { timeout: 15000 }),
    ).toBeInTheDocument();
  }, 30000);

  it('shows an empty state when no runs exist', async () => {
    server.use(
      http.get('http://127.0.0.1:8080/runs', () =>
        HttpResponse.json({ run_id: '', generated_at: '', runs: [] }),
      ),
    );
    renderPage();
    expect(await screen.findByText('No runs yet')).toBeInTheDocument();
    expect(screen.getByText('Trigger the first run to get started.')).toBeInTheDocument();
  });
});
