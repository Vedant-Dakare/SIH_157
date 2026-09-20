import { Outlet, useLocation } from 'react-router-dom';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { TooltipProvider } from '@/components/ui/tooltip';

export function AppShell() {
  const location = useLocation();

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[#f7f9fc] text-slate-900">

        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-white focus:px-4 focus:py-3 focus:text-slate-900 focus:shadow-lg"
        >
          Skip to main content
        </a>

        <Sidebar />
        <Header />

        {/* FULL-WIDTH HEADER DIVIDER */}
        <div
  className="pointer-events-none fixed left-0 right-0 top-[110px] z-[60] h-px bg-slate-200"
  aria-hidden="true"
/>

        <main
  id="main-content"
  className="min-h-screen pt-[120px] lg:pl-[248px]"
>
          <div className="mx-auto w-full max-w-[1680px] px-4 pb-10 sm:px-6 lg:px-8">
            <ErrorBoundary key={location.pathname} label="Page">
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}