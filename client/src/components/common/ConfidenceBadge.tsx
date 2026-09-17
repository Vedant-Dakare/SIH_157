import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { CONFIDENCE_STYLES } from '@/lib/constants';
import { cn } from '@/lib/utils';
import type { ConfidenceLevel } from '@/types/api';

export interface ConfidenceBadgeProps {
  confidence: ConfidenceLevel;
  reason?: string;
}

/** Confidence badge. Always visible with a label; reason shown in tooltip. */
export function ConfidenceBadge({ confidence, reason }: ConfidenceBadgeProps) {
  const style = CONFIDENCE_STYLES[confidence];
  const Icon = style.icon;
  return (
    <TooltipProvider delayDuration={0}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span aria-label={`Confidence ${confidence}`}>
            <Badge className={cn(style.bg, style.text, 'border border-slate-700')}>
              <Icon className="h-3 w-3" aria-hidden="true" />
              {confidence}
            </Badge>
          </span>
        </TooltipTrigger>
        <TooltipContent>
          <p>{reason ?? `Model confidence: ${confidence}`}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
