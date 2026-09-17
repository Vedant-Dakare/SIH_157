import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

import { EmptyState } from '@/components/common/EmptyState';
import { LoadingState } from '@/components/common/LoadingState';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger } from '@/components/ui/select';
import { useToast } from '@/components/ui/toaster';
import { useHealth, useRuns } from '@/hooks/useRuns';
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
      JSON.stringify({ defaultRun: values.defaultRun, queueLimit: values.queueLimit, dateFormat: values.dateFormat }),
    );
    toast({ title: 'Settings saved', description: 'Preferences stored locally.' });
  }

  function onReset() {
    window.localStorage.removeItem(TOKEN_KEY);
    window.localStorage.removeItem(PREFS_KEY);
    reset({ token: '', defaultRun: runs[0] ?? '', queueLimit: '25', dateFormat: 'UTC' });
    toast({ title: 'Settings reset', description: 'Defaults restored.' });
  }

  async function onUpload(): Promise<void> {
    if (!uploadFiles.length || !companyId.trim()) {
      toast({ title: 'Upload details incomplete', description: 'Select files and enter a company identifier.', variant: 'destructive' });
      return;
    }
    setUploading(true);
    try {
      const result = await uploadSubmission(companyId.trim(), `upload-${Date.now()}`, uploadFiles);
      toast({ title: 'Data uploaded', description: `Run ${result.run_id} started. Open Portfolio after processing completes.` });
      setUploadFiles([]);
      navigate(`/portfolio?run=${encodeURIComponent(result.run_id)}`);
    } catch (error) {
      toast({ title: 'Upload failed', description: error instanceof Error ? error.message : 'Unknown error', variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <PageHeader title="Settings" description="Local-only preferences. Nothing leaves this workstation." />
      <form
        onSubmit={(event) => {
          void handleSubmit(onSave)(event);
        }}
        className="space-y-6"
        aria-label="Settings form"
      >
        <section aria-label="API configuration" className="rounded-md border border-slate-700 bg-slate-900 p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-50">API Configuration</h3>
          <div className="mb-3">
            <Label htmlFor="api-url">API Base URL</Label>
            <Input id="api-url" value="http://127.0.0.1:8080" readOnly aria-readonly="true" className="mt-1 opacity-70" />
            <p className="mt-1 text-xs text-slate-500">Pinned to loopback. Cannot point at external hosts.</p>
          </div>
          <div>
            <Label htmlFor="api-token">API Token</Label>
            <Input
              id="api-token"
              type="password"
              autoComplete="off"
              placeholder="Empty unless the token gate is enabled"
              {...register('token')}
              className="mt-1"
            />
            {errors.token ? <p className="mt-1 text-xs text-red-500">{errors.token.message}</p> : null}
          </div>
        </section>

        <section aria-label="Private company data upload" className="rounded-md border border-slate-700 bg-slate-900 p-4">
          <h3 className="mb-1 text-sm font-semibold text-slate-50">Upload Company Data</h3>
          <p className="mb-3 text-xs text-slate-400">Processed locally on this workstation. Use files named alerts, cases, investigations, escalations, assets, or telemetry.</p>
          <div className="space-y-3">
            <div>
              <Label htmlFor="company-id">Company identifier</Label>
              <Input id="company-id" value={companyId} onChange={(event) => setCompanyId(event.target.value)} className="mt-1" placeholder="acme_finance" />
            </div>
            <div>
              <Label htmlFor="company-files">Submission files</Label>
              <Input id="company-files" type="file" multiple accept=".csv,.json,.jsonl,.ndjson,.parquet,.sqlite,.sqlite3,.db,.duckdb" onChange={(event) => setUploadFiles(Array.from(event.target.files ?? []))} className="mt-1" />
              <p className="mt-1 text-xs text-slate-500">{uploadFiles.length ? `${uploadFiles.length} file(s) selected` : 'Maximum upload size: 100 MB.'}</p>
            </div>
            <Button type="button" onClick={() => void onUpload()} disabled={uploading || !uploadFiles.length} aria-label="Upload company data">
              {uploading ? 'Uploading…' : 'Upload and Analyze'}
            </Button>
          </div>
        </section>

        <section aria-label="Display preferences" className="rounded-md border border-slate-700 bg-slate-900 p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-50">Display Preferences</h3>
          <div className="mb-3">
            <Label htmlFor="default-run">Default run</Label>
            <Select value={defaultRun} onValueChange={(value) => setValue('defaultRun', value)}>
              <SelectTrigger id="default-run" className="mt-1" aria-label="Default run">
                {defaultRun || 'Select a run'}
              </SelectTrigger>
              <SelectContent>
                {runs.map((id) => (
                  <SelectItem key={id} value={id}>
                    {id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="mb-3">
            <Label htmlFor="queue-limit">Default queue limit</Label>
            <Select value={queueLimit} onValueChange={(value) => setValue('queueLimit', value as SettingsForm['queueLimit'])}>
              <SelectTrigger id="queue-limit" className="mt-1" aria-label="Default queue limit">
                {queueLimit}
              </SelectTrigger>
              <SelectContent>
                {['10', '25', '50'].map((value) => (
                  <SelectItem key={value} value={value}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="date-format">Date format</Label>
            <Select value={dateFormat} onValueChange={(value) => setValue('dateFormat', value as SettingsForm['dateFormat'])}>
              <SelectTrigger id="date-format" className="mt-1" aria-label="Date format">
                {dateFormat}
              </SelectTrigger>
              <SelectContent>
                {['UTC', 'ISO', 'Local'].map((value) => (
                  <SelectItem key={value} value={value}>
                    {value}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </section>

        <section aria-label="System information" className="rounded-md border border-slate-700 bg-slate-900 p-4">
          <h3 className="mb-3 text-sm font-semibold text-slate-50">System Information</h3>
          {healthQuery.isLoading ? (
            <LoadingState rows={2} message="Loading system info…" />
          ) : healthQuery.data ? (
            <dl className="space-y-1 text-sm">
              <div className="flex gap-2">
                <dt className="text-slate-500">Pipeline version:</dt>
                <dd className="mono text-slate-50">{healthQuery.data.pipeline_version}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-slate-500">Last report:</dt>
                <dd className="text-slate-50">{formatDate(healthQuery.data.generated_at)}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="text-slate-500">Status:</dt>
                <dd className="text-slate-50">{healthQuery.data.status}</dd>
              </div>
            </dl>
          ) : (
            <EmptyState title="Offline" description="Backend unreachable." />
          )}
        </section>

        <div className="flex gap-2">
          <Button type="submit" aria-label="Save settings">
            Save
          </Button>
          <Button type="button" variant="outline" onClick={onReset} aria-label="Reset settings">
            Reset
          </Button>
        </div>
      </form>
    </div>
  );
}
