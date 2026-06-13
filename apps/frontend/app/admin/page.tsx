'use client';

import { Button } from '@heroui/react';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { deleteIndexedDepartment, enrichIndexedDepartmentProfiles, getAdminMetrics, getCurrentUser, getScanStatus, listAdminReports, listIndexedDepartments, listRecommendationRequests, refreshIndexedDepartment, refreshIndexedDepartmentPublications, updateAdminReport } from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import type { IndexedDepartment } from '@/lib/types';

export default function AdminDashboardPage() {
  const [groups, setGroups] = useState<IndexedDepartment[]>([]);
  const [requests, setRequests] = useState<any[]>([]);
  const [jobStatus, setJobStatus] = useState<{ status: string; message: string }>({ status: 'idle', message: 'No active jobs' });
  const [message, setMessage] = useState('');
  const [authorized, setAuthorized] = useState(false);
  const [refreshing, setRefreshing] = useState<string | null>(null);
  const [refreshGroup, setRefreshGroup] = useState<IndexedDepartment | null>(null);
  const [refreshUrl, setRefreshUrl] = useState('');
  const [deleteGroup, setDeleteGroup] = useState<IndexedDepartment | null>(null);
  const [publicationRefreshGroup, setPublicationRefreshGroup] = useState<IndexedDepartment | null>(null);
  const [enrichGroup, setEnrichGroup] = useState<IndexedDepartment | null>(null);
  const [activeProgress, setActiveProgress] = useState<any | null>(null);
  const [reports, setReports] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<{ total_events: number; events: { name: string; count: number }[] } | null>(null);

  const load = () => {
    listIndexedDepartments().then(r => setGroups(r.groups)).catch(e => setMessage(e.message || 'Could not load indexed departments.'));
    listRecommendationRequests().then(r => setRequests(r.requests)).catch(() => undefined);
    getScanStatus().then(setJobStatus).catch(() => undefined);
    listAdminReports('new').then(r => setReports(r.reports)).catch(() => undefined);
    getAdminMetrics().then(setMetrics).catch(() => undefined);
  };

  const resolveReport = (id: number, status: 'resolved' | 'rejected') => {
    updateAdminReport(id, { status }).then(() => setReports(current => current.filter(r => r.id !== id))).catch(() => undefined);
  };

  useEffect(() => {
    getCurrentUser().then(response => {
      if (response.user.role !== 'admin') {
        setMessage('Admin role required.');
        return;
      }
      setAuthorized(true);
      load();
    }).catch(e => setMessage(e.message || 'Admin access required.'));
  }, []);

  useEffect(() => {
    if (!activeProgress?.id || activeProgress.status === 'completed' || activeProgress.status === 'error') return;
    const events = new EventSource(`/api/admin/indexed-departments/jobs/${encodeURIComponent(activeProgress.id)}/events`, { withCredentials: true });
    events.onmessage = event => {
      const data = JSON.parse(event.data);
      setActiveProgress(data);
      if (data.status === 'completed' || data.status === 'error') {
        events.close();
        load();
      }
    };
    events.onerror = () => {
      events.close();
      setActiveProgress((current: any) => current ? { ...current, status: 'error', message: 'Live progress connection closed. The backend job may still be running.' } : current);
    };
    return () => events.close();
  }, [activeProgress?.id, activeProgress?.status]);

  const totals = useMemo(() => groups.reduce((acc, g) => ({ professors: acc.professors + g.professor_count, publications: acc.publications + g.publication_count }), { professors: 0, publications: 0 }), [groups]);

  async function confirmRefresh() {
    if (!refreshGroup) return;
    const key = `${refreshGroup.university}-${refreshGroup.department}`;
    setRefreshing(key);
    setMessage('');
    try {
      const result = await refreshIndexedDepartment({ university: refreshGroup.university, department: refreshGroup.department, faculty_page_url: refreshUrl });
      setMessage(result.message);
      setRefreshGroup(null);
      setRefreshUrl('');
      load();
    } catch (e: any) {
      setMessage(e.message || 'Could not start refresh.');
    } finally {
      setRefreshing(null);
    }
  }

  async function confirmPublicationRefresh() {
    if (!publicationRefreshGroup) return;
    const key = `${publicationRefreshGroup.university}-${publicationRefreshGroup.department}`;
    setRefreshing(key);
    setMessage('');
    try {
      const result = await refreshIndexedDepartmentPublications({
        university: publicationRefreshGroup.university,
        department: publicationRefreshGroup.department,
        max_publications: 10,
      });
      setMessage(result.message);
      setActiveProgress({ id: result.progress_id, status: 'pending', current: 0, total: 0, percent: 0, message: result.message });
      setPublicationRefreshGroup(null);
    } catch (e: any) {
      setMessage(e.message || 'Could not fetch OpenAlex publications.');
    } finally {
      setRefreshing(null);
    }
  }

  async function confirmEnrichProfiles() {
    if (!enrichGroup) return;
    const key = `${enrichGroup.university}-${enrichGroup.department}`;
    setRefreshing(key);
    setMessage('');
    try {
      const result = await enrichIndexedDepartmentProfiles({
        university: enrichGroup.university,
        department: enrichGroup.department,
      });
      setMessage(result.message);
      setActiveProgress({ id: result.progress_id, status: 'pending', current: 0, total: 0, percent: 0, message: result.message });
      setEnrichGroup(null);
    } catch (e: any) {
      setMessage(e.message || 'Could not start profile enrichment.');
    } finally {
      setRefreshing(null);
    }
  }

  async function confirmDelete() {
    if (!deleteGroup) return;
    setMessage('');
    try {
      const result = await deleteIndexedDepartment({ university: deleteGroup.university, department: deleteGroup.department, confirm: true });
      setMessage(`Deleted ${result.professors_deleted} professors and ${result.publications_deleted} publications.`);
      setDeleteGroup(null);
      load();
    } catch (e: any) {
      setMessage(e.message || 'Delete failed.');
    }
  }

  if (!authorized) {
    return <div className="page narrow"><div className="card"><h2>Admin Dashboard</h2><p className="muted">{message || 'Checking admin access…'}</p></div></div>;
  }

  return (
    <div className="page">
      <div className="row between" style={{ marginBottom: 24 }}>
        <div>
          <p className="muted small-text">Local admin</p>
          <h2>Admin Dashboard</h2>
          <p className="muted">Manage indexed universities, user requests, and QA-gated agentic workflows. Existing data is only replaced after a staged workflow is published.</p>
        </div>
        <div className="row">
          <Button variant="secondary" onPress={load}>Refresh</Button>
          <Link className="button primary" href="/admin/onboarding">New agentic scan</Link>
        </div>
      </div>

      <div className="grid">
        <div className="card stat"><strong>{groups.length}</strong><span>indexed departments</span></div>
        <div className="card stat"><strong>{totals.professors}</strong><span>indexed professors</span></div>
        <div className="card stat"><strong>{totals.publications}</strong><span>indexed publications</span></div>
        <div className="card stat"><strong>{requests.length}</strong><span>requested items</span></div>
      </div>

      {jobStatus.status !== 'idle' && <div className={`card ${jobStatus.status === 'error' ? 'error' : ''}`} style={{ marginTop: 22 }}><strong>{jobStatus.status}:</strong> {jobStatus.message}</div>}
      {message && <div className="notice" style={{ marginTop: 22 }}>{message}</div>}
      {activeProgress && (
        <div className={`card ${activeProgress.status === 'error' ? 'error' : ''}`} style={{ marginTop: 22 }}>
          <div className="row between">
            <div>
              <strong>{activeProgress.status === 'completed' ? 'Complete' : activeProgress.status === 'error' ? 'Error' : 'Working'}:</strong> {activeProgress.message}
              {activeProgress.total > 0 && <p className="muted small-text">{activeProgress.current} of {activeProgress.total} professors · {Math.round(activeProgress.percent || 0)}%</p>}
            </div>
            {activeProgress.status === 'completed' && <Button variant="secondary" onPress={() => setActiveProgress(null)}>Dismiss</Button>}
          </div>
          <div className="progress" style={{ marginTop: 12 }}><span style={{ width: `${activeProgress.percent || 0}%` }} /></div>
          {activeProgress.summary && <p className="muted small-text" style={{ marginTop: 10 }}>{JSON.stringify(activeProgress.summary)}</p>}
        </div>
      )}

      <section className="card" style={{ marginTop: 22 }}>
        <h3 style={{ marginBottom: 12 }}>Indexed Universities and Departments</h3>
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th>University</th><th>Department</th><th className="num">Professors</th><th className="num">Publications</th><th className="end">Actions</th></tr></thead>
            <tbody>
              {groups.map(group => {
                const key = `${group.university}-${group.department}`;
                return (
                  <tr key={key}>
                    <td><strong>{group.university}</strong></td>
                    <td className="muted">{group.department}</td>
                    <td className="num">{group.professor_count}</td>
                    <td className="num">{group.publication_count}</td>
                    <td>
                      <div className="cell-actions">
                        <Button size="sm" variant="secondary" isDisabled={refreshing === key} onPress={() => setPublicationRefreshGroup(group)}>{refreshing === key ? 'Starting…' : 'Fetch 10 pubs'}</Button>
                        <Button size="sm" variant="secondary" isDisabled={refreshing === key} onPress={() => setEnrichGroup(group)}>Enrich profiles</Button>
                        <Button size="sm" variant="secondary" isDisabled={refreshing === key} onPress={() => { setRefreshGroup(group); setRefreshUrl(''); }}>Rescan faculty</Button>
                        <Button size="sm" variant="danger-soft" onPress={() => setDeleteGroup(group)}>Delete</Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
              {groups.length === 0 && <tr><td colSpan={5} className="muted" style={{ textAlign: 'center', padding: 22 }}>No indexed departments yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid two" style={{ marginTop: 22, alignItems: 'start' }}>
        <section className="card">
          <div className="row between">
            <h3>Requested Universities and Departments</h3>
            <Link className="accent" href="/recommend">Recommend page</Link>
          </div>
          <div style={{ marginTop: 14, display: 'grid', gap: 10 }}>
            {requests.length === 0 ? <p className="muted">No user requests yet.</p> : requests.slice(0, 8).map(request => (
              <div className="card soft" key={request.id || `${request.university}-${request.created_at}`}>
                <div className="row between"><strong>{request.university}</strong><span className="tag">{request.status || 'submitted'}</span></div>
                <p className="muted small-text">{request.department} · {request.user_email || 'unknown user'}</p>
                {request.faculty_page_url && <a className="accent small-text" href={request.faculty_page_url} target="_blank" rel="noreferrer">{request.faculty_page_url}</a>}
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="row between">
            <h3>Data reports queue</h3>
            <span className="home-count-chip">{reports.length} new</span>
          </div>
          <div style={{ marginTop: 14, display: 'grid', gap: 10 }}>
            {reports.length === 0 ? <p className="muted">No open reports. User-submitted corrections will appear here.</p> : reports.slice(0, 8).map(report => (
              <div className="card soft" key={report.id}>
                <div className="row between">
                  <strong>{String(report.reason || '').replace(/_/g, ' ')}</strong>
                  {report.target_id && <Link className="accent small-text" href={`/professors/${report.target_id}`}>professor #{report.target_id}</Link>}
                </div>
                <p className="muted small-text" style={{ margin: '4px 0' }}>{report.description}</p>
                {report.source_url && <a className="accent small-text" href={report.source_url} target="_blank" rel="noreferrer">{report.source_url}</a>}
                <div className="row" style={{ gap: 8, marginTop: 8 }}>
                  <Button size="sm" variant="secondary" onPress={() => resolveReport(report.id, 'resolved')}>Mark resolved</Button>
                  <Button size="sm" variant="ghost" onPress={() => resolveReport(report.id, 'rejected')}>Reject</Button>
                </div>
              </div>
            ))}
          </div>
          {metrics && (
            <div style={{ marginTop: 18, borderTop: '1px solid var(--divider)', paddingTop: 12 }}>
              <div className="row between"><strong>Product events · last {metrics ? 30 : 0} days</strong><span className="muted small-text">{metrics.total_events} total</span></div>
              <div className="row" style={{ gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
                {metrics.events.length === 0 ? <span className="muted small-text">No events recorded yet.</span> : metrics.events.map(e => (
                  <span className="signal" key={e.name}><i />{e.name.replace(/_/g, ' ')} · {e.count}</span>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="card">
          <div className="row between">
            <h3>Agentic scan dashboard</h3>
            <Link className="accent" href="/admin/onboarding">Open wizard</Link>
          </div>
          <p className="muted small-text" style={{ marginTop: 12 }}>Durable scan jobs, task progress, OpenAlex publication fetch, candidate review with confidence scores, and Supabase import all live in the Scan Dashboard.</p>
          <div className="row" style={{ gap: 8, marginTop: 14 }}>
            <Link className="button primary" href="/admin/onboarding">New agentic scan</Link>
            <Link className="button secondary" href="/admin/scans">Open Scan Dashboard</Link>
          </div>
        </section>
      </div>

      <ConfirmDialog
        open={!!refreshGroup}
        title="Stage department refresh"
        message="Enter the faculty page URL. This starts a durable OpenAlex-backed scan workflow; existing indexed data is not replaced until candidates are approved/imported."
        confirmLabel="Start refresh"
        value={refreshUrl}
        valueLabel="Faculty page URL"
        valuePlaceholder="https://example.edu/cs/faculty"
        onValueChange={setRefreshUrl}
        onCancel={() => setRefreshGroup(null)}
        onConfirm={confirmRefresh}
        confirming={!!refreshing}
      />
      <ConfirmDialog
        open={!!publicationRefreshGroup}
        variant="warning"
        title="Fetch 10 OpenAlex publications?"
        message={`Replace existing publication lists for ${publicationRefreshGroup?.university || ''} · ${publicationRefreshGroup?.department || ''} with up to 10 OpenAlex publications per professor. This runs in the background and does not enrich summaries; use Enrich profiles as the next step.`}
        confirmLabel="Fetch 10 publications"
        onCancel={() => setPublicationRefreshGroup(null)}
        onConfirm={confirmPublicationRefresh}
        confirming={!!refreshing}
      />
      <ConfirmDialog
        open={!!enrichGroup}
        variant="warning"
        title="Enrich profiles?"
        message={`Regenerate research summaries for ${enrichGroup?.university || ''} · ${enrichGroup?.department || ''} using profile text plus the current publication evidence. Run this after Fetch 10 pubs completes.`}
        confirmLabel="Enrich profiles"
        onCancel={() => setEnrichGroup(null)}
        onConfirm={confirmEnrichProfiles}
        confirming={!!refreshing}
      />
      <ConfirmDialog
        open={!!deleteGroup}
        variant="danger"
        title="Delete indexed department?"
        message={`Delete local professors/publications for ${deleteGroup?.university || ''} · ${deleteGroup?.department || ''}?`}
        confirmLabel="Delete indexed data"
        onCancel={() => setDeleteGroup(null)}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
