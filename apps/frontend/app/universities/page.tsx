'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { Card, Input } from '@heroui/react';
import { getUniversitiesOverview, type DepartmentGroup } from '@/lib/api';
import { slugify } from '@/lib/slug';

interface UniversitySummary {
  name: string;
  slug: string;
  departments: number;
  professors: number;
  publications: number;
}

export default function UniversitiesPage() {
  const [groups, setGroups] = useState<DepartmentGroup[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getUniversitiesOverview()
      .then(r => setGroups(r.groups))
      .catch(e => setError(e.message || 'Could not load universities.'))
      .finally(() => setLoading(false));
  }, []);

  const universities = useMemo<UniversitySummary[]>(() => {
    const byName = new Map<string, UniversitySummary>();
    for (const group of groups) {
      const entry = byName.get(group.university) || { name: group.university, slug: slugify(group.university), departments: 0, professors: 0, publications: 0 };
      entry.departments += 1;
      entry.professors += group.professor_count;
      entry.publications += group.publication_count;
      byName.set(group.university, entry);
    }
    const list = Array.from(byName.values()).sort((a, b) => a.name.localeCompare(b.name));
    const needle = query.trim().toLowerCase();
    return needle ? list.filter(u => u.name.toLowerCase().includes(needle)) : list;
  }, [groups, query]);

  return (
    <div className="page narrow">
      <div style={{ margin: '36px 0 22px' }}>
        <h1 style={{ fontSize: 32, margin: 0 }}>Universities</h1>
        <p className="muted" style={{ marginTop: 8 }}>Browse the institutions indexed on ProfMatch. Every professor profile is public and source-backed.</p>
        <div style={{ maxWidth: 420, marginTop: 14 }}>
          <Input value={query} onChange={e => setQuery(e.target.value)} placeholder="Filter universities…" aria-label="Filter universities" />
        </div>
      </div>

      {error && <div className="error">{error}</div>}
      {loading && <div className="card soft">Loading universities…</div>}
      {!loading && !error && universities.length === 0 && (
        <div className="card soft" style={{ textAlign: 'center', padding: 32 }}>
          <h3>No universities match.</h3>
          <p className="muted" style={{ margin: '8px 0 14px' }}>Missing your university? Request it and our admins will review it for import.</p>
          <Link className="button secondary" href="/recommend">Request a department</Link>
        </div>
      )}

      <div className="grid two">
        {universities.map(u => (
          <Link key={u.slug} href={`/universities/${u.slug}`} style={{ display: 'block' }}>
            <Card style={{ padding: 20, height: '100%' }}>
              <h3 style={{ margin: 0 }}>{u.name}</h3>
              <p className="muted small-text" style={{ marginTop: 6 }}>
                {u.departments} department{u.departments === 1 ? '' : 's'} · {u.professors} professors · {u.publications} publications indexed
              </p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
