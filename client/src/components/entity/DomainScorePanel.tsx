import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { formatScore } from '@/lib/utils';
import type { DomainScore } from '@/types/api';

export interface DomainScorePanelProps {
  domainScores: DomainScore[];
  overallScore: number;
  selectedSignals?: string[] | null;
  onSelectDomain?: (
    domain: string,
    memberSignals: string[],
  ) => void;
}

const DOMAIN_DEFINITIONS: Record<string, string> = {
  detection_coverage:
    'Telemetry presence across expected sources and assets.',
  investigation_quality:
    'Thoroughness of triage notes, reopens and documentation.',
  escalation_integrity:
    'Whether critical cases escalate through tiers correctly.',
  operational_discipline:
    'Closure hygiene: timing, batching and SLA behaviour.',
  governance:
    'Composite patterns indicating metric or compliance gaming.',
  peer_divergence:
    'Deviation from the peer cohort on comparable metrics.',
  negative_space:
    'Expected-but-absent telemetry, categories and activity.',
};

function barColour(score: number): string {
  if (score >= 75) {
    return 'bg-[#123D73]';
  }

  if (score >= 50) {
    return 'bg-[#2563A8]';
  }

  if (score >= 25) {
    return 'bg-[#5B9BC4]';
  }

  return 'bg-[#9CCBE3]';
}

/** Seven domain bars plus a CSS overall gauge. Click a domain to filter findings. */
export function DomainScorePanel({
  domainScores,
  overallScore,
  selectedSignals,
  onSelectDomain,
}: DomainScorePanelProps) {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;

  const fraction =
    Math.max(0, Math.min(100, overallScore)) / 100;

  return (
    <div className="space-y-4">
      {/* Overall score */}
      <div className="flex items-center gap-4">
        <div
          role="img"
          aria-label={`Overall score ${formatScore(
            overallScore,
          )} out of 100`}
          className="relative h-28 w-28 shrink-0"
        >
          <svg
            viewBox="0 0 100 100"
            className="h-full w-full -rotate-90"
          >
            {/* Track */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke="#E2E8F0"
              strokeWidth="10"
            />

            {/* Score */}
            <circle
              cx="50"
              cy="50"
              r={radius}
              fill="none"
              stroke="#2563A8"
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={`${(
                fraction * circumference
              ).toFixed(1)} ${circumference.toFixed(1)}`}
            />
          </svg>

          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-bold text-[#123D73]">
              {formatScore(overallScore)}
            </span>

            <span className="text-[11px] font-medium text-slate-600">
              overall
            </span>
          </div>
        </div>

        <p className="text-sm leading-5 text-slate-700">
          Transparent composite over seven domains.
          Select a domain to filter the findings table.
        </p>
      </div>

      {/* Domain cards */}
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {domainScores.map((domain) => {
          const active =
            selectedSignals !== undefined &&
            selectedSignals !== null;

          return (
            <TooltipProvider
              key={domain.domain}
              delayDuration={0}
            >
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    onClick={() =>
                      onSelectDomain?.(
                        domain.domain,
                        domain.signals,
                      )
                    }
                    aria-label={`Filter findings to domain ${domain.domain}`}
                    aria-pressed={active}
                    className={`rounded-md border p-3 text-left transition-colors focus:outline-none focus:ring-2 focus:ring-blue-300 ${
                      active
                        ? 'border-blue-300 bg-blue-50'
                        : 'border-slate-200 bg-white hover:border-blue-200 hover:bg-blue-50/40'
                    }`}
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-semibold text-slate-900">
                        {domain.domain}
                      </span>

                      <span className="flex items-center gap-2 text-xs">
                        <span className="rounded-sm border border-slate-200 bg-slate-50 px-1.5 py-0.5 font-medium text-slate-700">
                          {domain.signals.length}{' '}
                          signal
                          {domain.signals.length === 1
                            ? ''
                            : 's'}
                        </span>

                        <strong className="font-bold text-[#123D73]">
                          {formatScore(domain.score)}
                        </strong>
                      </span>
                    </div>

                    <div
                      role="progressbar"
                      aria-valuenow={Math.round(
                        domain.score,
                      )}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label={`${domain.domain} score`}
                      className="h-2 w-full overflow-hidden rounded-full bg-slate-100"
                    >
                      <div
                        className={`h-full transition-all ${barColour(
                          domain.score,
                        )}`}
                        style={{
                          width: `${Math.max(
                            0,
                            Math.min(
                              100,
                              domain.score,
                            ),
                          )}%`,
                        }}
                      />
                    </div>
                  </button>
                </TooltipTrigger>

                <TooltipContent>
                  <p>
                    {DOMAIN_DEFINITIONS[
                      domain.domain
                    ] ??
                      'Supervisory risk domain.'}
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          );
        })}
      </div>
    </div>
  );
}