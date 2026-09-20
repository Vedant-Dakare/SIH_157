import * as React from 'react';
import { Check, Copy } from 'lucide-react';

export interface SampleAlertListProps {
  sampleAlertIds: string[];
  sampleCaseIds: string[];
  signalId: string;
}

/** Expandable sample-ID panel telling the analyst what to open first. */
export function SampleAlertList({
  sampleAlertIds,
  sampleCaseIds,
  signalId,
}: SampleAlertListProps) {
  const [open, setOpen] = React.useState(false);
  const [copied, setCopied] = React.useState(false);

  async function copyAll(): Promise<void> {
    try {
      await navigator.clipboard.writeText(
        [...sampleAlertIds, ...sampleCaseIds].join('\n'),
      );
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  if (
    sampleAlertIds.length === 0 &&
    sampleCaseIds.length === 0
  ) {
    return (
      <p className="text-xs text-slate-500">
        No sample records for this item.
      </p>
    );
  }

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((previous) => !previous)}
        aria-expanded={open}
        aria-label={`${open ? 'Hide' : 'Show'} sample records for ${signalId}`}
        className="rounded-sm text-xs font-medium text-[#2563a8] underline underline-offset-4 transition-colors hover:bg-blue-50 hover:text-[#123d73] focus:outline-none focus:ring-2 focus:ring-blue-200"
      >
        {open
          ? 'Hide sample records'
          : `Show sample records (${sampleAlertIds.length + sampleCaseIds.length})`}
      </button>

      {open ? (
        <div className="mt-2 rounded-md border border-slate-200 bg-slate-50 p-3">
          <p className="mb-2 text-xs text-slate-600">
            Open these records first when reviewing{' '}
            <span className="font-medium text-slate-800">
              {signalId || 'this finding'}
            </span>
            .
          </p>

          <div className="flex flex-wrap gap-1.5">
            {sampleAlertIds.map((id) => (
              <code
                key={`a-${id}`}
                className="mono rounded-sm border border-slate-200 bg-white px-1.5 py-0.5 text-xs text-slate-800"
              >
                {id}
              </code>
            ))}

            {sampleCaseIds.map((id) => (
              <code
                key={`c-${id}`}
                className="mono rounded-sm border border-blue-100 bg-blue-50 px-1.5 py-0.5 text-xs text-[#2563a8]"
              >
                {id}
              </code>
            ))}
          </div>

          <button
            type="button"
            onClick={() => void copyAll()}
            aria-label={
              copied
                ? 'Copied sample IDs'
                : 'Copy all sample IDs to clipboard'
            }
            className="mt-2 inline-flex items-center gap-1 rounded-sm px-2 py-1 text-xs font-medium text-slate-600 transition-colors hover:bg-blue-50 hover:text-[#123d73] focus:outline-none focus:ring-2 focus:ring-blue-200"
          >
            {copied ? (
              <Check
                className="h-3.5 w-3.5"
                aria-hidden="true"
              />
            ) : (
              <Copy
                className="h-3.5 w-3.5"
                aria-hidden="true"
              />
            )}

            {copied ? 'Copied' : 'Copy all'}
          </button>
        </div>
      ) : null}
    </div>
  );
}