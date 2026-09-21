import { ShieldAlert } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { BAND_DESCRIPTIONS } from '@/lib/constants';
import { cn } from '@/lib/utils';
import type { RiskBand } from '@/types/api';

export interface RiskBadgeProps {
  band: RiskBand;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

const SIZE_CLASSES: Record<NonNullable<RiskBadgeProps['size']>, string> = {
  sm: 'text-[11px] px-1.5',
  md: 'text-xs px-2',
  lg: 'text-sm px-3 py-1',
};

/**
 * Risk-band badge.
 * Visual styling only; risk-band values and tooltip content remain unchanged.
 */
export function RiskBadge({
  band,
  size = 'md',
  showIcon = false,
}: RiskBadgeProps) {
  const BAND_CLASSES: Record<RiskBand, string> = {
    HIGH:
      'border-red-200 bg-red-50 text-red-500 font-semibold',
    ELEVATED:
      'border-amber-200 bg-amber-50 text-amber-700 font-semibold',
    MODERATE:
      'border-yellow-200 bg-yellow-50 text-yellow-700 font-semibold',
    LOW:
      'border-emerald-200 bg-emerald-50 text-emerald-700 font-semibold',
  };

  return (
    <TooltipProvider delayDuration={0}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span aria-label={`Risk band ${band}`}>
            <Badge
              className={cn(
                BAND_CLASSES[band],
                'border font-semibold',
                SIZE_CLASSES[size],
              )}
            >
              {showIcon ? (
                <ShieldAlert
                  className="h-3 w-3"
                  aria-hidden="true"
                />
              ) : null}

              {band}
            </Badge>
          </span>
        </TooltipTrigger>

        <TooltipContent>
          <p>{BAND_DESCRIPTIONS[band]}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}