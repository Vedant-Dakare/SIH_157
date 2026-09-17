import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { axe } from 'vitest-axe';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import PortfolioPage from '@/pages/PortfolioPage';
import { ToastProvider } from '@/components/ui/toaster';

describe('PortfolioPage accessibility', () => {
  it('has zero axe violations', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={client}>
        <ToastProvider>
          <MemoryRouter initialEntries={['/portfolio?run=demo']}>
            <PortfolioPage />
          </MemoryRouter>
        </ToastProvider>
      </QueryClientProvider>,
    );
    expect(await screen.findByText('Total Entities')).toBeInTheDocument();
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
