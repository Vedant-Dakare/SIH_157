import type { ReactNode } from 'react';
import { Inbox } from 'lucide-react';

export interface EmptyStateProps {
  title: string;
  description: string;
  action?: ReactNode;
}

/** Centered empty state with icon, message and optional action. */
export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex w-full flex-col items-center justify-center gap-2 py-12 text-center">
      <Inbox className="h-8 w-8 text-slate-400" aria-hidden="true" />
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="max-w-sm text-sm text-slate-500">{description}</p>
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
