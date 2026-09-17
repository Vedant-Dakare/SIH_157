import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { formatScore } from '@/lib/utils';
import type { DomainScore } from '@/types/api';

export interface DomainScorePanelProps {
  domainScores: DomainScore[];
  overallScore: number;
  selectedSignals?: string[] | null;
  onSelectDomain?: (domain: string, memberSignals: string[]) => void;
}

const DOMAIN_DEFINITIONS: Record<string, string> = {
  detection_coverage: 'Telemetry presence across expected sources and assets.',
  investigation_quality: 'Thoroughness of triage notes, reopens and documentation.',
  escalation_integrity: 'Whether critical cases escalate through tiers correctly.',
  operational_discipline: 'Closure hygiene: timing, batching and SLA behaviour.',
  governance: 'Composite patterns indicating metric or compliance gaming.',
  peer_divergence: 'Deviation from the peer cohort on comparable metrics.',
  negative_space: 'Expected-but-absent telemetry, categories and activity.',
};

function barColour(score: number): string {
  if (score >= 75) {
    return 'bg-red-500';
  }
  if (score >= 50) {
    return 'bg-orange-500';
  }
  if (score >= 25) {
    return 'bg-yellow-500';
  }
  return 'bg-green-500';
}

/** Seven domain bars plus a CSS overall gauge. Click a domain to filter findings. */
export function DomainScorePanel({ domainScores, overallScore, selectedSignals, onSelectDomain }: DomainScorePanelProps) {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const fraction = Math.max(0, Math.min(100, overallScore)) / 100;
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <div
          role="img"
          aria-label={`Overall score ${formatScore(overallScore)} out of 100`}
          className="relative h-28 w-28 shrink-0"
        >
          <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
            <circle cx="50" cy="50" r={radius} fill="none" stroke="#1e293b" strokeWidth="10" />
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke={overallScore >= 75 ? '#ef4444' : overallScore >= 50 ? '#f97316' : overallScore >= 25 ? '#eab308' : '#22c55e'}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={`${(fraction * circumference).toFixed(1)} ${circumference.toFixed(1)}`}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-bold text-slate-50">{formatScore(overallScore)}</span>
            <span className="text-[11px] text-slate-500">overall</span>
          </div>
        </div>
        <p className="text-sm text-slate-400">
          Transparent composite over seven domains. Select a domain to filter the findings table.
        </p>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {domainScores.map((domain) => {
          const active = selectedSignals !== undefined && selectedSignals !== null;
          return (
            <TooltipProvider key={domain.domain} delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={() => onSelectDomain?.(domain.domain, domain.signals)}
                    aria-label={`Filter findings to domain ${domain.domain}`}
                    aria-pressed={active}
                    className="rounded-md border border-slate-700 bg-slate-900 p-3 text-left transition-colors hover:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-400"
                  >
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium text-slate-50">{domain.domain}</span>
                      <span className="flex items-center gap-2 text-xs text-slate-400">
                        <span className="rounded-sm bg-slate-800 px-1.5 py-0.5">
                          {domain.signals.length} signal{domain.signals.length === 1 ? '' : 's'}
                        </span>
                        <strong className="text-slate-50">{formatScore(domain.score)}</strong>
                      </span>
                    </div>
                    <div
                      role="progressbar"
                      aria-valuenow={Math.round(domain.score)}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${domain.domain} score`}
                      className="h-2 w-full overflow-hidden rounded-full bg-slate-800"
                    >
                      <div className={`h-full ${barColour(domain.score)}`} style={{ width: `${Math.max(0, Math.min(100, domain.score))}%` }} />
                    </div>
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{DOMAIN_DEFINITIONS[domain.domain] ?? 'Supervisory risk domain.'}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          );
        })}
      </div>
    </div>
  );
}
