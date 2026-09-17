import { Outlet, useLocation } from 'react-router-dom';

import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { TooltipProvider } from '@/components/ui/tooltip';

/** App shell: 240px sidebar + 56px header + scrollable main column. */
export function AppShell() {
  const location = useLocation();
  return (
    <TooltipProvider>
      <div className="min-h-screen bg-slate-950 text-slate-50">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-[100] focus:rounded-sm focus:bg-slate-100 focus:px-3 focus:py-2 focus:text-slate-950"
        >
          Skip to main content
        </a>
        <Sidebar />
        <Header />
        <main id="main-content" className="ml-60 mt-14 flex min-h-[calc(100vh-3.5rem)] justify-center">
          <div className="w-full max-w-screen-2xl flex-1 px-6 py-6">
            <ErrorBoundary key={location.pathname} label="Page">
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}
