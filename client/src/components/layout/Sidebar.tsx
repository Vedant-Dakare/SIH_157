import { NavLink, useSearchParams } from 'react-router-dom';
import { Activity, FileCheck, History, LayoutDashboard, ListOrdered, ScrollText, Settings, Users } from 'lucide-react';

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { useRuns } from '@/hooks/useRuns';

const NAV_ITEMS = [
  { to: '/portfolio', label: 'Portfolio', icon: LayoutDashboard },
  { to: '/entities', label: 'Entities', icon: Users },
  { to: '/queue', label: 'Review Queue', icon: ListOrdered },
  { to: '/runs', label: 'Runs', icon: History },
  { to: '/validation', label: 'Validation', icon: FileCheck },
  { to: '/audit', label: 'Audit', icon: ScrollText },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const;

/** Fixed 240px sidebar: nav, active states, run selector, wordmark. */
export function Sidebar() {
  const [searchParams, setSearchParams] = useSearchParams();
  const runsQuery = useRuns();
  const runs = runsQuery.data?.runs ?? [];
  const selectedRun = searchParams.get('run') ?? runs[0] ?? '';

  function selectRun(runId: string) {
    const next = new URLSearchParams(searchParams);
    next.set('run', runId);
    setSearchParams(next);
  }

  return (
    <nav aria-label="Primary navigation" className="fixed left-0 top-0 flex h-screen w-60 flex-col border-r border-slate-700 bg-slate-900">
      <div className="flex h-14 items-center gap-2 border-b border-slate-700 px-4">
        <Activity className="h-5 w-5 text-slate-50" aria-hidden="true" />
        <span className="text-sm font-bold tracking-wide text-slate-50">SAT-SA</span>
      </div>
      <div className="border-b border-slate-700 p-3">
        <label htmlFor="run-selector" className="mb-1 block text-xs text-slate-500">
          Current run
        </label>
        <Select value={selectedRun} onValueChange={selectRun} disabled={runs.length === 0}>
          <SelectTrigger id="run-selector" aria-label="Select current run">
            <SelectValue placeholder={runsQuery.isLoading ? 'Loading runs…' : 'No runs'} />
          </SelectTrigger>
          <SelectContent>
            {runs.map((runId) => (
              <SelectItem key={runId} value={runId}>
                {runId}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <ul className="flex-1 space-y-1 overflow-y-auto p-3">
        {NAV_ITEMS.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              aria-label={`Go to ${item.label}`}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400',
                  isActive ? 'bg-slate-800 text-slate-50' : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-50',
                )
              }
            >
              <item.icon className="h-4 w-4" aria-hidden="true" />
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
      <div className="border-t border-slate-700 p-3 text-xs text-slate-500">Air-gapped · offline build</div>
    </nav>
  );
}
