import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';

import { EmptyState } from '@/components/common/EmptyState';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/components/ui/toaster';
import { useHealth, useRuns } from '@/hooks/useRuns';
import { queryKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/utils';
import { uploadSubmission } from '@/lib/api';

const SettingsFormSchema = z.object({
  token: z.string().max(256, 'Token too long').optional().or(z.literal('')),
  defaultRun: z.string().optional().or(z.literal('')),
  queueLimit: z.enum(['10', '25', '50']),
  dateFormat: z.enum(['UTC', 'ISO', 'Local']),
});

type SettingsForm = z.infer<typeof SettingsFormSchema>;

const TOKEN_KEY = 'satsa-api-token';
const PREFS_KEY = 'satsa-settings';

function readPrefs(): Partial<SettingsForm> {
  try {
    const raw = window.localStorage.getItem(PREFS_KEY);
    return raw ? (JSON.parse(raw) as Partial<SettingsForm>) : {};
  } catch {
    return {};
  }
}

/** Settings: token, display prefs (localStorage) and system info. */
export default function SettingsPage() {
  const queryClient = useQueryClient();
  const runsQuery = useRuns();
  const healthQuery = useHealth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [uploadFiles, setUploadFiles] = useState<File[]>([]);
  const [companyId, setCompanyId] = useState('');
  const [uploading, setUploading] = useState(false);

  const runs = runsQuery.data?.runs ?? [];
  const stored = readPrefs();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<SettingsForm>({
    resolver: zodResolver(SettingsFormSchema),
    defaultValues: {
      token: window.localStorage.getItem(TOKEN_KEY) ?? '',
      defaultRun: stored.defaultRun ?? runs[0] ?? '',
      queueLimit: stored.queueLimit ?? '25',
      dateFormat: stored.dateFormat ?? 'UTC',
    },
  });

  const queueLimit = watch('queueLimit');
  const dateFormat = watch('dateFormat');
  const defaultRun = watch('defaultRun');

  function onSave(values: SettingsForm) {
    if (values.token) {
      window.localStorage.setItem(TOKEN_KEY, values.token);
    } else {
      window.localStorage.removeItem(TOKEN_KEY);
    }

    window.localStorage.setItem(
      PREFS_KEY,
      JSON.stringify({
        defaultRun: values.defaultRun,
        queueLimit: values.queueLimit,
        dateFormat: values.dateFormat,
      }),
    );

    toast({
      title: 'Settings saved',
      description: 'Preferences stored locally.',
    });
  }

  function onReset() {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(PREFS_KEY);

    reset({
      token: '',
      defaultRun: runs[0] ?? '',
      queueLimit: '25',
      dateFormat: 'UTC',
    });

    toast({
      title: 'Settings reset',
      description: 'Defaults restored.',
    });
  }

  async function onUpload(): Promise<void> {
    if (!uploadFiles.length || !companyId.trim()) {
      toast({
        title: 'Upload details incomplete',
        description: 'Select files and enter a company identifier.',
        variant: 'destructive',
      });
      return;
    }

    setUploading(true);

    try {
      const result = await uploadSubmission(
        companyId.trim(),
        `upload-${Date.now()}`,
        uploadFiles,
      );

      await queryClient.invalidateQueries({
        queryKey: queryKeys.runs.all,
      });

      toast({
        title: 'Data uploaded',
        description: `Run ${result.run_id} processed successfully. Loading Portfolio view.`,
      });

      setUploadFiles([]);
      navigate(`/portfolio?run=${encodeURIComponent(result.run_id)}`);
    } catch (error) {
      toast({
        title: 'Upload failed',
        description:
          error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <PageHeader
        title="Settings & System Configuration"
        description="Local-only supervisory preferences and secure ingestion gateway. All operations are confined to this air-gapped workstation."
      />

      <form
        onSubmit={(event) => {
          void handleSubmit(onSave)(event);
        }}
        className="space-y-6"
        aria-label="Settings form"
      >
        {/* API Configuration */}
        <section
          aria-label="API configuration"
          className="gov-card p-5 sm:p-6"
        >
          <div className="mb-4 border-b border-[#D9E2EC] pb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#123B5D]">
              API Loopback Configuration
            </h2>
            <p className="mt-1 text-xs text-[#52606D]">
              Local supervisory gateway endpoint connection parameters.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <Label
                htmlFor="api-url"
                className="text-xs font-semibold text-[#1F2933]"
              >
                API Base URL
              </Label>

              <Input
                id="api-url"
                value="http://127.0.0.1:8080"
                readOnly
                aria-readonly="true"
                className="mt-1 border-[#D9E2EC] bg-[#F8FAFC] font-mono text-xs text-[#1F2933]"
              />

              <p className="mt-1 text-[11px] text-[#52606D]">
                Pinned to loopback interface (127.0.0.1). Outbound transmission is strictly disallowed.
              </p>
            </div>

            <div>
              <Label
                htmlFor="api-token"
                className="text-xs font-semibold text-[#1F2933]"
              >
                API Authentication Token
              </Label>

              <Input
                id="api-token"
                type="password"
                autoComplete="off"
                placeholder="Empty unless the token gate is enabled"
                {...register('token')}
                className="mt-1 border-[#D9E2EC] bg-white text-xs text-[#1F2933] placeholder:text-slate-400 focus:border-[#1F5F8B] focus:ring-1 focus:ring-[#1F5F8B]"
              />

              {errors.token ? (
                <p className="mt-1 text-xs text-red-600">
                  {errors.token.message}
                </p>
              ) : null}
            </div>
          </div>
        </section>

        {/* Upload Company Data */}
        <section
          aria-label="Private company data upload"
          className="gov-card p-5 sm:p-6"
        >
          <div className="mb-4 border-b border-[#D9E2EC] pb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#123B5D]">
              Secure Ingestion Gateway
            </h2>
            <p className="mt-1 text-xs text-[#52606D]">
              Upload telemetry or operational case datasets for local analysis. Ingestion files: alerts, cases, investigations, escalations, assets, or telemetry.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <Label
                htmlFor="company-id"
                className="text-xs font-semibold text-[#1F2933]"
              >
                Entity / Company Identifier
              </Label>

              <Input
                id="company-id"
                value={companyId}
                onChange={(event) => setCompanyId(event.target.value)}
                className="mt-1 border-[#D9E2EC] bg-white text-xs text-[#1F2933] placeholder:text-slate-400 focus:border-[#1F5F8B] focus:ring-1 focus:ring-[#1F5F8B]"
                placeholder="e.g. acme_finance"
              />
            </div>

            <div>
              <Label
                htmlFor="company-files"
                className="text-xs font-semibold text-[#1F2933]"
              >
                Submission Files (.xlsx, .csv, .json, .parquet)
              </Label>

              <Input
                id="company-files"
                type="file"
                multiple
                accept=".xlsx,.xls,.csv,.json,.jsonl,.ndjson,.parquet,.sqlite,.sqlite3,.db,.duckdb"
                onChange={(event) =>
                  setUploadFiles(Array.from(event.target.files ?? []))
                }
                className="mt-1 border-[#D9E2EC] bg-white text-xs text-[#1F2933] file:mr-3 file:rounded file:border-0 file:bg-[#123B5D] file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-white hover:file:bg-[#0E2F4B]"
              />

              <p className="mt-1 text-[11px] text-[#52606D]">
                {uploadFiles.length
                  ? `${uploadFiles.length} file(s) selected`
                  : 'Supported formats: Excel (.xlsx, .xls), CSV, JSON, Parquet, SQLite, DuckDB. Max size: 100 MB.'}
              </p>
            </div>

            <Button
              type="button"
              onClick={() => void onUpload()}
              disabled={uploading || !uploadFiles.length}
              aria-label="Upload company data"
              className="border-[#123B5D] bg-[#123B5D] text-white hover:bg-[#0E2F4B]"
            >
              {uploading ? 'Processing & Ingesting…' : 'Upload and Analyze'}
            </Button>
          </div>
        </section>

        {/* Display Preferences */}
        <section
          aria-label="Display preferences"
          className="gov-card p-5 sm:p-6"
        >
          <div className="mb-4 border-b border-[#D9E2EC] pb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#123B5D]">
              Supervisory Display Preferences
            </h2>
            <p className="mt-1 text-xs text-[#52606D]">
              Default interface filters and presentation options.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <Label
                htmlFor="default-run"
                className="text-xs font-semibold text-[#1F2933]"
              >
                Default Pipeline Run
              </Label>

              <Select
                value={defaultRun}
                onValueChange={(value) => setValue('defaultRun', value)}
              >
                <SelectTrigger
                  id="default-run"
                  className="mt-1 border-[#D9E2EC] bg-white text-xs text-[#1F2933] hover:border-[#1F5F8B]"
                  aria-label="Default run"
                >
                  <SelectValue placeholder={defaultRun || 'Select a run'} />
                </SelectTrigger>

                <SelectContent className="border-[#D9E2EC] bg-white text-xs">
                  {runs.map((id) => (
                    <SelectItem
                      key={id}
                      value={id}
                      className="text-xs text-[#1F2933] focus:bg-[#EAF3F8] focus:text-[#123B5D]"
                    >
                      {id}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label
                htmlFor="queue-limit"
                className="text-xs font-semibold text-[#1F2933]"
              >
                Default Queue Limit
              </Label>

              <Select
                value={queueLimit}
                onValueChange={(value) =>
                  setValue(
                    'queueLimit',
                    value as SettingsForm['queueLimit'],
                  )
                }
              >
                <SelectTrigger
                  id="queue-limit"
                  className="mt-1 border-[#D9E2EC] bg-white text-xs text-[#1F2933] hover:border-[#1F5F8B]"
                  aria-label="Default queue limit"
                >
                  <SelectValue />
                </SelectTrigger>

                <SelectContent className="border-[#D9E2EC] bg-white text-xs">
                  {['10', '25', '50'].map((value) => (
                    <SelectItem
                      key={value}
                      value={value}
                      className="text-xs text-[#1F2933] focus:bg-[#EAF3F8] focus:text-[#123B5D]"
                    >
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label
                htmlFor="date-format"
                className="text-xs font-semibold text-[#1F2933]"
              >
                Date &amp; Time Format
              </Label>

              <Select
                value={dateFormat}
                onValueChange={(value) =>
                  setValue(
                    'dateFormat',
                    value as SettingsForm['dateFormat'],
                  )
                }
              >
                <SelectTrigger
                  id="date-format"
                  className="mt-1 border-[#D9E2EC] bg-white text-xs text-[#1F2933] hover:border-[#1F5F8B]"
                  aria-label="Date format"
                >
                  <SelectValue />
                </SelectTrigger>

                <SelectContent className="border-[#D9E2EC] bg-white text-xs">
                  {['UTC', 'ISO', 'Local'].map((value) => (
                    <SelectItem
                      key={value}
                      value={value}
                      className="text-xs text-[#1F2933] focus:bg-[#EAF3F8] focus:text-[#123B5D]"
                    >
                      {value}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </section>

        {/* System Information */}
        <section
          aria-label="System information"
          className="gov-card p-5 sm:p-6"
        >
          <div className="mb-4 border-b border-[#D9E2EC] pb-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#123B5D]">
              System Health &amp; Operational Information
            </h2>
            <p className="mt-1 text-xs text-[#52606D]">
              Status verification for active air-gapped backend engine.
            </p>
          </div>

          {healthQuery.isLoading ? (
            <LoadingState
              rows={2}
              message="Loading system info…"
            />
          ) : healthQuery.data ? (
            <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3 text-sm">
              <div className="rounded border border-[#D9E2EC] bg-[#F8FAFC] p-3">
                <dt className="text-xs font-bold uppercase tracking-wider text-[#52606D]">
                  Pipeline Version
                </dt>
                <dd className="mono mt-1 text-sm font-semibold text-[#123B5D]">
                  {healthQuery.data.pipeline_version}
                </dd>
              </div>

              <div className="rounded border border-[#D9E2EC] bg-[#F8FAFC] p-3">
                <dt className="text-xs font-bold uppercase tracking-wider text-[#52606D]">
                  Last Report Generated
                </dt>
                <dd className="mt-1 text-sm font-medium text-[#1F2933]">
                  {formatDate(healthQuery.data.generated_at)}
                </dd>
              </div>

              <div className="rounded border border-[#D9E2EC] bg-[#F8FAFC] p-3">
                <dt className="text-xs font-bold uppercase tracking-wider text-[#52606D]">
                  System Status
                </dt>
                <dd className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-emerald-700">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" aria-hidden="true" />
                  {healthQuery.data.status}
                </dd>
              </div>
            </dl>
          ) : (
            <EmptyState
              title="Offline"
              description="Backend unreachable."
            />
          )}
        </section>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <Button
            type="submit"
            aria-label="Save settings"
            className="border-[#123B5D] bg-[#123B5D] text-white hover:bg-[#0E2F4B]"
          >
            Save Preferences
          </Button>

          <Button
            type="button"
            variant="outline"
            onClick={onReset}
            aria-label="Reset settings"
            className="border-[#D9E2EC] bg-white text-[#123B5D] hover:bg-[#EAF3F8] hover:border-[#1F5F8B]"
          >
            Reset Defaults
          </Button>
        </div>
      </form>
    </div>
  );
}