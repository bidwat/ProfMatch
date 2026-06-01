'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { getAdminScan, listAdminScans, importAdminScan, listAdapters, runAdminScan, getScanStatus, listScanJobs, getScanJob, listScanJobTasks, listScanJobResults, listScanJobLogs, cancelScanJob, approveScanResult, rejectScanResult, fetchScanJobPublications, importApprovedScanResults } from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { SkeletonLine } from '@/components/Skeleton';
import type { AdminScanDetail, AdminScanSummary, ScanJob, ScanLog, ScanResult, ScanTask } from '@/lib/types';

export default function AdminScansPage() {
  const searchParams = useSearchParams();
  const [scans, setScans] = useState<AdminScanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminScanDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [adapters, setAdapters] = useState<string[]>([]);
  const [jobStatus, setJobStatus] = useState<{ status: string; message: string }>({ status: 'idle', message: 'No active jobs' });
  const [durableJobs, setDurableJobs] = useState<ScanJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);

  const fetchScans = useCallback(() => {
    setLoading(true);
    Promise.all([
      listAdminScans().catch(() => ({ scans: [] })),
      listScanJobs({ limit: 50 }).catch(() => ({ jobs: [] })),
    ])
      .then(([artifactResponse, jobResponse]) => {
        setScans(artifactResponse.scans);
        setDurableJobs(jobResponse.jobs);
        setSelectedId(current => current || artifactResponse.scans[0]?.id || null);
        const requestedJobId = Number(searchParams.get('job')) || null;
        setSelectedJobId(current => requestedJobId || current || jobResponse.jobs[0]?.id || null);
      })
      .catch((e: any) => setError(e.message || 'Could not load scan jobs. Admin access may be required.'))
      .finally(() => setLoading(false));
  }, [searchParams]);

  useEffect(() => {
    listAdapters()
      .then(response => setAdapters(response.adapters))
      .catch(console.error);
    
    fetchScans();

    const interval = setInterval(() => {
      if (document.hidden) return;
      getScanStatus().then(res => setJobStatus(res)).catch(() => {});
    }, 15000);
    
    return () => clearInterval(interval);
  }, [fetchScans]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    setDetailLoading(true);
    getAdminScan(selectedId)
      .then(setDetail)
      .catch((e: any) => setError(e.message || 'Could not load scan detail.'))
      .finally(() => setDetailLoading(false));
  }, [selectedId]);

  const totals = useMemo(() => scans.reduce((acc, scan) => ({
    professors: acc.professors + scan.professors,
    publications: acc.publications + scan.publications,
    issues: acc.issues + scan.total_issues,
    ready: acc.ready + (scan.db_import_allowed ? 1 : 0),
  }), { professors: 0, publications: 0, issues: 0, ready: 0 }), [scans]);

  return (
    <div className="page">
      <div className="row between" style={{ marginBottom: 24 }}>
        <div>
          <p className="muted small-text">Local admin · QA-gated ingestion</p>
          <h2>University Scan Dashboard</h2>
          <p className="muted">Review durable Postgres scan jobs, task state, logs, and importable candidates. Legacy QA artifacts remain visible below.</p>
        </div>
        <a className="button secondary" href="/professors">Browse indexed professors</a>
      </div>

      <div className="grid">
        <div className="card stat"><strong>{durableJobs.length}</strong><span>durable jobs</span></div>
        <div className="card stat"><strong>{durableJobs.reduce((sum, job) => sum + job.running_tasks, 0)}</strong><span>running tasks</span></div>
        <div className="card stat"><strong>{durableJobs.reduce((sum, job) => sum + job.failed_tasks, 0)}</strong><span>failed tasks</span></div>
        <div className="card stat"><strong>{totals.ready}</strong><span>legacy imports ready</span></div>
      </div>

      <div className="grid two" style={{ marginTop: 22, alignItems: 'start' }}>
        <div className="card" style={{ overflowX: 'auto' }}>
          <h3>Durable scan jobs</h3>
          <p className="muted small-text">Postgres-backed job/task state survives refreshes and worker restarts.</p>
          {durableJobs.length === 0 ? <p className="muted" style={{ marginTop: 12 }}>No durable scan jobs yet. Start one from Agentic Onboarding.</p> : (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12 }}>
              <thead><tr className="muted small-text"><th align="left">Job</th><th>Status</th><th>Progress</th><th>Tasks</th></tr></thead>
              <tbody>{durableJobs.map(job => (
                <tr key={job.id} onClick={() => setSelectedJobId(job.id)} className={selectedJobId === job.id ? 'table-row selected' : 'table-row'}>
                  <td style={{ padding: 10 }}><strong>#{job.id}</strong><br /><span className="muted small-text">{formatDate(job.created_at)} · {job.job_type}</span></td>
                  <td style={{ padding: 10 }}><Badge value={job.status} /></td>
                  <td style={{ padding: 10 }}><div className="progress"><span style={{ width: `${job.progress_percent}%` }} /></div><span className="muted small-text">{Math.round(job.progress_percent)}%</span></td>
                  <td style={{ padding: 10 }} className="muted small-text">{job.succeeded_tasks} ok · {job.running_tasks} running · {job.queued_tasks} queued · {job.failed_tasks} failed</td>
                </tr>
              ))}</tbody>
            </table>
          )}
        </div>
        <DurableJobDetail jobId={selectedJobId} onRefresh={fetchScans} />
      </div>

      <div className="grid two" style={{ alignItems: 'start' }}>
        <div className="card" style={{ marginTop: 22 }}>
          <h3>Agentic Onboarding <span className="tag" style={{ marginLeft: 8 }}>Experimental</span></h3>
          <p className="muted small-text" style={{ marginTop: 4 }}>Provide a faculty directory URL. An AI agent will analyze the HTML, extract the roster and detail pages, and guide you through a step-by-step enrichment and publication workflow.</p>
          <div style={{ marginTop: 16 }}>
            <a href="/admin/onboarding" className="button primary">Start Agentic Wizard</a>
          </div>
        </div>
      </div>

      {jobStatus.status === 'running' && (
        <div className="card" style={{ marginTop: 22, background: 'var(--surface-hover)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className="spinner" style={{
              display: 'inline-block',
              width: '18px',
              height: '18px',
              border: '2px solid var(--border)',
              borderTopColor: 'var(--primary)',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite'
            }}></span>
            <strong>Background Job Running:</strong> {jobStatus.message}
          </div>
        </div>
      )}

      {jobStatus.status === 'error' && (
        <div className="card error" style={{ marginTop: 22 }}>
          <strong>Background Job Failed:</strong> {jobStatus.message}
        </div>
      )}

      {loading && <div className="card skeleton-card" style={{ marginTop: 22 }}><SkeletonLine width="180px" height={18} /><SkeletonLine width="100%" height={12} /><SkeletonLine width="86%" height={12} /></div>}
      {error && <div className="error" style={{ marginTop: 22 }}>{error}</div>}
      {!loading && !error && scans.length === 0 && (
        <div className="card" style={{ marginTop: 22 }}>
          <h3>No scan artifacts yet</h3>
          <p className="muted">Use the form above to run a scan, then refresh this page when it completes.</p>
        </div>
      )}

      {scans.length > 0 && (
        <div className="grid two" style={{ marginTop: 22, alignItems: 'start' }}>
          <div className="card" style={{ overflowX: 'auto' }}>
            <h3>Runs</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12 }}>
              <thead><tr className="muted small-text"><th align="left">Scan</th><th>Status</th><th>Records</th><th>Issues</th><th>Gate</th></tr></thead>
              <tbody>
                {scans.map(scan => (
                  <tr key={scan.id} onClick={() => setSelectedId(scan.id)} className={selectedId === scan.id ? 'table-row selected' : 'table-row'}>
                    <td style={{ padding: 10 }}><strong>{scan.university}</strong><br /><span className="muted small-text">{scan.date} · {scan.adapter_name || 'adapter unknown'}</span></td>
                    <td style={{ padding: 10 }}><Badge value={scan.qa_status || scan.run_status || 'unknown'} /></td>
                    <td style={{ padding: 10 }} className="muted small-text">{scan.professors} faculty<br />{scan.publications} publications</td>
                    <td style={{ padding: 10 }} className="muted small-text">{scan.errors} errors · {scan.warnings} warnings · {scan.duplicates} duplicates</td>
                    <td style={{ padding: 10 }}><Badge value={scan.db_import_allowed ? 'import-ready' : 'review-required'} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>QA Artifact Detail</h3>
            {detailLoading && <div className="skeleton-card" style={{ marginTop: 12 }}><SkeletonLine width="70%" height={16} /><SkeletonLine width="100%" height={12} /><SkeletonLine width="92%" height={12} /><SkeletonLine width="82%" height={12} /></div>}
            {!detailLoading && detail ? <ScanDetail scan={detail} /> : !detailLoading && <p className="muted">Select a scan run.</p>}
          </div>
        </div>
      )}
    </div>
  );
}

function DurableJobDetail({ jobId, onRefresh }: { jobId: number | null; onRefresh: () => void }) {
  const [job, setJob] = useState<ScanJob | null>(null);
  const [tasks, setTasks] = useState<ScanTask[]>([]);
  const [results, setResults] = useState<ScanResult[]>([]);
  const [logs, setLogs] = useState<ScanLog[]>([]);
  const [loading, setLoading] = useState(false);
  const active = job && ['queued', 'running'].includes(job.status);

  const load = useCallback(() => {
    if (!jobId) return;
    setLoading(true);
    Promise.all([getScanJob(jobId), listScanJobTasks(jobId), listScanJobResults(jobId), listScanJobLogs(jobId)])
      .then(([jobRes, taskRes, resultRes, logRes]) => {
        setJob(jobRes.job);
        setTasks(taskRes.tasks);
        setResults(resultRes.results);
        setLogs(logRes.logs);
      })
      .finally(() => setLoading(false));
  }, [jobId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!active) return;
    const interval = setInterval(load, 7000);
    return () => clearInterval(interval);
  }, [active, load]);

  const action = async (fn: () => Promise<any>) => {
    await fn();
    load();
    onRefresh();
  };

  if (!jobId) return <div className="card"><h3>Durable job detail</h3><p className="muted">Select a durable job.</p></div>;
  return <div className="card">
    <div className="row between">
      <div><h3>Job #{jobId}</h3>{job && <p className="muted small-text">{job.status} · {job.total_tasks} task(s)</p>}</div>
      <div className="row" style={{ gap: 8 }}>
        <button className="button secondary" onClick={load} disabled={loading}>Refresh</button>
        {active && <button className="button secondary" onClick={() => action(() => cancelScanJob(jobId))}>Cancel</button>}
        {results.length > 0 && <button className="button secondary" onClick={() => action(() => fetchScanJobPublications(jobId, { max_publications: 10 }))}>Fetch 10 publications</button>}
        {results.some(r => r.status === 'approved') && <button className="button primary" onClick={() => action(() => importApprovedScanResults(jobId))}>Import approved</button>}
      </div>
    </div>
    {job && <div className="progress" style={{ marginTop: 12 }}><span style={{ width: `${job.progress_percent}%` }} /></div>}

    <DetailSection title="Tasks">
      {tasks.length === 0 ? <p className="muted small-text">No tasks yet.</p> : <div className="record-list">{tasks.map(task => <div key={task.id} className="record-block"><strong>{task.university} · {task.department}</strong><br /><Badge value={task.status} /> <span className="muted small-text">attempt {task.attempt_count}/{task.max_attempts}</span>{task.last_error && <p className="error" style={{ marginTop: 8 }}>{task.last_error}</p>}</div>)}</div>}
    </DetailSection>

    <DetailSection title="Candidate results">
      {results.length === 0 ? <p className="muted small-text">No candidates saved yet.</p> : <div className="record-list">{results.slice(0, 25).map(result => <div key={result.id} className="record-block">
        <div className="row between"><strong>{result.professor_name}</strong><Badge value={result.status} /></div>
        <p className="muted small-text">{result.title || 'Title unknown'} · {result.university} · {result.publications_payload?.length || 0}/10 publications · import: {result.import_status}</p>
        <p className="muted small-text">Fetching publications replaces the staged publication list with OpenAlex results.</p>
        {result.qa_issues?.length > 0 && <p className="muted small-text">QA: {result.qa_issues.map(issue => issue.code || issue.message).join(', ')}</p>}
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          <button className="button secondary" onClick={() => action(() => approveScanResult(result.id))}>Approve</button>
          <button className="button secondary" onClick={() => action(() => rejectScanResult(result.id))}>Reject</button>
        </div>
      </div>)}</div>}
    </DetailSection>

    <DetailSection title="Logs">
      {logs.length === 0 ? <p className="muted small-text">No logs yet.</p> : <div className="record-list">{logs.slice(0, 30).map(log => <div key={log.id} className="record-block"><Badge value={log.level} /> <strong>{log.event_type}</strong><p className="muted small-text">{formatDate(log.created_at)} · {log.message}</p></div>)}</div>}
    </DetailSection>
  </div>;
}

function ScanDetail({ scan }: { scan: AdminScanDetail }) {
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<any>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [confirmImport, setConfirmImport] = useState(false);

  const [rerunning, setRerunning] = useState(false);
  const [rerunMessage, setRerunMessage] = useState<string | null>(null);

  const handleImport = async () => {
    setImporting(true);
    setImportResult(null);
    setImportError(null);
    try {
      const result = await importAdminScan(scan.id);
      setImportResult(result);
    } catch (e: any) {
      setImportError(e.message || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  const handleRerun = async () => {
    if (!scan.adapter_name) return;
    setRerunning(true);
    setRerunMessage(null);
    try {
      await runAdminScan({
        adapter: scan.adapter_name,
        enrich_profiles: true,
        enrich_publications: true,
      });
      setRerunMessage('Enrichment scan started in background! Check back soon.');
    } catch (e: any) {
      setRerunMessage(e.message || 'Failed to start enrichment scan.');
    } finally {
      setRerunMessage(prev => prev || 'Enrichment scan started in background! Check back soon.');
      setTimeout(() => setRerunning(false), 2000);
    }
  };

  const paths = Object.entries(scan.paths).filter(([, value]) => Boolean(value));
  const missing = Object.entries(scan.issue_breakdown?.missing_required_fields || {});
  const byCode = Object.entries(scan.issue_breakdown?.by_code || {});
  return <div style={{ marginTop: 12 }}>
    <p className="muted"><strong>{scan.university}</strong> · {scan.department || 'department unknown'}</p>
    <div className="tags" style={{ margin: '12px 0' }}>
      <Badge value={`OpenRouter: ${scan.openrouter_status || 'missing audit'}`} />
      <Badge value={scan.db_import_allowed ? 'DB import allowed by QA' : 'DB import blocked until review'} />
    </div>
    <ul className="muted small-text" style={{ lineHeight: 1.9 }}>
      <li>Started: {formatDate(scan.started_at)}</li>
      <li>Completed: {formatDate(scan.completed_at)}</li>
      <li>QA status: {scan.qa_status || 'unknown'}</li>
      <li>Total issues: {scan.total_issues}</li>
    </ul>

    <DetailSection title="Issue breakdown">
      {byCode.length === 0 ? <p className="muted small-text">No validation issues were recorded.</p> : <div className="kv-list">{byCode.map(([code, count]) => <div key={code}><span>{code}</span><strong>{count}</strong></div>)}</div>}
    </DetailSection>

    <DetailSection title="Missing required fields">
      {missing.length === 0 ? <p className="muted small-text">No missing required fields were recorded.</p> : <div className="kv-list">{missing.map(([field, count]) => <div key={field}><span>{field}</span><strong>{count}</strong></div>)}</div>}
    </DetailSection>

    <DetailSection title="Extracted Professors Preview">
      {!scan.professors_preview || scan.professors_preview.length === 0 ? <p className="muted small-text">No professors extracted.</p> : <div className="record-list">{scan.professors_preview.slice(0, 5).map((prof, index) => <RecordBlock key={index} record={prof} />)}</div>}
      {scan.professors_preview && scan.professors_preview.length > 5 && <p className="muted small-text" style={{ marginTop: 8 }}>+ {scan.professors_preview.length - 5} more professors in preview...</p>}
    </DetailSection>

    <DetailSection title="Extracted Publications Preview">
      {!scan.publications_preview || scan.publications_preview.length === 0 ? <p className="muted small-text">No publications extracted.</p> : <div className="record-list">{scan.publications_preview.slice(0, 5).map((pub, index) => <RecordBlock key={index} record={pub} />)}</div>}
      {scan.publications_preview && scan.publications_preview.length > 5 && <p className="muted small-text" style={{ marginTop: 8 }}>+ {scan.publications_preview.length - 5} more publications in preview...</p>}
    </DetailSection>

    <DetailSection title="Validation issues">
      {scan.issues_preview.length === 0 ? <p className="muted small-text">No individual issues recorded.</p> : <div className="record-list">{scan.issues_preview.slice(0, 8).map((issue, index) => <RecordBlock key={index} record={issue} />)}</div>}
    </DetailSection>

    <DetailSection title="Duplicate candidates">
      {scan.duplicate_candidates.length === 0 ? <p className="muted small-text">No duplicate candidates recorded.</p> : <div className="record-list">{scan.duplicate_candidates.slice(0, 8).map((dup, index) => <RecordBlock key={index} record={dup} />)}</div>}
    </DetailSection>

    <DetailSection title="Artifact paths">
      <div className="artifact-list">
        {paths.map(([label, value]) => <div key={label}><span>{label.split('_').join(' ')}</span><code>{value}</code></div>)}
      </div>
    </DetailSection>

    <p className="notice" style={{ marginTop: 16 }}>This dashboard is read-only for artifact review. Imports must remain a separate, explicit QA-gated command.</p>

    <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
        {scan.db_import_allowed ? (
          <button className="button primary" onClick={() => setConfirmImport(true)} disabled={importing}>
            {importing ? 'Importing...' : 'Import to SQLite Database'}
          </button>
        ) : (
          <p className="muted small-text">Import disabled because QA validation did not pass.</p>
        )}

        {scan.adapter_name && (
          <button className="button secondary" onClick={handleRerun} disabled={rerunning}>
            {rerunning ? 'Starting...' : 'Enrich & Re-run Scan'}
          </button>
        )}
      </div>

      {rerunMessage && <p className="muted small-text" style={{ marginTop: 12 }}>{rerunMessage}</p>}
      {importError && <div className="error" style={{ marginTop: 12 }}>{importError}</div>}
      
      <ConfirmDialog
        open={confirmImport}
        variant="warning"
        title="Import scan to SQLite?"
        message={`Import ${scan.university} into the local SQLite database. This should only be done after QA review.`}
        confirmLabel="Import"
        onCancel={() => setConfirmImport(false)}
        onConfirm={() => { setConfirmImport(false); handleImport(); }}
        confirming={importing}
      />
      {importResult && (
        <div className="card" style={{ marginTop: 12 }}>
          <p className="tag success">Import Successful</p>
          <ul className="muted small-text" style={{ marginTop: 8 }}>
            <li>Professors inserted: {importResult.professors_inserted}</li>
            <li>Professors updated: {importResult.professors_updated}</li>
            <li>Publications inserted: {importResult.publications_inserted}</li>
            <li>Publications updated: {importResult.publications_updated}</li>
          </ul>
          {importResult.errors && importResult.errors.length > 0 && (
            <div style={{ marginTop: 8 }}>
              <strong>Errors during import:</strong>
              <pre className="code-block" style={{ marginTop: 4 }}>{importResult.errors.join('\n')}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  </div>;
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return <section style={{ marginTop: 18 }}><h4>{title}</h4>{children}</section>;
}

function RecordBlock({ record }: { record: Record<string, any> }) {
  const summary = record.message || record.reason || record.code || 'record';
  return <div className="record-block">
    <strong>{String(summary)}</strong>
    <pre>{JSON.stringify(record, null, 2)}</pre>
  </div>;
}

function Badge({ value }: { value: string }) {
  const ok = /ready|success|allowed|disabled/.test(value);
  return <span className={`tag ${ok ? 'success' : ''}`}>{value}</span>;
}

function formatDate(value?: string | null) {
  if (!value) return 'Not recorded';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}


