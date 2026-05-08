'use client';

import { useState } from 'react';
import { submitRecommendation } from '@/lib/api';

const emptyForm = { university: '', department: '', faculty_page_url: '' };

export default function RecommendPage() {
  const [form, setForm] = useState(emptyForm);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function validate() {
    if (!form.university.trim() || !form.department.trim()) return 'Add both university and department.';
    try {
      const url = new URL(form.faculty_page_url.trim());
      if (!['http:', 'https:'].includes(url.protocol)) return 'Faculty page URL must start with http or https.';
    } catch {
      return 'Enter a valid faculty page URL.';
    }
    return '';
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const validationError = validate();
    if (validationError) return setError(validationError);
    setSubmitting(true);
    setError('');
    try {
      await submitRecommendation({
        university: form.university.trim(),
        department: form.department.trim(),
        faculty_page_url: form.faculty_page_url.trim(),
      });
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not submit recommendation.');
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div className="page narrow">
        <div className="card" style={{ marginTop: 40 }}>
          <div className="badge">Submitted</div>
          <h2>Thanks for the recommendation.</h2>
          <p className="muted">The university and department will be reviewed before any new scan is published.</p>
          <button className="button primary" style={{ marginTop: 18 }} onClick={() => { setForm(emptyForm); setSubmitted(false); }}>Make another request</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page narrow">
      <div style={{ marginBottom: 24 }}>
        <h2>Recommend a University or Department</h2>
        <p className="muted">Tell us what faculty directory should be considered next.</p>
      </div>
      <form className="card form" onSubmit={submit}>
        <label className="label">University<input className="input" value={form.university} onChange={e => setForm(f => ({ ...f, university: e.target.value }))} placeholder="University name" required /></label>
        <label className="label">Department<input className="input" value={form.department} onChange={e => setForm(f => ({ ...f, department: e.target.value }))} placeholder="Computer Science" required /></label>
        <label className="label">Faculty Page URL<input className="input" type="url" value={form.faculty_page_url} onChange={e => setForm(f => ({ ...f, faculty_page_url: e.target.value }))} placeholder="https://example.edu/cs/faculty" required /></label>
        {error && <div className="error">{error}</div>}
        <button className="button primary" type="submit" disabled={submitting}>{submitting ? 'Submitting…' : 'Submit recommendation →'}</button>
      </form>
    </div>
  );
}
