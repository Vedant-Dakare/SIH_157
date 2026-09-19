import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { SignalFamily } from '@/types/api';

export interface SignalBadgeProps {
  signalId: string;
  family: SignalFamily;
  size?: 'sm' | 'md';
}

function familyOf(
  signalId: string,
  fallback: SignalFamily,
): SignalFamily {
  if (signalId.startsWith('EG-')) {
    return 'execution_gap';
  }

  if (signalId.startsWith('NS-')) {
    return 'negative_space';
  }

  if (signalId.startsWith('COMP-')) {
    return 'composite';
  }

  return fallback;
}

const FAMILY_STYLES: Record<
  SignalFamily,
  {
    label: string;
    className: string;
  }
> = {
  execution_gap: {
    label: 'Execution Gap',
    className:
      'border-[#c9bdf2] bg-[#f1edff] text-[#4c3a8a]',
  },

  negative_space: {
    label: 'Negative Space',
    className:
      'border-[#b7dce8] bg-[#eaf7fa] text-[#155e75]',
  },

  composite: {
    label: 'Composite',
    className:
      'border-[#b9d4ea] bg-[#edf5fb] text-[#24577d]',
  },

  peer: {
    label: 'Peer',
    className:
      'border-[#cbd5e1] bg-[#f1f5f9] text-[#334155]',
  },
};

/** Signal badge coloured by family. Shows ID plus short family name. */
export function SignalBadge({
  signalId,
  family,
  size = 'md',
}: SignalBadgeProps) {
  const resolved = familyOf(signalId, family);
  const style = FAMILY_STYLES[resolved];

  return (
    <Badge
      aria-label={`Signal ${signalId}, ${style.label}`}
      className={cn(
        style.className,
        'border font-mono font-medium',
        size === 'sm'
          ? 'text-[11px]'
          : 'text-xs',
      )}
    >
      {signalId} · {style.label}
    </Badge>
  );
}