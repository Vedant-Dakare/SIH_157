import * as React from 'react';

import { Toast, type ToastProps } from '@/components/ui/toast';
import { cn } from '@/lib/utils';

interface ToastInput {
  title?: string;
  description?: string;
  variant?: ToastProps['variant'];
}

interface ToastContextValue {
  toasts: ToastProps[];
  toast: (input: ToastInput) => string;
  dismiss: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

let toastCounter = 0;

/** Toast store provider. Local-only, no external dependencies. */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastProps[]>([]);

  const dismiss = React.useCallback((id: string) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const toast = React.useCallback(
    (input: ToastInput) => {
      toastCounter += 1;
      const id = `toast-${toastCounter}`;
      setToasts((current) => [...current, { ...input, id, onDismiss: dismiss }]);
      return id;
    },
    [dismiss],
  );

  const value = React.useMemo(() => ({ toasts, toast, dismiss }), [toasts, toast, dismiss]);
  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

/** Access the toast store. Falls back to a no-op toaster if outside ToastProvider. */
export function useToast(): ToastContextValue {
  const context = React.useContext(ToastContext);
  if (context) return context;
  const fallback: ToastContextValue = {
    toasts: [],
    toast: () => '',
    dismiss: () => {},
  };
  return fallback;
}

export function Toaster({ className }: { className?: string }) {
  return (
    <ToastProvider>
      <ToastViewport className={className} />
    </ToastProvider>
  );
}

export function ToastViewport({ className }: { className?: string }) {
  const { toasts, dismiss } = useToast();
  return (
    <div
      aria-live="polite"
      className={cn(
        'pointer-events-none fixed bottom-0 right-0 z-[100] flex w-full max-w-sm flex-col gap-2 p-4',
        className,
      )}
    >
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} onDismiss={dismiss} />
      ))}
    </div>
  );
}
