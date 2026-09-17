import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { X } from 'lucide-react';

import { cn } from '@/lib/utils';

const toastVariants = cva(
  'group pointer-events-auto relative flex w-full items-center justify-between gap-2 overflow-hidden rounded-md border border-slate-700 bg-slate-900 p-4 pr-8 text-slate-50 shadow-lg',
  {
    variants: {
      variant: {
        default: 'border-slate-700 bg-slate-900',
        destructive: 'border-red-500 bg-red-950 text-red-500',
      },
    },
    defaultVariants: { variant: 'default' },
  },
);

export interface ToastProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof toastVariants> {
  id: string;
  title?: string;
  description?: string;
  onDismiss?: (id: string) => void;
}

const Toast = React.forwardRef<HTMLDivElement, ToastProps>(
  ({ id, title, description, variant, onDismiss, className, ...props }, ref) => (
    <div ref={ref} role="status" className={cn(toastVariants({ variant }), className)} {...props}>
      <div className="grid gap-1">
        {title ? <div className="text-sm font-semibold">{title}</div> : null}
        {description ? <div className="text-sm text-slate-400">{description}</div> : null}
      </div>
      <button
        type="button"
        aria-label="Dismiss notification"
        onClick={() => onDismiss?.(id)}
        className="absolute right-2 top-2 rounded-sm text-slate-400 opacity-70 transition-opacity hover:text-slate-50 hover:opacity-100 focus:outline-none"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  ),
);
Toast.displayName = 'Toast';

export { Toast, toastVariants };
export type { ToastProps as ToastProperties };
