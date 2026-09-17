import { Badge } from '@/components/ui/badge';
import { SIGNAL_FAMILY_STYLES } from '@/lib/constants';
import { cn } from '@/lib/utils';
import type { SignalFamily } from '@/types/api';

export interface SignalBadgeProps {
  signalId: string;
  family: SignalFamily;
  size?: 'sm' | 'md';
}

function familyOf(signalId: string, fallback: SignalFamily): SignalFamily {
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

/** Signal badge coloured by family. Shows ID plus short family name. */
export function SignalBadge({ signalId, family, size = 'md' }: SignalBadgeProps) {
  const resolved = familyOf(signalId, family);
  const style = SIGNAL_FAMILY_STYLES[resolved];
  return (
    <Badge
      aria-label={`Signal ${signalId}, ${style.label}`}
      className={cn(style.bg, style.text, 'border border-slate-700 font-mono', size === 'sm' ? 'text-[11px]' : 'text-xs')}
    >
      {signalId} · {style.label}
    </Badge>
  );
}
