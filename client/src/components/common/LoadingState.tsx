import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

export interface LoadingStateProps {
  rows?: number;
  message?: string;
}

/** Skeleton loader matching the page layout. */
export function LoadingState({ rows = 5, message = 'Loading…' }: LoadingStateProps) {
  return (
    <div role="status" aria-live="polite" aria-label={message} className="w-full space-y-3 py-4">
      <span className="sr-only">{message}</span>
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className={cn('h-10 w-full', index === 0 && 'h-6 w-1/3')} />
      ))}
    </div>
  );
}
