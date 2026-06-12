'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { getProfessor, getUserState, patchUserState } from '@/lib/api';
import { ProfessorCard } from '@/components/ProfessorCard';
import { FilterSortBar, MultiSelectFilter, SearchBox, SingleSelectFilter, SortSelect } from '@/components/Filters';
import { Icon } from '@/components/Icon';
import { ProfessorListSkeleton } from '@/components/Skeleton';
import { localStore } from '@/lib/local-store';
import type { GetProfessorResponse } from '@/lib/types';

export default function SavedPage() {
  const [rows, setRows] = useState<GetProfessorResponse[]>([]);
  const [ids, setIds] = useState<number[]>([]);
  const [q, setQ] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [universities, setUniversities] = useState<string[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [recruiting, setRecruiting] = useState('');
  const [sort, setSort] = useState('recent-desc');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  useEffect(() => {
    const load = (saved: number[]) => {
      setLoading(true);
      setLoadError('');
      setIds(saved);
      if (saved.length === 0) { setRows([]); setLoading(false); return; }
      Promise.all(saved.map(id => getProfessor(id).catch(() => null)))
        .then(r => {
          const loaded = r.filter(Boolean) as GetProfessorResponse[];
          setRows(loaded);
          if (loaded.length < saved.length) setLoadError('Some saved professors could not be loaded.');
        })
        .finally(() => setLoading(false));
    };
    load(localStore.getSaved());
    getUserState().then(state => { localStore.setSaved(state.saved_professor_ids); load(state.saved_professor_ids); }).catch(() => undefined);
  }, []);

  const remove = (id: number) => {
    const next = ids.filter(x => x !== id);
    setIds(next); localStore.setSaved(next); patchUserState({ saved_professor_ids: next }).catch(() => undefined);
    setRows(r => r.filter(x => x.professor.id !== id));
  };

  const facets = useMemo(() => ({
    tags: Array.from(new Set(rows.flatMap(r => (r.professor.extra?.tags as string[]) || []))).sort(),
    universities: Array.from(new Set(rows.map(r => r.professor.university))).sort(),
    departments: Array.from(new Set(rows.map(r => r.professor.department).filter(Boolean))).sort(),
  }), [rows]);

  const visibleRows = useMemo(() => {
    const indexed = rows.map(row => ({ row, savedIndex: ids.indexOf(row.professor.id) }));
    const filtered = indexed.filter(({ row }) => {
      const p = row.professor;
      const rowTags = (p.extra?.tags as string[]) || [];
      const haystack = [p.name, p.title, p.university, p.department, p.research_summary, ...rowTags].filter(Boolean).join(' ').toLowerCase();
      return (!q || haystack.includes(q.toLowerCase()))
        && (tags.length === 0 || tags.every(tag => rowTags.includes(tag)))
        && (universities.length === 0 || universities.includes(p.university))
        && (departments.length === 0 || departments.includes(p.department))
        && (!recruiting || p.recruiting_signal === recruiting);
    });
    filtered.sort((a, b) => {
      const dir = sort.endsWith('desc') ? -1 : 1;
      if (sort.startsWith('recent')) return dir * (a.savedIndex - b.savedIndex);
      if (sort.startsWith('university')) return dir * a.row.professor.university.localeCompare(b.row.professor.university);
      if (sort.startsWith('recruiting')) return dir * a.row.professor.recruiting_signal.localeCompare(b.row.professor.recruiting_signal);
      return dir * a.row.professor.name.localeCompare(b.row.professor.name);
    });
    return filtered.map(x => x.row);
  }, [rows, ids, q, tags, universities, departments, recruiting, sort]);

  return (
    <div>
      <div className="topbar filter-bar">
        <div className="row between">
          <div><h2 style={{ margin: 0 }}>Saved</h2><p className="muted">{ids.length} saved professors · {visibleRows.length} visible</p></div>
          <div className="row" style={{ gap: 8 }}>
            <Link className="button secondary" href="/compare">Compare</Link>
            <Link className="button secondary" href="/board">Open board</Link>
            <Link className="button primary" href="/professors"><Icon name="compass" size={14} />Discover more</Link>
          </div>
        </div>
        <FilterSortBar
          activeFilters={[
            ...tags.map(value => ({ group: 'tags', value, onRemove: () => setTags(tags.filter(v => v !== value)) })),
            ...universities.map(value => ({ group: 'university', value, onRemove: () => setUniversities(universities.filter(v => v !== value)) })),
            ...departments.map(value => ({ group: 'department', value, onRemove: () => setDepartments(departments.filter(v => v !== value)) })),
            ...(recruiting ? [{ group: 'recruiting', value: recruiting === 'positive' ? 'Recruiting' : recruiting === 'negative' ? 'Not recruiting' : 'Unknown', onRemove: () => setRecruiting('') }] : []),
          ]}
          onClearAll={() => { setTags([]); setUniversities([]); setDepartments([]); setRecruiting(''); }}
        >
          <SearchBox value={q} onChange={setQ} placeholder="Search saved professors…" />
          <SortSelect value={sort} onChange={setSort} options={[{ value: 'recent-desc', label: 'Recently saved ↓' }, { value: 'recent-asc', label: 'Recently saved ↑' }, { value: 'name-asc', label: 'Name A–Z' }, { value: 'name-desc', label: 'Name Z–A' }, { value: 'university-asc', label: 'University A–Z' }, { value: 'university-desc', label: 'University Z–A' }, { value: 'recruiting-asc', label: 'Recruiting ↑' }, { value: 'recruiting-desc', label: 'Recruiting ↓' }]} />
          <MultiSelectFilter label="Tags" icon="tag" options={facets.tags} values={tags} onChange={setTags} />
          <MultiSelectFilter label="Universities" icon="building" options={facets.universities} values={universities} onChange={setUniversities} />
          <MultiSelectFilter label="Departments" icon="paper" options={facets.departments} values={departments} onChange={setDepartments} />
          <SingleSelectFilter label="Recruiting" value={recruiting} onChange={setRecruiting} icon="shield" emptyLabel="All statuses" options={[{ value: 'positive', label: 'Recruiting' }, { value: 'negative', label: 'Not recruiting' }, { value: 'unknown', label: 'Unknown' }]} />
        </FilterSortBar>
      </div>
      <div className="cards list">
        {loading && <ProfessorListSkeleton count={3} />}
        {loadError && <div className="notice">{loadError}</div>}
        {!loading && visibleRows.length === 0 ? <div className="card"><p className="muted">{ids.length ? 'No saved professors match these filters.' : 'No saved professors yet. Save professors from Matches or Discover.'}</p></div> : visibleRows.map(({ professor: p, publications }) => (
          <ProfessorCard key={p.id} professor={{ id: p.id, name: p.name, title: p.title, university: p.university, department: p.department, photo_url: p.photo_url, tags: p.extra?.tags as string[] || [], research_summary: p.research_summary, recruiting_signal: p.recruiting_signal, source_confidence: p.source_confidence, publication_count: publications.length }} saved={true} onSave={() => remove(p.id)} from="/saved" />
        ))}
      </div>
    </div>
  );
}
