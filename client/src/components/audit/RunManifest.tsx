import { AlertTriangle, Download } from 'lucide-react';

import { HashDisplay } from '@/components/common/HashDisplay';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toaster';
import { formatDate } from '@/lib/utils';
import type { RunManifest } from '@/types/api';

export interface RunManifestProps {
  manifest: RunManifest;
  runId: string;
  onVerify: () => void;
  verifying?: boolean;
}

/** Full manifest display with verify and JSON export actions. */
export function RunManifest({
  manifest,
  runId,
  onVerify,
  verifying = false,
}: RunManifestProps) {
  const { toast } = useToast();

  function exportJson(): void {
    const blob = new Blob([JSON.stringify(manifest, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${runId}-manifest.json`;
    anchor.click();
    URL.revokeObjectURL(url);

    toast({
      title: 'Manifest exported',
      description: `${runId}-manifest.json downloaded.`,
    });
  }

  return (
    <div className="space-y-4" aria-label={`Run manifest for ${runId}`}>
      <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <div className="rounded-md border border-[#BFDBFE] bg-[#EFF6FF] p-3">
          <dt className="text-xs text-[#5B7595]">run_id</dt>
          <dd className="mono text-[#123D73]">{manifest.run_id}</dd>
        </div>

        <div className="rounded-md border border-[#BFDBFE] bg-[#EFF6FF] p-3">
          <dt className="text-xs text-[#5B7595]">created_at</dt>
          <dd className="text-[#123D73]">
            {formatDate(manifest.created_at)}
          </dd>
        </div>

        <div className="rounded-md border border-[#BFDBFE] bg-[#EFF6FF] p-3">
          <dt className="text-xs text-[#5B7595]">window</dt>
          <dd className="mono text-xs text-[#123D73]">
            {manifest.window_start} .. {manifest.window_end}
          </dd>
        </div>

        <div className="rounded-md border border-[#BFDBFE] bg-[#EFF6FF] p-3">
          <dt className="text-xs text-[#5B7595]">pipeline</dt>
          <dd className="text-[#123D73]">{manifest.signals_version}</dd>
        </div>

        <div className="rounded-md border border-[#BFDBFE] bg-[#EFF6FF] p-3">
          <dt className="text-xs text-[#5B7595]">
            entities / findings / entries
          </dt>
          <dd className="text-[#123D73]">
            {manifest.entity_count} / {manifest.finding_count} /{' '}
            {manifest.entry_count}
          </dd>
        </div>

        <div className="rounded-md border border-[#BFDBFE] bg-[#EFF6FF] p-3">
          <dt className="text-xs text-[#5B7595]">seq range</dt>
          <dd className="text-[#123D73]">
            {manifest.first_seq} … {manifest.last_seq}
          </dd>
        </div>

        <div className="rounded-md border border-[#BFDBFE] bg-[#EFF6FF] p-3">
          <dt className="text-xs text-[#5B7595]">thresholds_hash</dt>
          <dd>
            <HashDisplay hash={manifest.thresholds_hash} />
          </dd>
        </div>

        <div className="rounded-md border border-[#BFDBFE] bg-[#EFF6FF] p-3">
          <dt className="text-xs text-[#5B7595]">hmac_signature</dt>
          <dd>
            <HashDisplay hash={manifest.signature} />
          </dd>
        </div>
      </dl>

      <div className="rounded-md border border-[#BFDBFE] bg-[#E0EEFF] p-3">
        <p className="mb-1 text-xs text-[#5B7595]">merkle_root</p>
        <p className="mono break-all text-base font-bold text-[#123D73]">
          {manifest.merkle_root}
        </p>
      </div>

      {manifest.finding_count === 0 ? (
        <p
          role="note"
          className="flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800"
        >
          <AlertTriangle
            className="h-4 w-4"
            aria-hidden="true"
          />
          This run recorded no findings — verify the input corpora before
          trusting it.
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          onClick={onVerify}
          disabled={verifying}
          aria-label="Verify audit chain"
          className="border-[#123D73] bg-[#123D73] text-white hover:border-[#BFDBFE] hover:bg-blue-100 hover:text-[#123D73]"
        >
          {verifying ? 'Verifying…' : 'Verify'}
        </Button>

        <Button
          type="button"
          variant="outline"
          onClick={exportJson}
          aria-label="Export manifest JSON"
          className="border-[#BFDBFE] bg-[#EFF6FF] text-[#123D73] hover:bg-blue-100 hover:text-[#123D73]"
        >
          <Download
            className="h-3.5 w-3.5"
            aria-hidden="true"
          />
          Export
        </Button>
      </div>
    </div>
  );
}