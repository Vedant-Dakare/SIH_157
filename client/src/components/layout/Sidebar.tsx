import { NavLink, useSearchParams } from 'react-router-dom';
import {
  Activity,
  FileCheck,
  History,
  LayoutDashboard,
  ListOrdered,
  ScrollText,
  Settings,
  Users,
  X,
} from 'lucide-react';

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { useRuns } from '@/hooks/useRuns';
import { EmblemOfIndia } from '@/components/common/EmblemOfIndia';

export const NAV_ITEMS = [
  { to: '/portfolio', label: 'Overview', icon: LayoutDashboard },
  { to: '/entities', label: 'Case Explorer', icon: Users },
  { to: '/queue', label: 'Attention Queue', icon: ListOrdered },
  { to: '/runs', label: 'Run History', icon: History },
  { to: '/validation', label: 'Validation', icon: FileCheck },
  { to: '/audit', label: 'Audit Trail', icon: ScrollText },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const;

export interface SidebarProps {
  isMobileMenuOpen?: boolean;
  onCloseMobileMenu?: () => void;
}

export function Sidebar({ isMobileMenuOpen, onCloseMobileMenu }: SidebarProps) {
  const [searchParams, setSearchParams] = useSearchParams();

  const runsQuery = useRuns();
  const runs = runsQuery.data?.runs ?? [];
  const selectedRun = searchParams.get('run') ?? runs[0] ?? '';

  function selectRun(runId: string) {
    const next = new URLSearchParams(searchParams);
    next.set('run', runId);
    setSearchParams(next);
  }

  const navContent = (
    <div className="flex h-full flex-col justify-between">
      {/* Branding & Run Selector */}
      <div>
        {/* Government Identity Header */}
        <div className="border-b border-[#D9E2EC] bg-white px-5 pt-4 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-md bg-[#123B5D] text-amber-300 p-1">
              <EmblemOfIndia className="h-9 w-auto text-amber-300" />
            </div>

            <div className="min-w-0 flex-1">
              <div className="text-[10px] font-bold uppercase tracking-wider text-[#52606D]">
                Govt of India
              </div>
              <div className="text-base font-bold tracking-tight text-[#123B5D]">
                SAT-SA Portal
              </div>
              <div className="text-[10px] uppercase tracking-[0.08em] text-[#52606D]">
                NCIIPC Supervision
              </div>
            </div>

            {onCloseMobileMenu ? (
              <button
                type="button"
                onClick={onCloseMobileMenu}
                aria-label="Close navigation"
                className="flex h-8 w-8 items-center justify-center rounded text-slate-500 hover:bg-slate-100 lg:hidden"
              >
                <X className="h-5 w-5" aria-hidden="true" />
              </button>
            ) : null}
          </div>

          {/* Current Run Selector */}
          <div className="mt-5 mb-1.5 flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5 text-[#1F5F8B]" aria-hidden="true" />
            <span className="text-[11px] font-bold uppercase tracking-[0.1em] text-[#52606D]">
              Current Run
            </span>
          </div>

          <Select value={selectedRun} onValueChange={selectRun} disabled={runs.length === 0}>
            <SelectTrigger
              id="run-selector"
              aria-label="Select current run"
              className="h-8.5 w-full border-[#D9E2EC] bg-white text-xs font-medium text-[#1F2933] focus:border-[#1F5F8B] focus:ring-1 focus:ring-[#1F5F8B]"
            >
              <SelectValue placeholder={runsQuery.isLoading ? 'Loading runs…' : 'No runs'} />
            </SelectTrigger>

            <SelectContent className="border-[#D9E2EC] bg-white text-xs">
              {runs.map((runId) => (
                <SelectItem key={runId} value={runId} className="text-xs text-[#1F2933]">
                  {runId}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Navigation items */}
        <nav className="px-3 py-3" aria-label="Portal Navigation">
          <div className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.12em] text-[#52606D]">
            Official Workspace
          </div>

          <ul className="space-y-1">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  aria-label={`Go to ${item.label}`}
                  onClick={onCloseMobileMenu}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-md px-3 py-2 text-xs font-medium transition-colors',
                      'focus:outline-none focus:ring-2 focus:ring-[#1F5F8B]',
                      isActive
                        ? 'border-l-[3px] border-[#123B5D] bg-[#EAF3F8] font-semibold text-[#123B5D]'
                        : 'border-l-[3px] border-transparent text-[#52606D] hover:bg-[#F8FAFC] hover:text-[#1F2933]',
                    )
                  }
                >
                  <item.icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                  <span>{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </div>

      {/* Institutional Security Environment Badge */}
      <div className="border-t border-[#D9E2EC] bg-[#F8FAFC] p-3.5">
        <div className="mb-1.5 flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-600 ring-2 ring-emerald-100" aria-hidden="true" />
          <span className="text-[11px] font-semibold text-[#1F2933]">Air-gapped environment</span>
        </div>

        <p className="text-[10px] leading-4 text-[#52606D]">
          SAT-SA · Human supervisory decision support framework
        </p>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop Persistent Sidebar */}
      <aside
        aria-label="Primary navigation"
        className="fixed bottom-0 left-0 top-[107px] z-30 hidden w-[250px] flex-col border-r border-[#D9E2EC] bg-white lg:flex"
      >
        {navContent}
      </aside>

      {/* Mobile Drawer Navigation */}
      {isMobileMenuOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs transition-opacity"
            onClick={onCloseMobileMenu}
            aria-hidden="true"
          />

          {/* Drawer Panel */}
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Mobile Navigation Menu"
            className="fixed inset-y-0 left-0 w-[280px] bg-white shadow-xl flex flex-col animate-in slide-in-from-left duration-200"
          >
            {navContent}
          </div>
        </div>
      ) : null}
    </>
  );
}