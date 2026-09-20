import * as React from 'react';
import { Check, Copy } from 'lucide-react';

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { truncateHash } from '@/lib/utils';

export interface HashDisplayProps {
  hash: string;
  chars?: number;
  label?: string;
}

/** Truncated monospace hash with copy button and full-hash tooltip. */
export function HashDisplay({ hash, chars = 8, label }: HashDisplayProps) {
  const [copied, setCopied] = React.useState(false);

  async function copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(hash);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <span className="inline-flex items-center gap-1.5">
      {label ? <span className="text-xs text-slate-500">{label}</span> : null}
      <TooltipProvider delayDuration={0}>
        <Tooltip>
          <TooltipTrigger asChild>
            <code aria-label={label ? `${label} ${hash}` : `Hash ${hash}`} className="mono rounded-sm border border-slate-200 bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">
              {truncateHash(hash, chars)}
            </code>
          </TooltipTrigger>
          <TooltipContent>
            <p className="mono break-all">{hash}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
      <button
        type="button"
        onClick={() => void copy()}
        aria-label={copied ? 'Copied' : `Copy ${label ?? 'hash'} to clipboard`}
        className="rounded-sm p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-200"
      >
        {copied ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : <Copy className="h-3.5 w-3.5" aria-hidden="true" />}
      </button>
    </span>
  );
}
