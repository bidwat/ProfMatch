'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { Button, Chip } from '@heroui/react';
import { getProfessor, getUserState } from '@/lib/api';
import { localStore } from '@/lib/local-store';
import { ConfidenceChip, Signal, cleanTitle } from '@/components/ProfessorCard';
import type { GetProfessorResponse, MatchResponse } from '@/lib/types';

const MAX_COMPARE = 4;

export default function ComparePage() {
  const [rows, setRows] = useState<GetProfessorResponse[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [loading, setLoading] = useState(true);
  const [matches, setMatches] = useState<MatchResponse | null>(null);

  useEffect(() => {
    setMatches(localStore.getMatches());
    getUserState()
      .then(state => Promise.all((state.saved_professor_ids || []).map(id => getProfessor(id).catch(() => null))))
      .then(loaded => {
        const ok = (loaded || []).filter(Boolean) as GetProfessorResponse[];
        setRows(ok);
        setSelected(ok.slice(0, Math.min(3, ok.length)).map(r => r.professor.id));
      })
      .finally(() => setLoading(false));
  }, []);

  const toggle = (id: number) => {
    setSelected(current => current.includes(id)
      ? current.filter(x => x !== id)
      : current.length >= MAX_COMPARE ? current : [...current, id]);
  };

  const chosen = useMemo(() => rows.filter(r => selected.includes(r.professor.id)), [rows, selected]);
  const matchFor = (id: number) => {
    const match = matches?.matches.find(m => m.professor_id === id);
    if (!match) return null;
    return Math.round((match.llm_rerank_score ?? match.total_score) * 100);
  };

  return (
    <div className="page">
      <div className="topbar">
        <h2 style={{ margin: 0 }}>Compare professors</h2>
        <p className="muted">Pick two to four saved professors and compare research fit, evidence, and contact signals side by side.</p>
      </div>

      {loading && <div className="card soft" style={{ margin: 24 }}>Loading saved professors…</div>}

      {!loading && rows.length === 0 && (
        <div className="card soft" style={{ margin: 24, textAlign: 'center', padding: 36 }}>
          <h3>No saved professors yet.</h3>
          <p className="muted" style={{ margin: '8px 0 16px' }}>Save professors you want to compare, contact, or track.</p>
          <Link className="button primary" href="/professors">Search professors</Link>
        </div>
      )}

      {!loading && rows.length > 0 && (
        <div style={{ padding: '18px 24px 50px', display: 'grid', gap: 16 }}>
          <div className="row" style={{ gap: 8 }} aria-label="Choose professors to compare">
            {rows.map(({ professor }) => (
              <Button
                key={professor.id}
                size="sm"
                variant={selected.includes(professor.id) ? 'primary' : 'outline'}
                onPress={() => toggle(professor.id)}
                isDisabled={!selected.includes(professor.id) && selected.length >= MAX_COMPARE}
              >
                {professor.name}
              </Button>
            ))}
          </div>

          {chosen.length >= 2 ? (
            <div style={{ overflowX: 'auto' }}>
              <table className="compare-table">
                <thead>
                  <tr>
                    <th scope="col">Field</th>
                    {chosen.map(({ professor }) => (
                      <th scope="col" key={professor.id}>
                        <Link className="accent" href={`/professors/${professor.id}?from=/compare`}>{professor.name}</Link>
                        <div className="muted small-text" style={{ fontWeight: 400 }}>{cleanTitle(professor.title)}</div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr><th scope="row">Research fit</th>{chosen.map(({ professor }) => <td key={professor.id}>{matchFor(professor.id) !== null ? <strong>{matchFor(professor.id)}%</strong> : <span className="muted">Run matches first</span>}</td>)}</tr>
                  <tr><th scope="row">University</th>{chosen.map(({ professor }) => <td key={professor.id}>{professor.university}</td>)}</tr>
                  <tr><th scope="row">Department</th>{chosen.map(({ professor }) => <td key={professor.id}>{professor.department}</td>)}</tr>
                  <tr><th scope="row">Recruiting</th>{chosen.map(({ professor }) => <td key={professor.id}><Signal status={professor.recruiting_signal} /></td>)}</tr>
                  <tr><th scope="row">Source confidence</th>{chosen.map(({ professor }) => <td key={professor.id}><ConfidenceChip confidence={professor.source_confidence} /></td>)}</tr>
                  <tr><th scope="row">Publications indexed</th>{chosen.map(row => <td key={row.professor.id}>{row.publications.length}</td>)}</tr>
                  <tr><th scope="row">Research tags</th>{chosen.map(({ professor }) => (
                    <td key={professor.id}>
                      <div className="row" style={{ gap: 4 }}>
                        {(Array.isArray(professor.extra?.tags) ? (professor.extra!.tags as string[]) : []).slice(0, 5).map(tag => <Chip key={tag} size="sm">{tag}</Chip>)}
                      </div>
                    </td>
                  ))}</tr>
                  <tr><th scope="row">Summary</th>{chosen.map(({ professor }) => <td key={professor.id} className="muted small-text" style={{ maxWidth: 280 }}>{(professor.research_summary || '').slice(0, 220) || '—'}</td>)}</tr>
                </tbody>
              </table>
            </div>
          ) : (
            <div className="card soft">Select at least two professors to compare.</div>
          )}
        </div>
      )}
    </div>
  );
}
