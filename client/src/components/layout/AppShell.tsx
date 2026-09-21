import * as React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { Header } from '@/components/layout/Header';
import { Sidebar } from '@/components/layout/Sidebar';
import { TooltipProvider } from '@/components/ui/tooltip';

export function AppShell() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  // Close mobile navigation drawer on route change
  React.useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[#F8FAFC] text-[#1F2933]">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-white focus:px-4 focus:py-3 focus:text-[#123B5D] focus:shadow-lg focus:ring-2 focus:ring-[#1F5F8B]"
        >
          Skip to main content
        </a>

        <Header
          isMobileMenuOpen={mobileMenuOpen}
          onToggleMobileMenu={() => setMobileMenuOpen((prev) => !prev)}
        />
        <Sidebar
          isMobileMenuOpen={mobileMenuOpen}
          onCloseMobileMenu={() => setMobileMenuOpen(false)}
        />

        {/* FULL-WIDTH HEADER DIVIDER */}
        <div
          className="pointer-events-none fixed left-0 right-0 top-[107px] z-[35] h-px bg-[#D9E2EC]"
          aria-hidden="true"
        />

        <main
          id="main-content"
          className="min-h-screen pt-[124px] lg:pl-[250px]"
        >
          <div className="mx-auto w-full max-w-[1680px] px-4 pb-12 sm:px-6 lg:px-8">
            <ErrorBoundary key={location.pathname} label="Page">
              <Outlet />
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}