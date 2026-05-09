'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { getAdminScan, listAdminScans, importAdminScan, listAdapters, runAdminScan, getScanStatus } from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { SkeletonLine } from '@/components/Skeleton';
import type { AdminScanDetail, AdminScanSummary } from '@/lib/types';

export default function AdminScansPage() {
  const [scans, setScans] = useState<AdminScanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AdminScanDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [adapters, setAdapters] = useState<string[]>([]);
  const [jobStatus, setJobStatus] = useState<{ status: string; message: string }>({ status: 'idle', message: 'No active jobs' });

  const fetchScans = useCallback(() => {
    setLoading(true);
    listAdminScans()
      .then(response => {
        setScans(response.scans);
        setSelectedId(current => current || response.scans[0]?.id || null);
      })
      .catch((e: any) => setError(e.message || 'Could not load scan artifacts. Admin access may be required.'))
      .finally(() => setLoading(false));
  }, []);

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
          <p className="muted">Review real scan artifacts before any SQLite import. This page reads files under <code>data/qa/scraper_runs</code>.</p>
        </div>
        <a className="button secondary" href="/professors">Browse indexed professors</a>
      </div>

      <div className="grid">
        <div className="card stat"><strong>{scans.length}</strong><span>scan runs</span></div>
        <div className="card stat"><strong>{totals.professors}</strong><span>candidate professors</span></div>
        <div className="card stat"><strong>{totals.ready}</strong><span>ready for import</span></div>
        <div className="card stat"><strong>{totals.issues}</strong><span>QA issues</span></div>
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


