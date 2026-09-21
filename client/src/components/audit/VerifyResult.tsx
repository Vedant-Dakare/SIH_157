import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  XCircle,
} from 'lucide-react';

import { HashDisplay } from '@/components/common/HashDisplay';
import { Button } from '@/components/ui/button';

export interface VerifyState {
  valid: boolean;
  entry_count: number;
  merkle_root: string;
  first_broken_seq?: number | null;
}

export interface VerifyResultProps {
  result: VerifyState | null;
  isLoading: boolean;
  onExportBroken?: () => void;
}

/** Chain verification outcome: intact, broken, loading, or not-yet-run. */
export function VerifyResult({
  result,
  isLoading,
  onExportBroken,
}: VerifyResultProps) {
  if (isLoading) {
    return (
      <div
        role="status"
        aria-label="Verification in progress"
        className="flex items-center gap-3 py-6"
      >
        <Loader2
          className="h-8 w-8 animate-spin text-[#2563A8]"
          aria-hidden="true"
        />

        <p className="text-sm font-medium text-slate-700">
          Verifying audit chain…
        </p>
      </div>
    );
  }

  if (result === null) {
    return (
      <p className="rounded-md border border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-700">
        Run verification to check the audit chain.
      </p>
    );
  }

  if (result.valid) {
    return (
      <div
        className="space-y-2 rounded-md border border-[#D9E2EC] bg-[#EAF3F8] px-5 py-4 shadow-xs"
        aria-label="Chain intact"
      >
        <p className="flex items-center gap-2 text-lg font-bold text-[#123B5D]">
          <CheckCircle2
            className="h-6 w-6 text-[#123B5D]"
            aria-hidden="true"
          />

          <span>Audit chain intact</span>
        </p>

        <p className="text-sm font-medium text-[#1F2933]">
          {result.entry_count} entries verified.
        </p>

        <HashDisplay
          hash={result.merkle_root}
          label="merkle_root"
        />
      </div>
    );
  }

  return (
    <div
      className="space-y-3 rounded-md border border-red-200 bg-red-50 px-4 py-4"
      aria-label="Chain broken"
    >
      <p className="flex items-center gap-2 text-lg font-bold text-red-800">
        <XCircle
          className="h-6 w-6"
          aria-hidden="true"
        />

        <span>
          Chain broken
          {result.first_broken_seq !==
            undefined &&
          result.first_broken_seq !== null
            ? ` at entry #${result.first_broken_seq}`
            : ''}
        </span>
      </p>

      <p className="flex items-center gap-2 text-sm font-medium text-slate-800">
        <AlertTriangle
          className="h-4 w-4 text-red-700"
          aria-hidden="true"
        />

        <span>
          Entries from the break forward cannot be
          trusted. Export the chain for investigation.
        </span>
      </p>

      {onExportBroken ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onExportBroken}
          aria-label="Export broken chain"
          className="border-red-300 bg-white text-red-800 hover:bg-red-50"
        >
          Export Broken Chain
        </Button>
      ) : null}
    </div>
  );
}