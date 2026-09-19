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
      'border-[#123d73] bg-[#123d73] text-white',
    ELEVATED:
      'border-[#2563a8] bg-[#e8f1fa] text-[#1d5b91]',
    MODERATE:
      'border-[#6baed6] bg-[#edf6fb] text-[#256b99]',
    LOW:
      'border-[#b8d9eb] bg-[#f1f8fc] text-[#39799e]',
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