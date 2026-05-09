'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getProfessor, getUserState } from '@/lib/api';
import { localStore } from '@/lib/local-store';
import { Icon } from '@/components/Icon';
import { Avatar } from '@/components/ProfessorCard';
import { ProfessorCardSkeleton } from '@/components/Skeleton';
import type { LocalUser, MatchResponse, ProfessorSummary, StudentProfile } from '@/lib/types';

function ProfileValue({ value, field }: { value?: string | number | null; field: string }) {
  const text = String(value || '').trim();
  if (!text) return <strong className="missing-profile-value" title={`Update Profile for ${field} field.`}>-</strong>;
  return <strong>{text}</strong>;
}

export default function DashboardPage() {
  const [user, setUser] = useState<LocalUser | null>(null);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [matches, setMatches] = useState<MatchResponse | null>(null);
  const [savedIds, setSavedIds] = useState<number[]>([]);
  const [savedProfessors, setSavedProfessors] = useState<ProfessorSummary[]>([]);

  useEffect(() => {
    setUser(localStore.getUser());
    setProfile(localStore.getProfile());
    setMatches(localStore.getMatches());
    const localSaved = localStore.getSaved();
    setSavedIds(localSaved);

    getUserState().then(state => {
      if (state.student_profile) {
        localStore.setProfile(state.student_profile);
        setProfile(state.student_profile);
        const currentUser = localStore.getUser();
        if (currentUser) {
          const nextUser = { ...currentUser, name: state.student_profile.name || currentUser.name, photo_url: state.student_profile.photo_url || currentUser.photo_url };
          localStore.setUser(nextUser);
          setUser(nextUser);
        }
      }
      if (state.last_match_response) { localStore.setMatches(state.last_match_response); setMatches(state.last_match_response); }
      if (state.saved_professor_ids) { localStore.setSaved(state.saved_professor_ids); setSavedIds(state.saved_professor_ids); }
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (savedIds.length === 0) { setSavedProfessors([]); return; }
    Promise.all(savedIds.slice(0, 3).map(id => getProfessor(id).catch(() => null)))
      .then(responses => setSavedProfessors(responses.filter(Boolean).map(r => {
        const response = r!;
        return {
          id: response.professor.id,
          name: response.professor.name,
          title: response.professor.title,
          university: response.professor.university,
          department: response.professor.department,
          research_summary: response.professor.research_summary,
          recruiting_signal: response.professor.recruiting_signal,
          source_confidence: response.professor.source_confidence,
          publication_count: response.publications.length,
          tags: response.professor.extra?.tags || [],
          photo_url: response.professor.photo_url,
        } as ProfessorSummary;
      })));
  }, [savedIds]);

  const displayName = profile?.name || user?.name || 'Applicant';
  const firstName = displayName.split(' ')[0] || 'Applicant';
  const topMatches = matches?.matches.slice(0, 3) || [];
  const targetDegree = [profile?.target_degree, profile?.target_department].filter(Boolean).join(', ');
  const highestDegree = profile?.highest_degree;
  const background = highestDegree && (highestDegree.degree || highestDegree.field || highestDegree.institution || highestDegree.year)
    ? [
      [highestDegree.degree, highestDegree.field].filter(Boolean).join(' '),
      [highestDegree.institution, highestDegree.year].filter(Boolean).join(' '),
    ].filter(Boolean).join(' · ')
    : '';
  const interestItems = Array.from(new Set([
    ...(profile?.interest_tags || []),
    ...(profile?.research_interests || '').split(/[,;\n]/),
  ].map(item => item.trim()).filter(Boolean)));
  const visibleInterests = interestItems.slice(0, 3);
  const hiddenInterestCount = Math.max(0, interestItems.length - visibleInterests.length);

  return (
    <div className="page">
      <div style={{ marginBottom: 24 }}>
        <h2>Welcome, {firstName}</h2>
        <p className="muted">Review your profile, current matches, and saved professors.</p>
      </div>

      <section className="academic-profile-card" style={{ marginBottom: 20 }}>
        <div className="academic-profile-shell">
          <Avatar name={displayName} photoUrl={profile?.photo_url || user?.photo_url} />
          <div className="academic-profile-content">
            <div className="academic-profile-header">
              <h3>{displayName}</h3>
              <Link className="profile-edit-link" href="/profile"><Icon name="edit" size={11} />Edit profile</Link>
            </div>
            {profile ? (
              <div className="academic-profile-fields">
                <div className="academic-profile-field"><span className="t-label">Target degree</span><ProfileValue value={targetDegree} field="target degree" /></div>
                <div className="academic-profile-field"><span className="t-label">Background</span><ProfileValue value={background} field="academic background" /></div>
                <div className="academic-profile-field interest-field">
                  <span className="t-label">Interests</span>
                  {visibleInterests.length ? (
                    <div className="profile-interest-chips">
                      {visibleInterests.map((interest, index) => <span className={`profile-interest-chip tone-${index % 3}`} key={interest}>{interest}</span>)}
                      {hiddenInterestCount > 0 && <Link className="profile-interest-more" href="/profile#areas-of-interest">+{hiddenInterestCount}</Link>}
                    </div>
                  ) : <strong className="missing-profile-value" title="Update Profile for interests field.">-</strong>}
                </div>
              </div>
            ) : <p className="muted">No academic profile yet. Add one to generate matches.</p>}
          </div>
        </div>
      </section>

      <section className="dashboard-split">
        <div className="card home-panel">
          <div className="home-panel-header">
            <div className="home-panel-title"><Icon name="sparkle" size={14} /><h3>Matches</h3><span className="home-count-chip">{matches?.matches.length || 0} professors</span></div>
            <Link className="home-view-link" href="/match">View all →</Link>
          </div>
          <div className="preview-list">
            {topMatches.length ? topMatches.map(match => (
              <Link className="mini-prof-row" href={`/professors/${match.professor_id}?from=/match`} key={match.professor_id}>
                <Avatar name={match.professor_name} photoUrl={match.photo_url} />
                <span><strong>{match.professor_name}</strong><small>{match.university}</small></span>
                <span className="mini-match-score">{Math.round((match.llm_rerank_score ?? match.total_score) * 100)}%</span>
              </Link>
            )) : <p className="muted">No matches yet. Update your profile to generate matches.</p>}
          </div>
        </div>

        <div className="card home-panel">
          <div className="home-panel-header">
            <div className="home-panel-title saved"><Icon name="bookmark" size={14} /><h3>Saved</h3><span className="home-count-chip saved">{savedIds.length} {savedIds.length === 1 ? 'professor' : 'professors'}</span></div>
            <Link className="home-view-link" href="/saved">View all →</Link>
          </div>
          <div className="preview-list">
            {savedProfessors.length ? savedProfessors.map(professor => (
              <Link className="mini-prof-row" href={`/professors/${professor.id}?from=/saved`} key={professor.id}>
                <Avatar name={professor.name} photoUrl={professor.photo_url} />
                <span><strong>{professor.name}</strong><small>{professor.university} · {professor.publication_count} papers</small></span>
                <span className="mini-saved-chip">Saved</span>
              </Link>
            )) : savedIds.length ? <ProfessorCardSkeleton /> : <p className="muted">No saved professors yet.</p>}
            {savedIds.length < 3 && (
              <p className="save-more-note">Save more professors from <Link href="/match">Matches</Link> or <Link href="/professors">Discover</Link>.</p>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
