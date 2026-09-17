/**
 * Client-side replica of the Phase 5 ledger hash
 * (satsa/audit/hashing.py + ledger._hash_entry):
 * entry_hash = sha256("||".join([prev_hash, canonical_json(payload),
 *                                str(seq), ts, run_id, event_type]))
 * canonical_json = sorted keys, compact separators, Python str() scalars.
 * Uses SubtleCrypto (offline, no CDN). Integer floats render as "N.0" to
 * match Python repr; exotic exponents may differ (documented limitation).
 */

function pythonScalar(value: unknown, floats = false): string {
  if (value === null || value === undefined) {
    return 'null';
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false';
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      return 'null';
    }
    if (floats && Number.isInteger(value)) {
      return `${String(value)}.0`;
    }
    return String(value);
  }
  if (typeof value === 'string') {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return `[${value.map((item) => pythonScalar(item, floats)).join(',')}]`;
  }
  if (typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) =>
      a < b ? -1 : a > b ? 1 : 0,
    );
    const body = entries
      .map(([key, item]) => `${JSON.stringify(key)}:${pythonScalar(item, floats)}`)
      .join(',');
    return `{${body}}`;
  }
  return JSON.stringify(String(value));
}

/** Canonical JSON matching Python's sort_keys + compact separators. */
export function canonicalJson(value: unknown, floats = false): string {
  return pythonScalar(value, floats);
}

async function sha256Hex(text: string): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) {
    throw new Error('SubtleCrypto unavailable in this context');
  }
  const digest = await subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

export interface LedgerLikeEntry {
  seq: number;
  run_id: string;
  ts: string;
  event_type: string;
  payload: Record<string, unknown>;
  prev_hash: string;
  entry_hash: string;
}

/** Recompute an entry hash exactly like the backend. */
export async function hashEntry(entry: LedgerLikeEntry, floats = false): Promise<string> {
  const parts = [
    entry.prev_hash,
    canonicalJson(entry.payload, floats),
    String(entry.seq),
    entry.ts,
    entry.run_id,
    entry.event_type,
  ];
  return sha256Hex(parts.join('||'));
}

function hasIntegralNumbers(value: unknown): boolean {
  if (typeof value === 'number') {
    return Number.isInteger(value);
  }
  if (Array.isArray(value)) {
    return value.some(hasIntegralNumbers);
  }
  if (value !== null && typeof value === 'object') {
    return Object.values(value as Record<string, unknown>).some(hasIntegralNumbers);
  }
  return false;
}

/** Verify hash equality plus prev-hash linkage to the previous entry. */
export async function verifyEntry(
  entry: LedgerLikeEntry,
  expectedPrev: string,
): Promise<{ hashOk: boolean; linkOk: boolean }> {
  const candidates = [await hashEntry(entry, false)];
  if (hasIntegralNumbers(entry.payload)) {
    candidates.push(await hashEntry(entry, true));
  }
  return { hashOk: candidates.includes(entry.entry_hash), linkOk: entry.prev_hash === expectedPrev };
}
