'use client';

import Link from 'next/link';
import { use, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { getProfessor, patchUserState } from '@/lib/api';
import { TagList, Signal, ConfidenceChip, cleanTitle, Avatar } from '@/components/ProfessorCard';
import { Icon } from '@/components/Icon';
import { Toast } from '@/components/Toast';
import { LoginModal } from '@/components/LoginModal';
import { ReportIssueModal } from '@/components/ReportIssueModal';
import { OutreachDraftModal } from '@/components/OutreachDraftModal';
import { DetailSkeleton } from '@/components/Skeleton';
import { localStore } from '@/lib/local-store';
import { track } from '@/lib/analytics';
import type { GetProfessorResponse, MatchResponse, MatchScore } from '@/lib/types';

export default function ProfessorDetailPage({ params: paramsPromise }: { params: Promise<{ id: string }> }) {
  const params = use(paramsPromise);
  const searchParams = useSearchParams();
  const from = searchParams.get('from') || '/professors';
  const [data, setData] = useState<GetProfessorResponse | null>(null);
  const [tab, setTab] = useState<'overview' | 'papers'>('overview');
  const [error, setError] = useState('');
  
  const [saved, setSaved] = useState<number[]>([]);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [matchData, setMatchData] = useState<MatchScore | null>(null);
  const [compact, setCompact] = useState(false);
  const [toast, setToast] = useState('');
  const [showReportModal, setShowReportModal] = useState(false);
  const [showOutreachModal, setShowOutreachModal] = useState(false);
  const compactRef = useRef(false);

  useEffect(() => {
    getProfessor(params.id).then(setData).catch(e => setError(e.message || 'Could not load professor'));
    track('profile_opened', { professor_id: Number(params.id) });

    // Load state
    const s = localStore.getSaved();
    setSaved(s);
    const user = localStore.getUser();
    setIsLoggedIn(!!user);

    if (user) {
      const matches: MatchResponse | null = localStore.getMatches();
      if (matches) {
        const profMatch = matches.matches.find(m => String(m.professor_id) === String(params.id));
        if (profMatch) setMatchData(profMatch);
      }
    }
  }, [params.id]);

  useEffect(() => {
    const onScroll = () => {
      const y = window.scrollY;
      const next = compactRef.current ? y > 24 : y > 260;
      if (next !== compactRef.current) {
        compactRef.current = next;
        setCompact(next);
      }
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const toggleSave = () => { 
    if (!isLoggedIn) {
      setShowLoginModal(true);
      return;
    }
    const id = Number(params.id);
    const next = saved.includes(id) ? saved.filter(x => x !== id) : [...saved, id];
    if (!saved.includes(id)) track('professor_saved', { professor_id: id, surface: 'detail' });
    setSaved(next);
    localStore.setSaved(next); 
    setToast(saved.includes(id) ? 'Professor removed from saved.' : 'Professor saved.');
    patchUserState({ saved_professor_ids: next }).catch(() => undefined); 
  };

  if (error) return <div className="page"><div className="error">{error}</div></div>;
  if (!data) return <DetailSkeleton />;
  
  const p = data.professor;
  const tags = Array.isArray(p.extra?.tags) ? p.extra?.tags as string[] : [];
  const links = [
    ['Homepage', p.homepage_url], ['Faculty profile', p.faculty_profile_url], ['Google Scholar', p.google_scholar_url], ['DBLP', p.dblp_url],
  ].filter(([, url]) => url);
  const isSaved = saved.includes(p.id);

  return (
    <div className="page narrow">
      <div className={`card sticky-professor-card ${compact ? 'compact' : ''}`}>
        <div className="professor-sticky-toolbar">
          <Link className="accent" href={from}>← Back</Link>
          <div className="row" style={{ gap: 8 }}>
            <button className="button secondary" onClick={() => { if (!isLoggedIn) { setShowLoginModal(true); return; } setShowOutreachModal(true); }}>
              <Icon name="paper" size={13} /> Draft email
            </button>
            <button className="button secondary" onClick={() => { if (!isLoggedIn) { setShowLoginModal(true); return; } setShowReportModal(true); }}>
              Report issue
            </button>
            <button className={`button ${isSaved ? 'saved' : 'secondary'}`} onClick={toggleSave}>
              <Icon name="save" size={13} /> {isSaved ? 'Saved' : 'Save'}
            </button>
          </div>
        </div>

        <div className="professor-sticky-main">
          <Avatar name={p.name} photoUrl={p.photo_url} large={true} />
          <div className="professor-sticky-copy">
            <h2>{p.name}</h2>
            <p className="muted professor-designation">{cleanTitle(p.title)} · {p.department}</p>
            <p className="muted professor-university">{p.university}</p>
            {p.email && <p className="professor-email"><a className="accent" href={`mailto:${p.email}`}>{p.email}</a></p>}
          </div>
          <div className="stat professor-paper-stat">
            <strong>{data.publications.length}</strong>
            <span>papers</span>
          </div>
        </div>

        <div className="professor-sticky-extra">
          <TagList tags={tags} max={12} />
          <div className="signals" style={{ marginTop: 24 }}>
            <Signal status={p.recruiting_signal} />
            <ConfidenceChip confidence={p.source_confidence} />
          </div>
          <div className="actions">{links.map(([label, url]) => <a key={label} className="button secondary" href={url as string} target="_blank" rel="noreferrer">{label}</a>)}</div>
        </div>
      </div>

      {/* Match Insight Banner */}
      {!isLoggedIn ? (
        <div className="card soft" style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <p className="muted">Want to see if this professor is a good fit for your research?</p>
          <a className="button primary" href="/signin">Log in to view match score</a>
        </div>
      ) : matchData ? (
        <div className="card soft" style={{ marginTop: 16, borderColor: 'var(--accent)' }}>
          <div className="row between" style={{ marginBottom: 12 }}>
            <h3 style={{ color: 'var(--accent)', margin: 0 }}>✨ {Math.round((matchData.llm_rerank_score ?? matchData.total_score) * 100)}% Match</h3>
          </div>
          <p style={{ lineHeight: 1.6 }}>{matchData.llm_rerank_reason || matchData.explanation}</p>
          
          {matchData.evidence.publications && matchData.evidence.publications.length > 0 && (
            <div className="paper-list" style={{ marginTop: 16 }}>
              <p className="small-text muted"><b>Relevant papers for your profile</b></p>
              {matchData.evidence.publications.slice(0, 3).map(pub => (
                <div className="paper-mini" key={pub.id || pub.title}>
                  <div><b>{pub.url ? <a href={pub.url} target="_blank" rel="noreferrer">{pub.title}</a> : pub.title}</b>{pub.year ? ` (${pub.year})` : ''}</div>
                  {pub.abstract_snippet && <p className="muted small-text" style={{ marginTop: 4 }}>{pub.abstract_snippet}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}

      <div className="tabs">{(['overview', 'papers'] as const).map(t => <button key={t} className={`tab ${tab === t ? 'active' : ''}`} onClick={() => setTab(t)}>{t[0].toUpperCase() + t.slice(1)}</button>)}</div>
      
      {tab === 'overview' && (
        <div className="card">
          <div className="row between" style={{ alignItems: 'baseline' }}>
            <h3>Research summary</h3>
            <span className="t-label">AI summary · generated from public sources</span>
          </div>
          <p className="summary" style={{ display: 'block', WebkitLineClamp: 'unset', marginTop: 10, lineHeight: 1.6 }}>{p.research_summary || p.research_text || 'Research summary unavailable.'}</p>
          <p className="muted small-text" style={{ marginTop: 10 }}>
            Summarized from the public faculty profile, personal/lab pages, and recent publications. It can lag behind the professor&apos;s newest work — verify against the source links above before outreach.
          </p>
          <div className="signals" style={{ marginTop: 18 }}>
            <span className="signal"><i />Updated {new Date(p.updated_at).toLocaleDateString()}</span>
            {(p.extra?.research_source_url || p.extra?.bio_source_url) && (
              <a className="signal" href={(p.extra?.research_source_url || p.extra?.bio_source_url) as string} target="_blank" rel="noreferrer"><i />Profile text source</a>
            )}
            {p.photo_source_url && <span className="signal"><i />Photo source-backed</span>}
          </div>
        </div>
      )}

      {tab === 'papers' && (
        <div className="card">
          <h3>Recent publications</h3>
          {data.publications.length === 0 && (
            <p className="muted" style={{ marginTop: 10 }}>No reliably matched publications yet. Check the homepage or Google Scholar links above for the professor&apos;s own list.</p>
          )}
          {data.publications.map(pub => (
            <div key={pub.id} style={{ padding: '16px 0', borderBottom: '1px solid var(--border)' }}>
              <div className="row between" style={{ gap: 12, alignItems: 'baseline', flexWrap: 'nowrap' }}>
                <b>{pub.url ? <a className="accent" href={pub.url} target="_blank" rel="noreferrer">{pub.title}</a> : pub.title}</b>
                <ConfidenceChip confidence={pub.match_confidence} kind="Author-match" />
              </div>
              <p className="muted small-text" style={{ marginTop: 4 }}>{pub.venue || 'Unknown venue'} · {pub.year || 'n.d.'} · {pub.source}</p>
              {pub.abstract && <p className="muted" style={{ marginTop: 8, lineHeight: 1.5 }}>{pub.abstract}</p>}
            </div>
          ))}
        </div>
      )}

      <Toast message={toast} onClose={() => setToast('')} />
      <ReportIssueModal isOpen={showReportModal} onClose={() => setShowReportModal(false)} professorId={Number(params.id)} onSubmitted={setToast} />
      <OutreachDraftModal isOpen={showOutreachModal} onClose={() => setShowOutreachModal(false)} professorId={Number(params.id)} professorName={p.name} onToast={setToast} />
      <LoginModal
        isOpen={showLoginModal} 
        onClose={() => setShowLoginModal(false)} 
        message="Log in to save this professor and track your outreach progress." 
      />
    </div>
  );
}
