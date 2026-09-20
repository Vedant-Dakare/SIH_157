import { Badge } from '@/components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { ConfidenceLevel } from '@/types/api';

export interface ConfidenceBadgeProps {
  confidence: ConfidenceLevel;
  reason?: string;
}

const CONFIDENCE_CLASSES: Record<ConfidenceLevel, string> = {
  HIGH:
    'border-[#123D73] bg-[#123D73] text-white',

  MEDIUM:
    'border-[#2F6FA3] bg-[#2F6FA3] text-white',

  LOW:
    'border-[#8FC4E3] bg-[#E8F4FA] text-[#256B99]',
};

/** Confidence badge. Always visible with a label; reason shown in tooltip. */
export function ConfidenceBadge({
  confidence,
  reason,
}: ConfidenceBadgeProps) {
  const style = CONFIDENCE_CLASSES[confidence];

  return (
    <TooltipProvider delayDuration={0}>
      <Tooltip>
        <TooltipTrigger asChild>
          <span aria-label={`Confidence ${confidence}`}>
            <Badge
              className={cn(
                style,
                'border font-semibold',
              )}
            >
              {confidence}
            </Badge>
          </span>
        </TooltipTrigger>

        <TooltipContent>
          <p>
            {reason ?? `Model confidence: ${confidence}`}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}