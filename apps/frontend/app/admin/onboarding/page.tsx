'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { createScanJob, getAgenticJob, enrichAgenticHomepage, fetchAgenticPublications, generateAgenticSummary, publishAgenticJob, listAgenticJobs, stopAgenticJob, deleteAgenticJob } from '@/lib/api';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { Avatar } from '@/components/ProfessorCard';

function parseProgress(msg: string) {
  const match = msg.match(/(\d+)\/(\d+)/);
  if (match) {
    const current = parseInt(match[1]);
    const total = parseInt(match[2]);
    const percent = Math.min(100, Math.round((current / total) * 100));
    return { current, total, percent, text: msg.replace(/\d+\/\d+/, '').replace(/:/, '').trim() };
  }
  return null;
}

export default function AgenticOnboardingPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const jobId = searchParams.get('job');
  
  const [items, setItems] = useState([{ url: '', university: '', department: 'Computer Science' }]);
  const [automatic, setAutomatic] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [message, setMessage] = useState('');
  
  const [job, setJob] = useState<any>(null);
  const [jobsList, setJobsList] = useState<any[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; redirect: boolean } | null>(null);

  useEffect(() => {
    if (!jobId) {
      listAgenticJobs().then(res => setJobsList(res.jobs)).catch(console.error);
      return;
    }
    getAgenticJob(jobId).then(res => setJob(res)).catch(() => {});
    const events = new EventSource(`/api/admin/agentic/job/${encodeURIComponent(jobId)}/events`, { withCredentials: true });
    events.onmessage = event => setJob(JSON.parse(event.data));
    events.onerror = () => events.close();
    return () => events.close();
  }, [jobId]);

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    const validItems = items.filter(item => item.url.trim() && item.university.trim());
    if (validItems.length === 0) return;
    setTriggering(true);
    setMessage('');
    try {
      const res = await createScanJob({
        items: validItems.map(item => ({
          university: item.university.trim(),
          department: item.department.trim() || 'Computer Science',
          faculty_url: item.url.trim(),
        })),
        settings: { fetch_publications: true, llm_extraction: automatic, max_attempts: 3 },
      });
      router.push(`/admin/scans?job=${res.job_id}`);
    } catch (err: any) {
      setMessage(err.message || 'Failed to start.');
    } finally {
      setTriggering(false);
    }
  };

  const handleAction = async (action: () => Promise<any>) => {
    try {
      await action();
    } catch (e: any) {
      setMessage(e.message || 'Action failed.');
    }
  };

  const handleStop = async () => {
    if (!jobId) return;
    try {
      await stopAgenticJob(jobId);
      const res = await getAgenticJob(jobId);
      setJob(res);
    } catch (e: any) {
      setMessage(e.message || 'Action failed.');
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteAgenticJob(deleteTarget.id);
      if (deleteTarget.redirect) {
        router.push('/admin/onboarding');
      } else {
        const res = await listAgenticJobs();
        setJobsList(res.jobs);
      }
      setDeleteTarget(null);
    } catch (e: any) {
      setMessage(e.message || 'Could not delete job.');
    }
  };

  if (jobId && job) {
    const isRunning = job.status === 'running' || job.status === 'pending';
    const isCompleted = job.status === 'completed';
    const isError = job.status === 'error';
    const isAutoDone = job.step === 'auto_done' || job.step === 'publish';
    
    const progress = parseProgress(job.message);

    return (
      <div className="page">
        <div className="row between" style={{ marginBottom: 24 }}>
          <div>
            <p className="muted small-text">Local admin · Agentic Pipeline</p>
            <h2>Agentic Wizard: {job.university}</h2>
            <p className="muted">{job.url}</p>
          </div>
          <div className="row" style={{ gap: 8 }}>
            {isRunning && (
              <button className="button secondary" onClick={handleStop}>Stop Job</button>
            )}
            <button className="button secondary" onClick={() => setDeleteTarget({ id: jobId, redirect: true })}>Delete</button>
            <a className="button secondary" href="/admin/onboarding">Start New</a>
          </div>
        </div>

        {isRunning && (
          <div className="card" style={{ marginBottom: 22, background: 'var(--surface-hover)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span className="spinner" style={{ display: 'inline-block', width: '18px', height: '18px', border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></span>
              <strong>{job.step.replace('_', ' ')}:</strong> 
              {progress ? progress.text : job.message}
            </div>
            {progress && (
              <div style={{ marginTop: 16 }}>
                <div className="row between small-text muted" style={{ marginBottom: 6 }}>
                  <span>{progress.current} of {progress.total}</span>
                  <span>{progress.percent}%</span>
                </div>
                <div className="progress"><span style={{ width: `${progress.percent}%` }}></span></div>
              </div>
            )}
          </div>
        )}

        {isError && (
          <div className="card error" style={{ marginBottom: 22 }}>
            <strong>Failed:</strong> {job.message}
          </div>
        )}

        {isCompleted && isAutoDone && (
          <div className="card" style={{ marginBottom: 22, borderColor: 'var(--green)', background: 'rgba(15, 123, 108, 0.05)' }}>
            <strong style={{ color: 'var(--green)' }}>{job.message}</strong>
            <div style={{ marginTop: 12 }}>
              <a href="/admin" className="button primary">Return to Admin Dashboard</a>
            </div>
          </div>
        )}

        {job.professors && job.professors.length > 0 && (
          <div className="card" style={{ overflowX: 'auto' }}>
            <div className="row between" style={{ marginBottom: 16 }}>
              <h3>Extracted Professors ({job.professors.length})</h3>
              <div className="row" style={{ gap: 8 }}>
                <button className="button secondary" disabled={isRunning} onClick={() => handleAction(() => enrichAgenticHomepage(jobId))}>
                  1. Enrich Homepages
                </button>
                <button className="button secondary" disabled={isRunning} onClick={() => handleAction(() => fetchAgenticPublications(jobId))}>
                  2. Fetch 10 Publications
                </button>
                <button className="button secondary" disabled={isRunning} onClick={() => handleAction(() => generateAgenticSummary(jobId))}>
                  3. Gen AI Summary
                </button>
                <button className="button primary" disabled={isRunning} onClick={() => handleAction(() => publishAgenticJob(jobId))}>
                  4. Publish to SQLite
                </button>
              </div>
            </div>
            
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12, fontSize: '14px' }}>
              <thead>
                <tr className="muted small-text">
                  <th align="left">Professor</th>
                  <th align="left">Contact & Links</th>
                  <th align="left">Research / Bio</th>
                  <th align="left">Publications</th>
                </tr>
              </thead>
              <tbody>
                {job.professors.map((p: any, i: number) => (
                  <tr key={i} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '12px 10px', verticalAlign: 'top' }}>
                      <div style={{ display: 'flex', gap: 12 }}>
                        <Avatar name={p.name || 'Professor'} photoUrl={p.photo} />
                        <div>
                          <strong>{p.name}</strong>
                          <div className="muted small-text">{p.position || 'Unknown Title'}</div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '12px 10px', verticalAlign: 'top', wordBreak: 'break-all' }}>
                      <div className="muted">{p.email || 'No email'}</div>
                      <div className="small-text" style={{ marginTop: 4 }}>
                        <a href={p.faculty_profile_url} target="_blank" rel="noreferrer">Profile</a>
                        {p.homepage && <><br /><a href={p.homepage} target="_blank" rel="noreferrer">Homepage</a></>}
                      </div>
                    </td>
                    <td style={{ padding: '12px 10px', verticalAlign: 'top', maxWidth: 300 }}>
                      <div className="muted" style={{ maxHeight: 100, overflowY: 'auto' }}>
                        {p.bio || 'No bio extracted'}
                      </div>
                      {p.ai_summary && (
                        <div style={{ marginTop: 8, padding: 8, background: 'var(--surface-hover)', borderRadius: 4 }}>
                          <strong>AI Summary:</strong> {p.ai_summary}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '12px 10px', verticalAlign: 'top' }}>
                      {p.publications && p.publications.length > 0 ? (
                        <ul style={{ margin: 0, paddingLeft: 16 }}>
                          {p.publications.slice(0, 3).map((pub: any, j: number) => (
                            <li key={j} className="muted small-text" style={{ marginBottom: 4 }}>{pub.title} ({pub.year})</li>
                          ))}
                          {p.publications.length > 3 && <li className="muted small-text">+ {p.publications.length - 3} more</li>}
                        </ul>
                      ) : (
                        <span className="muted small-text">None fetched</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <ConfirmDialog
          open={!!deleteTarget}
          variant="danger"
          title="Delete agentic job?"
          message="This removes the staged local job artifact. Published SQLite data is not changed."
          confirmLabel="Delete job"
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
        />
      </div>
    );
  }

  return (
    <div className="page">
      <div className="row between" style={{ marginBottom: 24 }}>
        <div>
          <p className="muted small-text">Local admin · Interactive UI</p>
          <h2>Agentic Roster Onboarding</h2>
          <p className="muted">Enter one or more faculty directories. The durable worker will process each department as a separate task.</p>
        </div>
        <a className="button secondary" href="/admin/scans">Back to Scans</a>
      </div>

      <div className="grid two" style={{ alignItems: 'start' }}>
        <div className="card">
          <h3>Create Durable Scan Job</h3>
          <form onSubmit={handleStart} style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginTop: 16 }}>
            {items.map((item, index) => (
              <div className="card soft" key={index} style={{ display: 'grid', gap: 10 }}>
                <div className="row between"><strong>Department {index + 1}</strong>{items.length > 1 && <button className="ghost small" type="button" onClick={() => setItems(rows => rows.filter((_, i) => i !== index))}>Remove</button>}</div>
                <div>
                  <label className="small-text muted" style={{ display: 'block', marginBottom: 4 }}>Faculty Directory URL</label>
                  <input className="input" type="url" value={item.url} onChange={e => setItems(rows => rows.map((row, i) => i === index ? { ...row, url: e.target.value } : row))} placeholder="https://cs.university.edu/faculty" required={index === 0} />
                </div>
                <div>
                  <label className="small-text muted" style={{ display: 'block', marginBottom: 4 }}>University Name</label>
                  <input className="input" type="text" value={item.university} onChange={e => setItems(rows => rows.map((row, i) => i === index ? { ...row, university: e.target.value } : row))} placeholder="e.g. Stanford University" required={index === 0} />
                </div>
                <div>
                  <label className="small-text muted" style={{ display: 'block', marginBottom: 4 }}>Department Name</label>
                  <input className="input" type="text" value={item.department} onChange={e => setItems(rows => rows.map((row, i) => i === index ? { ...row, department: e.target.value } : row))} />
                </div>
              </div>
            ))}
            <button className="button secondary" type="button" onClick={() => setItems(rows => [...rows, { url: '', university: '', department: 'Computer Science' }])} style={{ alignSelf: 'flex-start' }}>Add another department</button>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }} className="muted small-text">
              <input type="checkbox" checked={automatic} onChange={e => setAutomatic(e.target.checked)} />
              Automatic Mode (extracts, enriches, and summarizes without waiting)
            </label>
            <button className="button primary" type="submit" disabled={triggering} style={{ alignSelf: 'flex-start' }}>
              {triggering ? 'Starting...' : 'Start Agentic Extraction'}
            </button>
          </form>
          {message && <p className="error" style={{ marginTop: '12px' }}>{message}</p>}
        </div>

        <div className="card">
          <h3>Recent Agentic Jobs</h3>
          {jobsList.length === 0 ? (
            <p className="muted small-text" style={{ marginTop: 12 }}>No agentic jobs found.</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12 }}>
              <thead>
                <tr className="muted small-text">
                  <th align="left">University</th>
                  <th align="left">Status</th>
                  <th align="left">Professors</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {jobsList.map(j => (
                  <tr key={j.id} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '10px 0' }}>
                      <a href={`/admin/onboarding?job=${j.id}`} style={{ fontWeight: 'bold', color: 'var(--accent)' }}>{j.university}</a>
                      <div className="muted small-text">{new Date(j.created_at).toLocaleString()}</div>
                    </td>
                    <td style={{ padding: '10px 0' }}>
                      <span className={`tag ${j.status === 'completed' ? 'success' : j.status === 'stopped' || j.status === 'error' ? 'error' : ''}`}>{j.status}</span>
                      <div className="muted small-text">{j.step.replace('_', ' ')}</div>
                    </td>
                    <td style={{ padding: '10px 0' }}>{j.professor_count || 0}</td>
                    <td style={{ padding: '10px 0', textAlign: 'right' }}>
                      <button className="button secondary" style={{ padding: '4px 8px', fontSize: '12px' }} onClick={() => setDeleteTarget({ id: j.id, redirect: false })}>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      <ConfirmDialog
        open={!!deleteTarget}
        variant="danger"
        title="Delete agentic job?"
        message="This removes the staged local job artifact. Published SQLite data is not changed."
        confirmLabel="Delete job"
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </div>
  );
}
