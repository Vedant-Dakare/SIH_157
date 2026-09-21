import type { QueryKey } from '@tanstack/react-query';

/** Central TanStack Query key factory. All keys are const tuples. */
export const queryKeys: {
  health: { status: QueryKey };
  runs: {
    all: QueryKey;
    detail: (runId: string) => QueryKey;
    manifest: (runId: string) => QueryKey;
    status: (runId: string) => QueryKey;
  };
  entities: {
    all: (runId: string, filters?: { band?: string; sector?: string }) => QueryKey;
    detail: (entityId: string, runId: string) => QueryKey;
    findings: (entityId: string, runId: string) => QueryKey;
  };
  findings: {
    detail: (findingId: string, runId?: string) => QueryKey;
    evidence: (findingId: string, runId?: string) => QueryKey;
    counterfactual: (findingId: string, runId?: string) => QueryKey;
  };
  queue: { list: (runId: string, limit: number) => QueryKey };
  audit: { verify: QueryKey; entries: (runId?: string) => QueryKey };
  validation: { report: (runId: string) => QueryKey };
} = {
  health: {
    status: ['health', 'status'],
  },
  runs: {
    all: ['runs'],
    detail: (runId: string) => ['runs', 'detail', runId],
    manifest: (runId: string) => ['runs', 'manifest', runId],
    status: (runId: string) => ['runs', 'status', runId],
  },
  entities: {
    all: (runId: string, filters: { band?: string; sector?: string } = {}) =>
      ['entities', 'all', runId, filters] as const,
    detail: (entityId: string, runId: string) => ['entities', 'detail', entityId, runId] as const,
    findings: (entityId: string, runId: string) =>
      ['entities', 'findings', entityId, runId] as const,
  },
  findings: {
    detail: (findingId: string, runId?: string) =>
      ['findings', 'detail', findingId, runId ?? ''] as const,
    evidence: (findingId: string, runId?: string) =>
      ['findings', 'evidence', findingId, runId ?? ''] as const,
    counterfactual: (findingId: string, runId?: string) =>
      ['findings', 'counterfactual', findingId, runId ?? ''] as const,
  },
  queue: {
    list: (runId: string, limit: number) => ['queue', 'list', runId, limit] as const,
  },
  audit: {
    verify: ['audit', 'verify'],
    entries: (runId?: string) => ['audit', 'entries', runId ?? 'all'] as const,
  },
  validation: {
    report: (runId: string) => ['validation', 'report', runId] as const,
  },
};
