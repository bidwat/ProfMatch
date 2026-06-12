'use client';

import { useEffect, useMemo, useState } from 'react';
import { getProfessorFacets, getUserState, listProfessors, patchUserState } from '@/lib/api';
import { track } from '@/lib/analytics';
import { localStore } from '@/lib/local-store';
import type { ProfessorSummary } from '@/lib/types';
import { ProfessorCard } from '@/components/ProfessorCard';
import { LoginModal } from '@/components/LoginModal';
import { ProfessorListSkeleton } from '@/components/Skeleton';
import { FilterSortBar, MultiSelectFilter, SearchBox, SingleSelectFilter, SortSelect } from '@/components/Filters';

function useDebouncedValue(value: string, delay = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

export default function ProfessorsPage() {
  const [professors, setProfessors] = useState<ProfessorSummary[]>([]);
  const [facets, setFacets] = useState({ tags: [] as string[], universities: [] as string[], departments: [] as string[], titles: [] as string[] });
  const [q, setQ] = useState('');
  const debouncedQ = useDebouncedValue(q);
  const [universities, setUniversities] = useState<string[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [recruiting, setRecruiting] = useState('');
  const [sort, setSort] = useState('name-asc');
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [cursorToLoad, setCursorToLoad] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState<number[]>([]);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const limit = 24;

  useEffect(() => {
    // Seed search/filters from URL params (landing search, university and
    // department page cross-links, shared URLs).
    const urlParams = new URLSearchParams(window.location.search);
    const initialQ = urlParams.get('q');
    if (initialQ) setQ(initialQ);
    const initialUniversity = urlParams.get('university');
    if (initialUniversity) setUniversities([initialUniversity]);
    const initialDepartment = urlParams.get('department');
    if (initialDepartment) setDepartments([initialDepartment]);
    const initialTag = urlParams.get('tag');
    if (initialTag) setTags([initialTag]);
    getProfessorFacets().then(setFacets).catch(() => {});
    setSaved(localStore.getSaved());
    setIsLoggedIn(!!localStore.getUser());
    getUserState().then(state => {
      setIsLoggedIn(true);
      if (state.saved_professor_ids) { localStore.setSaved(state.saved_professor_ids); setSaved(state.saved_professor_ids); }
    }).catch(() => undefined);
  }, []);

  useEffect(() => { setNextCursor(null); setCursorToLoad(null); setProfessors([]); }, [debouncedQ, universities, tags, departments, recruiting, sort]);

  useEffect(() => {
    setLoading(true);
    setError('');
    listProfessors({ q: debouncedQ, university: universities, tag: tags, department: departments, recruiting_signal: recruiting, sort, cursor: cursorToLoad || undefined, limit })
      .then(r => {
        setProfessors(current => cursorToLoad ? [...current, ...r.professors] : r.professors);
        setTotal(r.total);
        setNextCursor(r.next_cursor || null);
        if (!cursorToLoad && debouncedQ) {
          track('search_performed', { query_length: debouncedQ.length, results_count: r.total, filters_count: universities.length + tags.length + departments.length + (recruiting ? 1 : 0) });
        }
      })
      .catch(e => setError(e.message || 'Could not load professors'))
      .finally(() => setLoading(false));
  }, [debouncedQ, universities, tags, departments, recruiting, sort, cursorToLoad]);

  const toggleSave = (id: number) => {
    if (!isLoggedIn) { setShowLoginModal(true); return; }
    const next = saved.includes(id) ? saved.filter(x => x !== id) : [...saved, id];
    if (!saved.includes(id)) track('professor_saved', { professor_id: id, surface: 'discover' });
    setSaved(next); localStore.setSaved(next); patchUserState({ saved_professor_ids: next }).catch(() => undefined);
  };

  const recruitingOptions = useMemo(() => ['positive', 'negative', 'unknown'], []);

  return (
    <div>
      <div className="topbar filter-bar">
        <div className="row between">
          <div><h2 style={{ margin: 0 }}>Discover</h2><p className="muted">{total} professors · {professors.length} loaded</p></div>
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
          <SearchBox value={q} onChange={setQ} placeholder="Search all fields…" />
          <SortSelect value={sort} onChange={setSort} options={[{ value: 'name-asc', label: 'Name A–Z' }, { value: 'name-desc', label: 'Name Z–A' }, { value: 'university-asc', label: 'University A–Z' }, { value: 'university-desc', label: 'University Z–A' }, { value: 'recruiting-asc', label: 'Recruiting ↑' }, { value: 'recruiting-desc', label: 'Recruiting ↓' }]} />
          <MultiSelectFilter label="Tags" icon="tag" options={facets.tags} values={tags} onChange={setTags} />
          <MultiSelectFilter label="Universities" icon="building" options={facets.universities} values={universities} onChange={setUniversities} />
          <MultiSelectFilter label="Departments" icon="paper" options={facets.departments} values={departments} onChange={setDepartments} />
          <SingleSelectFilter label="Recruiting" value={recruiting} onChange={setRecruiting} icon="shield" emptyLabel="All statuses" options={recruitingOptions.map(r => ({ value: r, label: r === 'positive' ? 'Recruiting' : r === 'negative' ? 'Not recruiting' : 'Unknown' }))} />
        </FilterSortBar>
      </div>

      {error && <div className="error" style={{ margin: 24 }}>{error}</div>}
      <div className="cards list">
        {professors.map(p => (
          <ProfessorCard key={p.id} professor={p} saved={saved.includes(p.id)} onSave={() => toggleSave(p.id)} from="/professors" />
        ))}
        {loading && <ProfessorListSkeleton count={cursorToLoad ? 2 : 4} />}
        {!loading && !error && professors.length === 0 && (
          <div className="card soft">
            <h3>No professors match these filters.</h3>
            <p className="muted">Try clearing filters or searching for a broader research area.</p>
            <button className="button secondary" style={{ marginTop: 12 }} onClick={() => { setQ(''); setUniversities([]); setTags([]); setDepartments([]); setRecruiting(''); }}>Clear filters</button>
          </div>
        )}
        {!loading && nextCursor && <button className="button secondary" onClick={() => setCursorToLoad(nextCursor)}>Load more professors</button>}
      </div>

      <LoginModal isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} message="Log in to save professors to your account and build a shortlist." />
    </div>
  );
}
