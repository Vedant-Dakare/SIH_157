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
    detail: (findingId: string) => QueryKey;
    evidence: (findingId: string) => QueryKey;
    counterfactual: (findingId: string) => QueryKey;
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
    detail: (findingId: string) => ['findings', 'detail', findingId] as const,
    evidence: (findingId: string) => ['findings', 'evidence', findingId] as const,
    counterfactual: (findingId: string) => ['findings', 'counterfactual', findingId] as const,
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
