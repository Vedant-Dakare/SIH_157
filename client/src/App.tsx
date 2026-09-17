import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';

import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { Toaster } from '@/components/ui/toaster';
import { router } from '@/router';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000,
      gcTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      refetchOnReconnect: false,
      refetchInterval: false,
      retry: 1,
    },
  },
});

/** Root app: query client, router, toasts. No background refetch (air-gapped). */
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Toaster />
      <ErrorBoundary label="Application">
        <RouterProvider router={router} />
      </ErrorBoundary>
    </QueryClientProvider>
  );
}
