'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { Button, Card } from '@heroui/react';
import { getProfessor, getUserState, patchUserState } from '@/lib/api';
import { localStore } from '@/lib/local-store';
import { track } from '@/lib/analytics';
import { Toast } from '@/components/Toast';
import type { GetProfessorResponse } from '@/lib/types';

// Default stages per spec §16.4 (professor-centered application workflow).
const STAGES = [
  'Discovered', 'Interested', 'Reading papers', 'Email drafted', 'Contacted',
  'Follow-up needed', 'Positive reply', 'Negative reply', 'No response',
  'Applying', 'Applied', 'Interview', 'Accepted', 'Rejected', 'Archived',
] as const;

interface BoardRow {
  professor_id: number;
  stage: string;
  note?: string;
  updated_at?: string;
}

export default function BoardPage() {
  const [rows, setRows] = useState<BoardRow[]>([]);
  const [savedIds, setSavedIds] = useState<number[]>([]);
  const [professors, setProfessors] = useState<Record<number, GetProfessorResponse['professor']>>({});
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState('');

  useEffect(() => {
    getUserState()
      .then(state => {
        const tracker = (state.tracker_rows || []).filter((row: any) => typeof row?.professor_id === 'number') as BoardRow[];
        setRows(tracker);
        setSavedIds(state.saved_professor_ids || []);
        const ids = Array.from(new Set([...tracker.map(r => r.professor_id), ...(state.saved_professor_ids || [])]));
        return Promise.all(ids.map(id => getProfessor(id).catch(() => null)));
      })
      .then(loaded => {
        const byId: Record<number, GetProfessorResponse['professor']> = {};
        for (const item of (loaded || []).filter(Boolean) as GetProfessorResponse[]) byId[item.professor.id] = item.professor;
        setProfessors(byId);
      })
      .finally(() => setLoading(false));
  }, []);

  const persist = (next: BoardRow[]) => {
    setRows(next);
    patchUserState({ tracker_rows: next as any }).catch(() => setToast('Could not save the board. Changes may not persist.'));
  };

  const setStage = (professorId: number, stage: string) => {
    const from = rows.find(row => row.professor_id === professorId)?.stage;
    persist(rows.map(row => row.professor_id === professorId ? { ...row, stage, updated_at: new Date().toISOString() } : row));
    track('board_card_moved', { from_stage: from || null, to_stage: stage });
    setToast(`Moved to ${stage}.`);
  };

  const setNote = (professorId: number, note: string) => {
    persist(rows.map(row => row.professor_id === professorId ? { ...row, note } : row));
  };

  const removeCard = (professorId: number) => {
    persist(rows.filter(row => row.professor_id !== professorId));
  };

  const addSaved = () => {
    const existing = new Set(rows.map(r => r.professor_id));
    const additions = savedIds.filter(id => !existing.has(id)).map(id => ({ professor_id: id, stage: 'Discovered', updated_at: new Date().toISOString() }));
    if (additions.length === 0) { setToast('All saved professors are already on the board.'); return; }
    persist([...rows, ...additions]);
    setToast(`Added ${additions.length} saved professor${additions.length === 1 ? '' : 's'}.`);
  };

  const columns = useMemo(() => {
    const grouped = new Map<string, BoardRow[]>();
    for (const row of rows) {
      const stage = STAGES.includes(row.stage as any) ? row.stage : 'Discovered';
      grouped.set(stage, [...(grouped.get(stage) || []), row]);
    }
    return STAGES.filter(stage => grouped.has(stage)).map(stage => ({ stage, cards: grouped.get(stage)! }));
  }, [rows]);

  return (
    <div className="page">
      <div className="topbar">
        <div className="row between">
          <div>
            <h2 style={{ margin: 0 }}>Application board</h2>
            <p className="muted">Track each professor from discovery to outreach to application. Stages save to your account.</p>
          </div>
          <Button variant="secondary" onPress={addSaved}>Add saved professors</Button>
        </div>
      </div>

      {loading && <div className="card soft" style={{ margin: 24 }}>Loading your board…</div>}

      {!loading && rows.length === 0 && (
        <div className="card soft" style={{ margin: 24, textAlign: 'center', padding: 36 }}>
          <h3>Start your application board</h3>
          <p className="muted" style={{ margin: '8px 0 16px' }}>Add saved professors to track reading, outreach, follow-ups, and applications.</p>
          <div className="row center">
            <Button onPress={addSaved}>Add saved professors</Button>
            <Link className="button secondary" href="/professors">Search professors</Link>
          </div>
        </div>
      )}

      {!loading && columns.length > 0 && (
        <div className="board-columns">
          {columns.map(({ stage, cards }) => (
            <section key={stage} className="board-column" aria-label={`${stage} column`}>
              <header className="board-column-header"><strong>{stage}</strong><span className="home-count-chip">{cards.length}</span></header>
              {cards.map(card => {
                const professor = professors[card.professor_id];
                return (
                  <Card key={card.professor_id} className="board-card">
                    <Link className="accent" href={`/professors/${card.professor_id}?from=/board`} style={{ fontWeight: 600 }}>
                      {professor?.name || `Professor #${card.professor_id}`}
                    </Link>
                    {professor && <p className="muted small-text" style={{ margin: '2px 0 0' }}>{professor.university}</p>}
                    <label className="label small-text" style={{ marginTop: 10 }}>
                      Stage
                      <select className="select" value={card.stage} onChange={e => setStage(card.professor_id, e.target.value)}>
                        {STAGES.map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </label>
                    <label className="label small-text" style={{ marginTop: 8 }}>
                      Notes
                      <textarea className="textarea" style={{ minHeight: 56 }} value={card.note || ''} placeholder="Papers read, contact details, next step…" onChange={e => setNote(card.professor_id, e.target.value)} onBlur={() => persist(rows)} />
                    </label>
                    <button className="ghost small" style={{ marginTop: 8 }} onClick={() => removeCard(card.professor_id)}>Remove from board</button>
                  </Card>
                );
              })}
            </section>
          ))}
        </div>
      )}

      <Toast message={toast} onClose={() => setToast('')} />
    </div>
  );
}
