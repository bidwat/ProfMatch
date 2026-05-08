'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { findMatches, getUserState, patchUserState } from '@/lib/api';
import { localStore } from '@/lib/local-store';
import type { StudentProfile } from '@/lib/types';

const fields = ['Artificial Intelligence', 'Machine Learning', 'Computer Vision', 'Natural Language Processing', 'Robotics', 'Human-Computer Interaction', 'Systems', 'Security', 'Databases', 'Programming Languages', 'Theory', 'Graphics'];

export default function IntakePage() {
  const router = useRouter();
  const user = typeof window !== 'undefined' ? localStore.getUser() : null;
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState({
    name: user?.name || '', background: '', interests: [] as string[], other: '', target_degree: 'PhD', departments: 'Computer Science', universities: '', locations: '', rerank: false,
  });
  useEffect(() => {
    getUserState().then(state => {
      if (!state.student_profile) return;
      const profile = state.student_profile;
      localStore.setProfile(profile);
      setData(d => ({
        ...d,
        name: profile.name || d.name,
        background: profile.background || '',
        other: profile.research_interests || '',
        target_degree: profile.target_degree || 'PhD',
        departments: profile.preferred_departments?.join(', ') || 'Computer Science',
        universities: profile.preferred_universities?.join(', ') || '',
        locations: profile.preferred_locations?.join(', ') || '',
        rerank: profile.rerank || false,
      }));
    }).catch(() => undefined);
  }, []);

  const progress = ((step + 1) / 4) * 100;
  const toggle = (field: string) => setData(d => ({ ...d, interests: d.interests.includes(field) ? d.interests.filter(x => x !== field) : [...d.interests, field] }));

  async function submit() {
    const research_interests = [...data.interests, data.other].filter(Boolean).join(', ');
    if (!research_interests.trim()) { setError('Add at least one research interest.'); return; }
    const profile: StudentProfile = {
      name: data.name || user?.name || 'Applicant',
      background: data.background,
      research_interests,
      target_degree: data.target_degree,
      preferred_departments: split(data.departments),
      preferred_universities: split(data.universities),
      preferred_locations: split(data.locations),
      limit: 10,
      shortlist_limit: 50,
      rerank: data.rerank,
      include_publication_evidence: true,
      max_abstracts_per_professor: 10,
    };
    setLoading(true); setError('');
    try {
      const matches = await findMatches(profile);
      localStore.setProfile(profile);
      localStore.setMatches(matches);
      patchUserState({ student_profile: profile, last_match_response: matches }).catch(() => undefined);
      router.push('/match');
    } catch (e: any) {
      setError(e.message || 'Could not run matching. Is the backend running?');
    } finally { setLoading(false); }
  }

  return (
    <div className="page narrow">
      <div className="card">
        <div className="row between"><div><p className="muted small-text">Step {step + 1} of 4</p><h2>{['Background', 'Research interests', 'Goals', 'Preferences'][step]}</h2></div><button className="ghost" onClick={() => router.push('/professors')}>Skip →</button></div>
        <div className="progress" style={{ marginBottom: 24 }}><span style={{ width: `${progress}%` }} /></div>
        {step === 0 && <div className="form"><label className="label">Name<input className="input" value={data.name} onChange={e => setData(d => ({ ...d, name: e.target.value }))} /></label><label className="label">Academic/research background<textarea className="textarea" placeholder="Degree, projects, publications, lab or industry experience..." value={data.background} onChange={e => setData(d => ({ ...d, background: e.target.value }))} /></label></div>}
        {step === 1 && <div><p className="muted" style={{ marginBottom: 12 }}>Choose broad fields. The matcher also uses your free-text keywords.</p><div className="tags">{fields.map(f => <button type="button" key={f} className={`tag ${data.interests.includes(f) ? 'button primary' : ''}`} onClick={() => toggle(f)}>{f}</button>)}</div><label className="label" style={{ marginTop: 16 }}>Specific interests<input className="input" placeholder="e.g. reliable distributed systems for ML inference" value={data.other} onChange={e => setData(d => ({ ...d, other: e.target.value }))} /></label></div>}
        {step === 2 && <div className="form-grid"><label className="label">Target degree<select className="select" value={data.target_degree} onChange={e => setData(d => ({ ...d, target_degree: e.target.value }))}><option>PhD</option><option>MS thesis</option><option>MS coursework</option><option>Research internship</option></select></label><label className="label">Preferred departments<input className="input" value={data.departments} onChange={e => setData(d => ({ ...d, departments: e.target.value }))} /></label></div>}
        {step === 3 && <div className="form"><label className="label">Preferred universities, optional<input className="input" placeholder="Stanford, Cornell, UIUC" value={data.universities} onChange={e => setData(d => ({ ...d, universities: e.target.value }))} /></label><label className="label">Preferred locations, optional<input className="input" placeholder="California, Texas, New York" value={data.locations} onChange={e => setData(d => ({ ...d, locations: e.target.value }))} /></label><label className="row"><input type="checkbox" checked={data.rerank} onChange={e => setData(d => ({ ...d, rerank: e.target.checked }))} /> Optional LLM rerank with free OpenRouter model</label><p className="muted small-text">Leave rerank off for fast local-only FTS5 + metadata scoring.</p></div>}
        {error && <div className="error" style={{ marginTop: 16 }}>{error}</div>}
        <div className="row" style={{ marginTop: 24 }}><button className="button secondary" disabled={step === 0 || loading} onClick={() => setStep(s => s - 1)}>← Back</button><div style={{ flex: 1 }} />{step < 3 ? <button className="button primary" onClick={() => setStep(s => s + 1)}>Continue →</button> : <button className="button primary" disabled={loading} onClick={submit}>{loading ? 'Matching…' : 'Find my professors →'}</button>}</div>
      </div>
    </div>
  );
}

function split(value: string) { return value.split(',').map(v => v.trim()).filter(Boolean); }
