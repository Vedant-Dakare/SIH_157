import { NavLink, useSearchParams } from 'react-router-dom';
import {
  Activity,
  FileCheck,
  History,
  LayoutDashboard,
  ListOrdered,
  ScrollText,
  Settings,
  ShieldCheck,
  Users,
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

const NAV_ITEMS = [
  { to: '/portfolio', label: 'Overview', icon: LayoutDashboard },
  { to: '/entities', label: 'Case Explorer', icon: Users },
  { to: '/queue', label: 'Attention Queue', icon: ListOrdered },
  { to: '/runs', label: 'Run History', icon: History },
  { to: '/validation', label: 'Validation', icon: FileCheck },
  { to: '/audit', label: 'Audit Trail', icon: ScrollText },
  { to: '/settings', label: 'Settings', icon: Settings },
] as const;

export function Sidebar() {
  const [searchParams, setSearchParams] = useSearchParams();

  const runsQuery = useRuns();
  const runs = runsQuery.data?.runs ?? [];
  const selectedRun =
    searchParams.get('run') ?? runs[0] ?? '';

  function selectRun(runId: string) {
    const next = new URLSearchParams(searchParams);
    next.set('run', runId);
    setSearchParams(next);
  }

  return (
    <aside
      aria-label="Primary navigation"
      className="fixed bottom-0 left-0 top-8 z-50 hidden w-[248px] flex-col border-r border-slate-200 bg-white lg:flex"
    >
      {/* SAT-SA + Current Run */}
      <div className="border-b border-slate-200 bg-white px-5 pt-7 pb-6">
        {/* SAT-SA */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-[#082b57]">
            <ShieldCheck
              className="h-5 w-5 text-white"
              aria-hidden="true"
            />
          </div>

          <div>
            <div className="text-lg font-bold tracking-tight text-[#102a56]">
              SAT-SA
            </div>

            <div className="text-[10px] uppercase tracking-[0.1em] text-slate-500">
              Supervisory Analytics
            </div>
          </div>
        </div>

        {/* Current Run */}
        <div className="mt-6 mb-2 flex items-center gap-2">
          <Activity
            className="h-4 w-4 text-[#123d73]"
            aria-hidden="true"
          />

          <span className="text-[11px] font-semibold uppercase tracking-[0.1em] text-slate-500">
            Current Run
          </span>
        </div>

        <Select
          value={selectedRun}
          onValueChange={selectRun}
          disabled={runs.length === 0}
        >
          <SelectTrigger
            id="run-selector"
            aria-label="Select current run"
            className="h-9 border-slate-300 bg-white text-xs text-slate-700"
          >
            <SelectValue
              placeholder={
                runsQuery.isLoading
                  ? 'Loading runs…'
                  : 'No runs'
              }
            />
          </SelectTrigger>

          <SelectContent>
            {runs.map((runId) => (
              <SelectItem
                key={runId}
                value={runId}
              >
                {runId}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <div className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">
          Workspace
        </div>

        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                aria-label={`Go to ${item.label}`}
                className={({ isActive }) =>
                  cn(
                    'console-interactive flex items-center gap-3 rounded-md border px-3 py-2.5 text-sm',
                    'focus:outline-none focus:ring-2 focus:ring-blue-200',
                    isActive
                      ? 'border-blue-200 bg-blue-50 font-semibold text-[#123d73]'
                      : 'border-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900',
                  )
                }
              >
                <item.icon
                  className="h-[17px] w-[17px] shrink-0"
                  aria-hidden="true"
                />

                <span>{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Environment */}
      <div className="border-t border-slate-200 bg-slate-50 p-4">
        <div className="mb-2 flex items-center gap-2">
          <span
            className="h-2 w-2 rounded-full bg-emerald-500"
            aria-hidden="true"
          />

          <span className="text-[11px] font-medium text-slate-600">
            Air-gapped environment
          </span>
        </div>

        <p className="text-[10px] leading-4 text-slate-400">
          SAT-SA · Supervisory decision support
        </p>
      </div>
    </aside>
  );
}