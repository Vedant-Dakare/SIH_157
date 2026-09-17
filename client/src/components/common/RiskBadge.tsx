import { ShieldAlert } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { BAND_DESCRIPTIONS, RISK_BAND_STYLES } from '@/lib/constants';
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

/** Coloured risk-band badge with an explanatory tooltip. Always labelled. */
export function RiskBadge({ band, size = 'md', showIcon = false }: RiskBadgeProps) {
  const style = RISK_BAND_STYLES[band];
  return (
    <TooltipProvider delayDuration={0}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span aria-label={`Risk band ${band}`}>
            <Badge className={cn(style.bg, style.text, `border ${style.border}`, SIZE_CLASSES[size])}>
              {showIcon ? <ShieldAlert className="h-3 w-3" aria-hidden="true" /> : null}
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
