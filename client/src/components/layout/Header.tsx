import { useLocation, useSearchParams } from 'react-router-dom';
import { Play } from 'lucide-react';

import { HashDisplay } from '@/components/common/HashDisplay';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toaster';
import { useHealth } from '@/hooks/useRuns';
import { triggerRun } from '@/lib/api';
import { formatDate } from '@/lib/utils';

const TITLES: Record<string, string> = {
  '/portfolio': 'Portfolio Dashboard',
  '/entities': 'Entities',
  '/queue': 'Review Queue',
  '/runs': 'Run History',
  '/validation': 'Validation Report',
  '/audit': 'Audit & Ledger',
  '/settings': 'Settings',
};

function titleFor(pathname: string): string {
  if (pathname.startsWith('/findings/')) {
    return 'Finding Detail';
  }
  if (pathname.startsWith('/entities/')) {
    return 'Entity Detail';
  }
  if (pathname.startsWith('/audit/')) {
    return 'Run Manifest';
  }
  if (pathname.startsWith('/portfolio/')) {
    return 'Portfolio Dashboard';
  }
  return TITLES[pathname] ?? 'SAT-SA';
}

/** Fixed 56px header: title, run badge, health dot, trigger-run button. */
export function Header() {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const healthQuery = useHealth();
  const { toast } = useToast();
  const runId = searchParams.get('run') ?? '';

  async function onTrigger(): Promise<void> {
    try {
      const result = await triggerRun();
      toast({ title: 'Pipeline run started', description: `Run ${result.run_id} queued.` });
    } catch (error) {
      toast({
        title: 'Failed to trigger run',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  }

  const healthy = healthQuery.data?.status === 'ok';

  return (
    <header className="fixed left-60 right-0 top-0 z-40 flex h-14 items-center justify-between gap-4 border-b border-slate-700 bg-slate-900 px-6">
      <h1 className="text-sm font-semibold text-slate-50">{titleFor(location.pathname)}</h1>
      <div className="flex items-center gap-3">
        {runId ? (
          <span className="flex items-center gap-2 text-xs text-slate-400" aria-label={`Current run ${runId}`}>
            <HashDisplay hash={runId} chars={12} label="run" />
            {healthQuery.data ? <span>{formatDate(healthQuery.data.generated_at)}</span> : null}
          </span>
        ) : null}
        <span
          role="status"
          aria-label={healthy ? 'Pipeline reachable' : 'Pipeline unreachable'}
          title={healthy ? 'Pipeline reachable' : 'Pipeline unreachable'}
          className={`h-2.5 w-2.5 rounded-full ${healthy ? 'bg-green-500' : 'bg-red-500'}`}
        />
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => void onTrigger()}
          aria-label="Trigger pipeline run"
        >
          <Play className="h-3.5 w-3.5" aria-hidden="true" />
          Run
        </Button>
      </div>
    </header>
  );
}
