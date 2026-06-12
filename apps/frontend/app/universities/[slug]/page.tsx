'use client';

import Link from 'next/link';
import { use, useEffect, useMemo, useState } from 'react';
import { Card } from '@heroui/react';
import { getUniversitiesOverview, type DepartmentGroup } from '@/lib/api';
import { slugify } from '@/lib/slug';

export default function UniversityPage({ params: paramsPromise }: { params: Promise<{ slug: string }> }) {
  const params = use(paramsPromise);
  const [groups, setGroups] = useState<DepartmentGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getUniversitiesOverview()
      .then(r => setGroups(r.groups))
      .catch(e => setError(e.message || 'Could not load this university.'))
      .finally(() => setLoading(false));
  }, []);

  const departments = useMemo(() => groups.filter(g => slugify(g.university) === params.slug), [groups, params.slug]);
  const universityName = departments[0]?.university;
  const totals = useMemo(() => departments.reduce(
    (acc, g) => ({ professors: acc.professors + g.professor_count, publications: acc.publications + g.publication_count }),
    { professors: 0, publications: 0 },
  ), [departments]);

  useEffect(() => {
    if (universityName) document.title = `${universityName} – Professors and Departments | Univya`;
  }, [universityName]);

  if (loading) return <div className="page narrow"><div className="card soft" style={{ marginTop: 32 }}>Loading university…</div></div>;
  if (error) return <div className="page narrow"><div className="error" style={{ marginTop: 32 }}>{error}</div></div>;

  if (!universityName) {
    return (
      <div className="page narrow">
        <div className="card soft" style={{ marginTop: 32, textAlign: 'center', padding: 32 }}>
          <h3>University not found.</h3>
          <p className="muted" style={{ margin: '8px 0 14px' }}>It may not be indexed yet. You can request it for import.</p>
          <div className="row center">
            <Link className="button secondary" href="/universities">All universities</Link>
            <Link className="button primary" href="/recommend">Request a department</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="page narrow">
      <nav className="muted small-text" style={{ marginTop: 26 }} aria-label="Breadcrumb">
        <Link className="accent" href="/universities">Universities</Link> / {universityName}
      </nav>
      <div style={{ margin: '10px 0 22px' }}>
        <h1 style={{ fontSize: 32, margin: 0 }}>{universityName}</h1>
        <p className="muted" style={{ marginTop: 8 }}>
          {departments.length} department{departments.length === 1 ? '' : 's'} indexed · {totals.professors} professors · {totals.publications} publications
        </p>
        <Link className="button secondary" style={{ marginTop: 10 }} href={`/professors?university=${encodeURIComponent(universityName)}`}>
          Search all professors at {universityName}
        </Link>
      </div>

      <div className="grid two">
        {departments.map(g => (
          <Link key={g.department} href={`/universities/${params.slug}/${slugify(g.department)}`} style={{ display: 'block' }}>
            <Card style={{ padding: 20, height: '100%' }}>
              <h3 style={{ margin: 0 }}>{g.department}</h3>
              <p className="muted small-text" style={{ marginTop: 6 }}>{g.professor_count} professors · {g.publication_count} publications indexed</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
