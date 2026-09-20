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
    <div className="max-w-2xl space-y-6">
      <PageHeader
        title="Settings"
        description="Local-only preferences. Nothing leaves this workstation."
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
          className="rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] p-5"
        >
          <h3 className="mb-4 text-sm font-semibold text-[#123D73]">
            API Configuration
          </h3>

          <div className="mb-4">
            <Label
              htmlFor="api-url"
              className="text-[#334155]"
            >
              API Base URL
            </Label>

            <Input
              id="api-url"
              value="http://127.0.0.1:8080"
              readOnly
              aria-readonly="true"
              className="mt-1 border-[#BFDBFE] bg-white text-[#123D73] opacity-80"
            />

            <p className="mt-1 text-xs text-[#64748B]">
              Pinned to loopback. Cannot point at external hosts.
            </p>
          </div>

          <div>
            <Label
              htmlFor="api-token"
              className="text-[#334155]"
            >
              API Token
            </Label>

            <Input
              id="api-token"
              type="password"
              autoComplete="off"
              placeholder="Empty unless the token gate is enabled"
              {...register('token')}
              className="mt-1 border-[#BFDBFE] bg-white text-[#123D73] placeholder:text-slate-400 focus:border-[#123D73] focus:ring-blue-100"
            />

            {errors.token ? (
              <p className="mt-1 text-xs text-red-600">
                {errors.token.message}
              </p>
            ) : null}
          </div>
        </section>

        {/* Upload Company Data */}
        <section
          aria-label="Private company data upload"
          className="rounded-lg border border-[#BFDBFE] bg-[#E0EEFF] p-5"
        >
          <h3 className="mb-1 text-sm font-semibold text-[#123D73]">
            Upload Company Data
          </h3>

          <p className="mb-4 text-xs leading-5 text-[#5B7595]">
            Processed locally on this workstation. Use files named alerts,
            cases, investigations, escalations, assets, or telemetry.
          </p>

          <div className="space-y-4">
            <div>
              <Label
                htmlFor="company-id"
                className="text-[#334155]"
              >
                Company identifier
              </Label>

              <Input
                id="company-id"
                value={companyId}
                onChange={(event) => setCompanyId(event.target.value)}
                className="mt-1 border-[#BFDBFE] bg-white text-[#123D73] placeholder:text-slate-400 focus:border-[#123D73] focus:ring-blue-100"
                placeholder="acme_finance"
              />
            </div>

            <div>
              <Label
                htmlFor="company-files"
                className="text-[#334155]"
              >
                Submission files (.xlsx, .csv, .json, .parquet)
              </Label>

              <Input
                id="company-files"
                type="file"
                multiple
                accept=".xlsx,.xls,.csv,.json,.jsonl,.ndjson,.parquet,.sqlite,.sqlite3,.db,.duckdb"
                onChange={(event) =>
                  setUploadFiles(Array.from(event.target.files ?? []))
                }
                className="mt-1 border-[#BFDBFE] bg-white text-[#334155] file:mr-3 file:rounded-md file:border-0 file:bg-[#123D73] file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-white hover:file:bg-[#0B315D]"
              />

              <p className="mt-1 text-xs text-[#64748B]">
                {uploadFiles.length
                  ? `${uploadFiles.length} file(s) selected`
                  : 'Supports Excel (.xlsx, .xls), CSV, JSON, and Parquet. Max size: 100 MB.'}
              </p>
            </div>

            <Button
              type="button"
              onClick={() => void onUpload()}
              disabled={uploading || !uploadFiles.length}
              aria-label="Upload company data"
              className="border-[#123D73] bg-[#123D73] text-white hover:border-[#BFDBFE] hover:bg-blue-100 hover:text-[#123D73]"
            >
              {uploading ? 'Uploading…' : 'Upload and Analyze'}
            </Button>
          </div>
        </section>

        {/* Display Preferences */}
        <section
          aria-label="Display preferences"
          className="rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] p-5"
        >
          <h3 className="mb-4 text-sm font-semibold text-[#123D73]">
            Display Preferences
          </h3>

          <div className="mb-4">
            <Label
              htmlFor="default-run"
              className="text-[#334155]"
            >
              Default run
            </Label>

            <Select
              value={defaultRun}
              onValueChange={(value) => setValue('defaultRun', value)}
            >
              <SelectTrigger
                id="default-run"
                className="mt-1 border-[#BFDBFE] bg-white text-[#123D73] hover:bg-blue-50"
                aria-label="Default run"
              >
                {defaultRun || 'Select a run'}
              </SelectTrigger>

              <SelectContent className="border-[#BFDBFE] bg-white">
                {runs.map((id) => (
                  <SelectItem
                    key={id}
                    value={id}
                    className="text-[#123D73] focus:bg-blue-50 focus:text-[#123D73]"
                  >
                    {id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="mb-4">
            <Label
              htmlFor="queue-limit"
              className="text-[#334155]"
            >
              Default queue limit
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
                className="mt-1 border-[#BFDBFE] bg-white text-[#123D73] hover:bg-blue-50"
                aria-label="Default queue limit"
              >
                {queueLimit}
              </SelectTrigger>

              <SelectContent className="border-[#BFDBFE] bg-white">
                {['10', '25', '50'].map((value) => (
                  <SelectItem
                    key={value}
                    value={value}
                    className="text-[#123D73] focus:bg-blue-50 focus:text-[#123D73]"
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
              className="text-[#334155]"
            >
              Date format
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
                className="mt-1 border-[#BFDBFE] bg-white text-[#123D73] hover:bg-blue-50"
                aria-label="Date format"
              >
                {dateFormat}
              </SelectTrigger>

              <SelectContent className="border-[#BFDBFE] bg-white">
                {['UTC', 'ISO', 'Local'].map((value) => (
                  <SelectItem
                    key={value}
                    value={value}
                    className="text-[#123D73] focus:bg-blue-50 focus:text-[#123D73]"
                  >
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </section>

        {/* System Information */}
        <section
          aria-label="System information"
          className="rounded-lg border border-[#BFDBFE] bg-[#E0EEFF] p-5"
        >
          <h3 className="mb-4 text-sm font-semibold text-[#123D73]">
            System Information
          </h3>

          {healthQuery.isLoading ? (
            <LoadingState
              rows={2}
              message="Loading system info…"
            />
          ) : healthQuery.data ? (
            <dl className="space-y-3 text-sm">
              <div className="flex gap-2">
                <dt className="text-[#64748B]">
                  Pipeline version:
                </dt>

                <dd className="mono font-medium text-[#123D73]">
                  {healthQuery.data.pipeline_version}
                </dd>
              </div>

              <div className="flex gap-2">
                <dt className="text-[#64748B]">
                  Last report:
                </dt>

                <dd className="text-[#123D73]">
                  {formatDate(healthQuery.data.generated_at)}
                </dd>
              </div>

              <div className="flex gap-2">
                <dt className="text-[#64748B]">
                  Status:
                </dt>

                <dd className="font-medium text-[#123D73]">
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
        <div className="flex gap-2">
          <Button
            type="submit"
            aria-label="Save settings"
            className="border-[#123D73] bg-[#123D73] text-white hover:border-[#BFDBFE] hover:bg-blue-100 hover:text-[#123D73]"
          >
            Save
          </Button>

          <Button
            type="button"
            variant="outline"
            onClick={onReset}
            aria-label="Reset settings"
            className="border-[#BFDBFE] bg-[#EFF6FF] text-[#123D73] hover:bg-blue-100 hover:text-[#123D73]"
          >
            Reset
          </Button>
        </div>
      </form>
    </div>
  );
}