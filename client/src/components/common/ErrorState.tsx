import { AlertTriangle } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

export interface ErrorStateProps {
  error: Error | null;
  retry?: () => void;
  message?: string;
}

/** Full-panel error display with icon, message and retry action. */
export function ErrorState({ error, retry, message }: ErrorStateProps) {
  const text = message ?? error?.message ?? 'Something went wrong.';
  return (
    <div role="alert" aria-live="assertive" className="flex w-full justify-center py-12">
      <div className="w-full max-w-md">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" aria-hidden="true" />
          <AlertTitle>Request failed</AlertTitle>
          <AlertDescription>{text}</AlertDescription>
        </Alert>
        {retry ? (
          <Button type="button" onClick={retry} variant="outline" className="mt-4" aria-label="Retry request">
            Retry
          </Button>
        ) : null}
      </div>
    </div>
  );
}
