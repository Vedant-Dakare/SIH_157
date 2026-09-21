import * as React from 'react';
import { Menu, Search, X } from 'lucide-react';
import { EmblemOfIndia } from '@/components/common/EmblemOfIndia';

export interface HeaderProps {
  onToggleMobileMenu?: () => void;
  isMobileMenuOpen?: boolean;
}

export function Header({ onToggleMobileMenu, isMobileMenuOpen }: HeaderProps) {
  const [activeScale, setActiveScale] = React.useState<'sm' | 'md' | 'lg'>('md');

  function setFontScale(scale: 'sm' | 'md' | 'lg') {
    setActiveScale(scale);
    if (typeof document !== 'undefined') {
      document.documentElement.classList.remove('font-scale-sm', 'font-scale-md', 'font-scale-lg');
      document.documentElement.classList.add(`font-scale-${scale}`);
    }
  }

  return (
    <header className="fixed left-0 right-0 top-0 z-40 bg-white shadow-xs border-b border-[#D9E2EC]">
      {/* Tricolour Accent Line */}
      <div className="tricolour-line w-full" aria-hidden="true" />

      {/* Top utility bar - Official Indian Government Standard */}
      <div className="flex h-8 items-center justify-between bg-[#123B5D] px-4 text-[11px] text-slate-100 sm:px-6">
        <div className="flex items-center gap-2">
          <span className="font-semibold tracking-wide text-white">भारत सरकार</span>
          <span className="text-blue-300">|</span>
          <span className="hidden tracking-wide text-blue-100 sm:inline">Government of India</span>
        </div>

        <div className="flex items-center gap-3 sm:gap-4">
          <a
            href="#main-content"
            className="text-blue-100 hover:text-white hover:underline focus:outline-none focus:ring-1 focus:ring-white"
          >
            Skip to main content
          </a>
          <span className="text-blue-300" aria-hidden="true">|</span>
          <span className="hidden sm:inline text-blue-200">Accessibility</span>
          <div className="flex items-center gap-1 font-mono text-[11px]" aria-label="Font size controls">
            <button
              type="button"
              onClick={() => setFontScale('sm')}
              className={`px-1 rounded hover:bg-white/10 ${activeScale === 'sm' ? 'font-bold text-white underline' : 'text-blue-200'}`}
              aria-label="Decrease font size"
            >
              A-
            </button>
            <button
              type="button"
              onClick={() => setFontScale('md')}
              className={`px-1 rounded hover:bg-white/10 ${activeScale === 'md' ? 'font-bold text-white underline' : 'text-blue-200'}`}
              aria-label="Normal font size"
            >
              A
            </button>
            <button
              type="button"
              onClick={() => setFontScale('lg')}
              className={`px-1 rounded hover:bg-white/10 ${activeScale === 'lg' ? 'font-bold text-white underline' : 'text-blue-200'}`}
              aria-label="Increase font size"
            >
              A+
            </button>
          </div>
          <span className="text-blue-300" aria-hidden="true">|</span>
          <span className="font-medium text-white">English</span>
          <span className="hidden sm:inline text-blue-300" aria-hidden="true">|</span>
          <span className="hidden sm:inline text-blue-200">Help</span>
        </div>
      </div>

      {/* Main Official Header Bar */}
      <div className="flex h-[72px] items-center justify-between px-4 sm:px-6 lg:ml-[250px]">
        {/* Mobile menu button and Portal Title for Small Screens */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onToggleMobileMenu}
            aria-label={isMobileMenuOpen ? 'Close main navigation' : 'Open main navigation'}
            aria-expanded={isMobileMenuOpen}
            className="flex h-9 w-9 items-center justify-center rounded-md border border-[#D9E2EC] bg-white text-[#123B5D] hover:bg-[#EAF3F8] lg:hidden focus:outline-none focus:ring-2 focus:ring-[#1F5F8B]"
          >
            {isMobileMenuOpen ? (
              <X className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Menu className="h-5 w-5" aria-hidden="true" />
            )}
          </button>

          <div className="flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-[#123B5D] text-white p-1">
              <EmblemOfIndia className="h-8 w-auto text-amber-300" />
            </div>
            <div>
              <div className="text-sm font-bold tracking-tight text-[#123B5D]">SAT-SA</div>
              <div className="text-[10px] uppercase tracking-wider text-[#52606D]">Govt of India · NCIIPC</div>
            </div>
          </div>

          <div className="hidden lg:block">
            <div className="text-[10px] font-bold uppercase tracking-wider text-[#52606D]">
              National Cyber Coordination &amp; Supervisory Portal
            </div>
            <div className="text-xs text-[#1F2933]">
              Security Operations Center (SOC) Alert Triage &amp; Supervisory Analytics
            </div>
          </div>
        </div>

        {/* Global Search & System Status */}
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="relative hidden w-[260px] xl:block">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
              aria-hidden="true"
            />
            <input
              type="search"
              aria-label="Search cases or entities"
              placeholder="Search cases or entities"
              className="h-9 w-full rounded-md border border-[#D9E2EC] bg-[#F8FAFC] pl-9 pr-3 text-xs text-[#1F2933] outline-none placeholder:text-slate-400 transition-colors focus:border-[#1F5F8B] focus:bg-white focus:ring-2 focus:ring-[#EAF3F8]"
            />
          </div>

          <div className="flex h-8 items-center gap-2 rounded-md border border-[#D9E2EC] bg-[#F8FAFC] px-2.5 text-xs text-[#1F2933]">
            <span
              className="h-2 w-2 rounded-full bg-emerald-600 ring-2 ring-emerald-100"
              aria-hidden="true"
            />
            <span className="font-medium text-[11px] text-[#1F2933]">System operational</span>
            <span className="hidden sm:inline text-[10px] text-[#52606D] font-mono">· Air-gapped</span>
          </div>
        </div>
      </div>
    </header>
  );
}