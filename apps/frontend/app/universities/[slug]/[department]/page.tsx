'use client';

import Link from 'next/link';
import { use, useEffect, useState } from 'react';
import { getUniversitiesOverview, listProfessors, getUserState, patchUserState } from '@/lib/api';
import { localStore } from '@/lib/local-store';
import { slugify } from '@/lib/slug';
import { ProfessorCard } from '@/components/ProfessorCard';
import { LoginModal } from '@/components/LoginModal';
import { ProfessorListSkeleton } from '@/components/Skeleton';
import type { ProfessorSummary } from '@/lib/types';

export default function DepartmentPage({ params: paramsPromise }: { params: Promise<{ slug: string; department: string }> }) {
  const params = use(paramsPromise);
  const [names, setNames] = useState<{ university: string; department: string } | null>(null);
  const [professors, setProfessors] = useState<ProfessorSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notFound, setNotFound] = useState(false);
  const [saved, setSaved] = useState<number[]>([]);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);

  useEffect(() => {
    setSaved(localStore.getSaved());
    setIsLoggedIn(!!localStore.getUser());
    getUserState().then(state => {
      setIsLoggedIn(true);
      if (state.saved_professor_ids) { localStore.setSaved(state.saved_professor_ids); setSaved(state.saved_professor_ids); }
    }).catch(() => undefined);

    getUniversitiesOverview()
      .then(r => {
        const match = r.groups.find(g => slugify(g.university) === params.slug && slugify(g.department) === params.department);
        if (!match) { setNotFound(true); setLoading(false); return null; }
        setNames({ university: match.university, department: match.department });
        document.title = `${match.department} – ${match.university} | ProfMatch`;
        return listProfessors({ university: [match.university], department: [match.department], sort: 'name-asc', limit: 100 });
      })
      .then(r => {
        if (!r) return;
        setProfessors(r.professors);
        setTotal(r.total);
      })
      .catch(e => setError(e.message || 'Could not load this department.'))
      .finally(() => setLoading(false));
  }, [params.slug, params.department]);

  const toggleSave = (id: number) => {
    if (!isLoggedIn) { setShowLoginModal(true); return; }
    const next = saved.includes(id) ? saved.filter(x => x !== id) : [...saved, id];
    setSaved(next); localStore.setSaved(next); patchUserState({ saved_professor_ids: next }).catch(() => undefined);
  };

  if (notFound) {
    return (
      <div className="page narrow">
        <div className="card soft" style={{ marginTop: 32, textAlign: 'center', padding: 32 }}>
          <h3>Department not found.</h3>
          <p className="muted" style={{ margin: '8px 0 14px' }}>It may not be indexed yet. You can request it for import.</p>
          <div className="row center">
            <Link className="button secondary" href={`/universities/${params.slug}`}>Back to university</Link>
            <Link className="button primary" href="/recommend">Request a department</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page narrow">
      <nav className="muted small-text" style={{ marginTop: 26 }} aria-label="Breadcrumb">
        <Link className="accent" href="/universities">Universities</Link> /{' '}
        <Link className="accent" href={`/universities/${params.slug}`}>{names?.university || '…'}</Link> / {names?.department || '…'}
      </nav>
      <div style={{ margin: '10px 0 18px' }}>
        <h1 style={{ fontSize: 30, margin: 0 }}>{names ? `${names.department}` : 'Department'}</h1>
        {names && <p className="muted" style={{ marginTop: 6 }}>{names.university} · {total} professors indexed</p>}
      </div>

      {error && <div className="error">{error}</div>}
      <div className="cards list" style={{ padding: 0 }}>
        {loading && <ProfessorListSkeleton count={3} />}
        {professors.map(p => (
          <ProfessorCard key={p.id} professor={p} saved={saved.includes(p.id)} onSave={() => toggleSave(p.id)} from={`/universities/${params.slug}/${params.department}`} />
        ))}
      </div>

      <LoginModal isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} message="Log in to save professors to your shortlist." />
    </div>
  );
}
