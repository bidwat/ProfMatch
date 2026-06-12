/* eslint-disable @next/next/no-img-element */
import Link from 'next/link';
import { useState } from 'react';
import { Icon } from '@/components/Icon';
import { Toast } from '@/components/Toast';

export function cleanTitle(title?: string | null) {
  if (!title) return 'Faculty';
  return title
    .replace(/ORCID.*?(\d{4}-){3}\d{3}[\dX]/i, '')
    .replace(/CMU Scholars/i, '')
    .trim() || 'Faculty';
}

export function TagList({ tags, max = 5, moreHref }: { tags?: string[]; max?: number; moreHref?: string }) {
  const allTags = tags || [];
  const visible = allTags.slice(0, max);
  const hiddenCount = Math.max(0, allTags.length - visible.length);
  return (
    <div className="tags">
      {visible.map(tag => <span className="tag" key={tag}>{tag}</span>)}
      {hiddenCount > 0 && moreHref && <Link className="tag tag-more" href={moreHref}>+{hiddenCount}</Link>}
    </div>
  );
}

export function Signal({ status }: { status: string }) {
  const cls = status === 'positive' ? 'good' : status === 'negative' ? 'bad' : 'warn';
  const label = status === 'positive' ? 'Recruiting evidence' : status === 'negative' ? 'Not recruiting' : 'Recruiting unknown';
  return <span className={`signal ${cls}`}><i />{label}</span>;
}

export function confidenceBand(confidence?: number | null) {
  if (typeof confidence !== 'number') return null;
  if (confidence >= 0.85) return { label: 'High confidence', tone: 'olive' };
  if (confidence >= 0.65) return { label: 'Medium confidence', tone: 'gold' };
  return { label: 'Low confidence', tone: 'peach' };
}

export function ConfidenceChip({ confidence, kind = 'Source' }: { confidence?: number | null; kind?: string }) {
  const band = confidenceBand(confidence);
  if (!band) return null;
  return (
    <span className={`confidence-chip tone-${band.tone}`} title={`${kind} confidence ${Math.round((confidence as number) * 100)}%`}>
      {band.label}
    </span>
  );
}

interface ProfessorCardProps {
  professor: {
    id: number | string;
    name: string;
    title?: string | null;
    university: string;
    department: string;
    photo_url?: string | null;
    tags?: string[];
    research_summary?: string | null;
    recruiting_signal?: string;
    source_confidence?: number;
    publication_count?: number;
  };
  matchData?: {
    score: number;
    reason: string;
    paperCount: number;
    researchScore?: number;
    publicationScore?: number;
    recruitingScore?: number;
    metadataScore?: number;
    outreachAngle?: string | null;
    risks?: string[];
  };
  saved?: boolean;
  onSave?: () => void;
  from?: string;
}

export function ProfessorCard({ professor, matchData, saved, onSave, from }: ProfessorCardProps) {
  const href = `/professors/${professor.id}${from ? `?from=${encodeURIComponent(from)}` : ''}`;
  const [toast, setToast] = useState('');

  function handleSave() {
    onSave?.();
    setToast(saved ? 'Professor removed from saved.' : 'Professor saved.');
  }

  return (
    <>
    <article className={`card professor-card list-row ${matchData ? 'match-row' : ''}`}>
      <div className="card-top">
        <Link className="identity clickable-identity" href={href}>
          <Avatar name={professor.name} photoUrl={professor.photo_url} />
          <div>
            <h3 style={{ fontSize: '18px', marginBottom: 4 }}>{professor.name}</h3>
            <p className="muted small-text">{cleanTitle(professor.title)} · {professor.university}</p>
            <p className="muted small-text">{professor.department}</p>
          </div>
        </Link>
        {matchData ? (
          <div className="score">
            <strong>{Math.round(matchData.score * 100)}%</strong>
            <span>match</span>
          </div>
        ) : (
          <div className="mini-stat">
            <strong>{professor.publication_count || 0}</strong>
            <span>papers indexed</span>
          </div>
        )}
      </div>

      {!matchData && <TagList tags={professor.tags} max={3} moreHref={href} />}
      
      {matchData ? (
        <div className="match-reason" style={{ marginTop: 12 }}>
          <p><b>Why matched · </b>{matchData.reason}</p>
          <div className="match-reason-meta">
            <span>{matchData.paperCount} relevant papers matched</span>
          </div>
        </div>
      ) : (
        <p className="summary" style={{ marginTop: 12 }}>
          {professor.research_summary || 'Research summary unavailable.'}
        </p>
      )}

      <div className="card-footer-actions" style={{ marginTop: 16 }}>
        <div className="signals card-footer-signals">
          {matchData ? (
            <>
              {typeof matchData.recruitingScore === 'number' && <span className="signal"><i />Recruiting {Math.round(matchData.recruitingScore * 100)}%</span>}
              {typeof matchData.metadataScore === 'number' && <span className="signal"><i />Confidence {Math.round(matchData.metadataScore * 100)}%</span>}
            </>
          ) : professor.recruiting_signal ? (
            <>
              <Signal status={professor.recruiting_signal} />
              <ConfidenceChip confidence={professor.source_confidence} />
            </>
          ) : null}
        </div>
        <div className="actions">
          <Link className="button secondary" href={href}><Icon name="eye" size={13} /> Expand</Link>
          {onSave && <button className={`button primary ${saved ? 'saved' : ''}`} onClick={handleSave}><Icon name="save" size={13} /> {saved ? 'Saved' : 'Save'}</button>}
        </div>
      </div>
    </article>
    <Toast message={toast} onClose={() => setToast('')} />
    </>
  );
}

export function Avatar({ name, photoUrl, large }: { name: string; photoUrl?: string | null, large?: boolean }) {
  const className = `avatar ${photoUrl ? 'photo' : ''} ${large ? 'profile-avatar' : ''}`;
  if (photoUrl) return <img className={className} src={photoUrl} alt={`${name} profile photo`} loading="lazy" referrerPolicy="no-referrer" />;
  return <div className={className}>{initials(name)}</div>;
}

function initials(name: string) {
  const parts = name.trim().split(/\s+/);
  return `${parts[0]?.[0] || 'P'}${parts.at(-1)?.[0] || ''}`.slice(0, 2).toUpperCase();
}
