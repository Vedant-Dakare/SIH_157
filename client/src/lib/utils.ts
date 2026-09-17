import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/** Merge Tailwind class lists, resolving conflicts. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format ISO timestamp as "14 Jun 2024 09:32 UTC". Invalid input → "—". */
export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }
  const months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ];
  const day = String(date.getUTCDate()).padStart(2, '0');
  const month = months[date.getUTCMonth()];
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  return `${day} ${month} ${date.getUTCFullYear()} ${hours}:${minutes} UTC`;
}

/** Format seconds as "2h 34m", "5m 07s" or "47s". Non-finite → "—". */
export function formatDuration(totalSeconds: number | null | undefined): string {
  if (totalSeconds === null || totalSeconds === undefined || !Number.isFinite(totalSeconds)) {
    return '—';
  }
  const total = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const seconds = total % 60;
  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${String(seconds).padStart(2, '0')}s`;
  }
  return `${seconds}s`;
}

/** Format a score with one decimal place. Non-finite → "—". */
export function formatScore(score: number | null | undefined): string {
  if (score === null || score === undefined || !Number.isFinite(score)) {
    return '—';
  }
  return score.toFixed(1);
}

/** Truncate a hash with an ellipsis. Empty input → "—". */
export function truncateHash(hash: string | null | undefined, chars = 8): string {
  if (!hash) {
    return '—';
  }
  if (hash.length <= chars) {
    return hash;
  }
  return `${hash.slice(0, chars)}…`;
}

/** Format a ratio as "34.7%". Non-finite → "—". */
export function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return '—';
  }
  return `${(value * 100).toFixed(1)}%`;
}

/** Human label for a signal family id. Unknown ids pass through. */
export function signalFamilyLabel(family: string | null | undefined): string {
  switch (family) {
    case 'execution_gap':
      return 'Execution Gap';
    case 'negative_space':
      return 'Negative Space';
    case 'peer':
      return 'Peer';
    case 'anomaly':
      return 'Anomaly';
    case 'composite':
      return 'Composite';
    default:
      return family ?? '—';
  }
}
