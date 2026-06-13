'use client';

import { Button } from '@heroui/react';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createScanJob } from '@/lib/api';

export default function AgenticOnboardingPage() {
  const router = useRouter();

  const [items, setItems] = useState([{ url: '', university: '', department: 'Computer Science' }]);
  const [automatic, setAutomatic] = useState(false);
  const [triggering, setTriggering] = useState(false);
  const [message, setMessage] = useState('');

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

  return (
    <div className="page">
      <div className="row between" style={{ marginBottom: 24 }}>
        <div>
          <p className="muted small-text">Local admin · Interactive UI</p>
          <h2>Agentic Roster Onboarding</h2>
          <p className="muted">Enter one or more faculty directories. The durable worker processes each department as a separate task, then crawls, extracts, fetches 10 OpenAlex publications with a confidence score, and summarizes each professor for review.</p>
        </div>
        <a className="button secondary" href="/admin/scans">Back to Scans</a>
      </div>

      <div className="card" style={{ maxWidth: 640 }}>
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
          <Button variant="secondary" type="button" onPress={() => setItems(rows => [...rows, { url: '', university: '', department: 'Computer Science' }])} style={{ alignSelf: 'flex-start' }}>Add another department</Button>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }} className="muted small-text">
            <input type="checkbox" checked={automatic} onChange={e => setAutomatic(e.target.checked)} />
            Automatic Mode (extracts, enriches, and summarizes without waiting)
          </label>
          <Button type="submit" isDisabled={triggering} style={{ alignSelf: 'flex-start' }}>
            {triggering ? 'Starting...' : 'Start Agentic Extraction'}
          </Button>
        </form>
        {message && <p className="error" style={{ marginTop: '12px' }}>{message}</p>}
        <p className="muted small-text" style={{ marginTop: 16 }}>Once started, you’ll be taken to the Scan Dashboard to watch task progress, review candidates with confidence scores, approve, and import.</p>
      </div>
    </div>
  );
}
