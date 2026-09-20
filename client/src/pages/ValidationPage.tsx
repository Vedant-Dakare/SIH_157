import { Link, useSearchParams } from 'react-router-dom';

import { EmptyState } from '@/components/common/EmptyState';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import { useToast } from '@/components/ui/toaster';
import { getValidationReport } from '@/lib/api';
import type { ValidationReport } from '@/types/api';
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/lib/queryKeys';

export interface AblationRow {
  family_name: string;
  signals_disabled: string[];
  baseline_recall: number;
  ablated_recall: number;
  recall_drop: number;
  relative_contribution_pct: number;
}

export interface DisagreementRow {
  entity_id: string;
  signal_id: string;
  sat_sa_flagged: boolean;
  expert_flagged: boolean;
  kind: 'SAT-SA only' | 'Expert only';
  finding_id?: string;
}

export interface ValidationExtras {
  ablation?: AblationRow[];
  disagreements?: DisagreementRow[];
}

function MetricCards({ report }: { report: ValidationReport }) {
  const cards = [
    { label: 'Precision@10', value: report.precision_at_k['10'] ?? 0 },
    { label: 'Recall (overall)', value: report.overall_recall },
    { label: 'F1 (execution_gap)', value: report.f1_by_family['execution_gap'] ?? 0 },
    { label: "Cohen's Kappa", value: report.cohens_kappa },
  ];
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label}>
          <CardHeader>
            <CardTitle className="text-sm font-medium text-slate-500">{card.label}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold text-[#123D73]">{card.value.toFixed(3)}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function Bar({ label, value, colour }: { label: string; value: number; colour: string }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span>{value.toFixed(3)}</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={Math.round(value * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label} bar`}
        className="h-2 w-full overflow-hidden rounded-full bg-slate-200"
      >
        <div className={`h-full ${colour}`} style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} />
      </div>
    </div>
  );
}

export function ValidationSections({
  report,
  extras = {},
}: {
  report: ValidationReport;
  extras?: ValidationExtras;
}) {
  const { toast } = useToast();
  const ablation = [...(extras.ablation ?? [])].sort(
    (a, b) => b.relative_contribution_pct - a.relative_contribution_pct,
  );
  const disagreements = extras.disagreements ?? [];

  function exportDisagreements(): void {
    const header = 'entity_id,signal_id,sat_sa_flagged,expert_flagged,kind\n';
    const body = disagreements
      .map((row) => [row.entity_id, row.signal_id, row.sat_sa_flagged, row.expert_flagged, row.kind].join(','))
      .join('\n');
    const blob = new Blob([header + body], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `disagreements-${report.run_id}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
    toast({ title: 'Disagreements exported', description: `${disagreements.length} rows.` });
  }

  const scenarios = Object.entries(report.recall_by_scenario).sort(([a], [b]) => a.localeCompare(b));
  return (
    <div className="space-y-6">
      <MetricCards report={report} />
      <Tabs defaultValue="precision">
        <TabsList aria-label="Validation sections">
          <TabsTrigger value="precision">Precision &amp; Recall</TabsTrigger>
          <TabsTrigger value="scenarios">By Scenario</TabsTrigger>
          <TabsTrigger value="ablation">Ablation</TabsTrigger>
          <TabsTrigger value="disagreements">Disagreements</TabsTrigger>
        </TabsList>
        <TabsContent value="precision">
          <ErrorBoundary label="precision panel">

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div className="rounded-md border border-slate-200 bg-white p-4">
              <h3 className="mb-3 text-sm font-semibold text-slate-900">Precision@k</h3>
              <div className="space-y-3">
                {[5, 10, 20].map((k) => (
                  <Bar key={k} label={`k = ${k}`} value={report.precision_at_k[String(k)] ?? 0} colour="bg-blue-500" />
                ))}
              </div>
            </div>
            <div className="rounded-md border border-slate-200 bg-white p-4">
              <h3 className="mb-3 text-sm font-semibold text-slate-900">Recall by signal family</h3>
              <div className="space-y-3">
                {Object.entries(report.f1_by_family).map(([family, value]) => (
                  <Bar key={family} label={family} value={value} colour="bg-green-500" />
                ))}
              </div>
            </div>
          </div>
          </ErrorBoundary>
        </TabsContent>
        <TabsContent value="scenarios">
          <ErrorBoundary label="scenarios panel">

          <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
            <table aria-label="Recall by scenario" className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
                  <th className="px-3 py-2 font-medium">Scenario</th>
                  <th className="px-3 py-2 font-medium">Recall</th>
                  <th className="px-3 py-2 font-medium">Notes</th>
                </tr>
              </thead>
              <tbody>
                {scenarios.map(([scenario, recall]) => (
                  <tr
                    key={scenario}
                    className={`border-b border-slate-100 last:border-0 hover:bg-blue-50/40 ${scenario === 'S1' ? 'bg-slate-50' : ''}`}
                  >
                    <td className="mono px-3 py-2 font-medium text-slate-900">{scenario}</td>
                    <td className="px-3 py-2 tabular-nums text-slate-900">{recall.toFixed(3)}</td>
                    <td className="px-3 py-2 text-slate-500">
                      {scenario === 'S1' ? 'Healthy control — expects 0 HIGH findings.' : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          </ErrorBoundary>
        </TabsContent>
        <TabsContent value="ablation">
          <ErrorBoundary label="ablation panel">

          {ablation.length === 0 ? (
            <p className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              No ablation table for this run. See docs/SIGNAL_CATALOGUE.md for the latest table.
            </p>
          ) : (
            <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
              <table aria-label="Ablation by signal family" className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
                    {['Family', 'Disabled', 'Baseline', 'Ablated', 'Drop', 'Contribution %'].map((header) => (
                      <th key={header} className="px-3 py-2 font-medium">
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {ablation.map((row) => (
                    <tr key={row.family_name} className="border-b border-slate-100 last:border-0 hover:bg-blue-50/40">
                      <td className="px-3 py-2 font-medium text-slate-900">{row.family_name}</td>
                      <td className="px-3 py-2 text-slate-600">{row.signals_disabled.length}</td>
                      <td className="px-3 py-2 tabular-nums text-slate-900">{row.baseline_recall.toFixed(3)}</td>
                      <td className="px-3 py-2 tabular-nums text-slate-900">{row.ablated_recall.toFixed(3)}</td>
                      <td className={`px-3 py-2 tabular-nums ${row.recall_drop > 0.1 ? 'text-red-600' : 'text-slate-600'}`}>
                        {row.recall_drop.toFixed(3)}
                      </td>
                      <td className="px-3 py-2 tabular-nums text-slate-900">{row.relative_contribution_pct.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          </ErrorBoundary>
        </TabsContent>
        <TabsContent value="disagreements">
          <ErrorBoundary label="disagreements panel">

          {disagreements.length === 0 ? (
            <p className="rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
              No recorded disagreements for this run.
            </p>
          ) : (
            <div className="space-y-3">
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={exportDisagreements}
                  aria-label="Export disagreements as CSV"
                  className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-[#123D73] hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-200"
                >
                  Export CSV
                </button>
              </div>
              <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
                <table aria-label="Expert disagreements" className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 bg-slate-50 text-left text-slate-600">
                      {['Entity', 'Signal', 'SAT-SA', 'Expert', 'Type', 'Evidence'].map((header) => (
                        <th key={header} className="px-3 py-2 font-medium">
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {disagreements.map((row, index) => (
                      <tr key={`${row.entity_id}-${row.signal_id}-${index}`} className="border-b border-slate-100 last:border-0 hover:bg-blue-50/40">
                        <td className="mono px-3 py-2 font-medium text-slate-900">{row.entity_id}</td>
                        <td className="mono px-3 py-2 text-slate-800">{row.signal_id}</td>
                        <td className="px-3 py-2 text-slate-600">{row.sat_sa_flagged ? 'yes' : 'no'}</td>
                        <td className="px-3 py-2 text-slate-600">{row.expert_flagged ? 'yes' : 'no'}</td>
                        <td className="px-3 py-2 font-medium text-slate-900">{row.kind}</td>
                        <td className="px-3 py-2">
                          {row.finding_id ? (
                            <Link to={`/findings/${row.finding_id}`} className="font-medium text-[#2563A8] underline underline-offset-4 hover:text-[#123D73]">
                              Evidence
                            </Link>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
          </ErrorBoundary>
        </TabsContent>
      </Tabs>
    </div>
  );
}

/** Validation report page: provisional endpoint with artefact fallback. */
export default function ValidationPage() {
  const [searchParams] = useSearchParams();
  const runId = searchParams.get('run') ?? '';
  const reportQuery = useQuery({
    queryKey: queryKeys.validation.report(runId),
    queryFn: () => getValidationReport(runId),
    enabled: Boolean(runId),
  });

  return (
    <div>
      <PageHeader title="Validation Report" description="Precision, recall, ablation and expert agreement." />
      {reportQuery.isLoading ? (
        <p role="status" className="py-8 text-center text-sm text-slate-600">
          Loading validation report…
        </p>
      ) : null}
      {reportQuery.error || !runId ? (
        <EmptyState
          title="No validation report"
          description="No stable /validation endpoint exists yet; reports live in data/curated/validation/ from Phase 7 runs. Select a run to retry."
        />
      ) : null}
      {!reportQuery.isLoading && !reportQuery.error && reportQuery.data ? (
        <ValidationSections report={reportQuery.data} />
      ) : null}
    </div>
  );
}
