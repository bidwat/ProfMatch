import type { MetadataRoute } from 'next';

const SITE_URL = process.env.SITE_URL || 'https://prof-match-chi.vercel.app';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export const dynamic = 'force-dynamic';

function slugify(value: string): string {
  return value.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes: MetadataRoute.Sitemap = ['/', '/professors', '/universities', '/pricing'].map(path => ({
    url: `${SITE_URL}${path === '/' ? '' : path}`,
    changeFrequency: 'weekly',
    priority: path === '/' ? 1 : 0.8,
  }));

  let universityRoutes: MetadataRoute.Sitemap = [];
  try {
    const overview = await fetch(`${BACKEND_URL}/api/universities/overview`, { next: { revalidate: 3600 } });
    if (overview.ok) {
      const { groups } = await overview.json();
      const universities = new Set<string>();
      for (const group of groups as { university: string; department: string }[]) {
        universities.add(slugify(group.university));
        universityRoutes.push({ url: `${SITE_URL}/universities/${slugify(group.university)}/${slugify(group.department)}`, changeFrequency: 'monthly', priority: 0.6 });
      }
      universityRoutes = [
        ...Array.from(universities).map(slug => ({ url: `${SITE_URL}/universities/${slug}`, changeFrequency: 'monthly' as const, priority: 0.7 })),
        ...universityRoutes,
      ];
    }
  } catch {
    // University routes are optional in the sitemap.
  }

  try {
    const response = await fetch(`${BACKEND_URL}/api/professors?limit=100&sort=name-asc`, { next: { revalidate: 3600 } });
    if (!response.ok) return [...staticRoutes, ...universityRoutes];
    const data = await response.json();
    let professors: { id: number }[] = data.professors || [];
    let cursor: string | null = data.next_cursor || null;
    // Walk the cursor pagination; profiles refresh slowly, so cap the walk.
    for (let page = 0; cursor && page < 50; page += 1) {
      const next = await fetch(`${BACKEND_URL}/api/professors?limit=100&sort=name-asc&cursor=${encodeURIComponent(cursor)}`, { next: { revalidate: 3600 } });
      if (!next.ok) break;
      const body = await next.json();
      professors = professors.concat(body.professors || []);
      cursor = body.next_cursor || null;
    }
    return [
      ...staticRoutes,
      ...universityRoutes,
      ...professors.map(p => ({
        url: `${SITE_URL}/professors/${p.id}`,
        changeFrequency: 'monthly' as const,
        priority: 0.6,
      })),
    ];
  } catch {
    return [...staticRoutes, ...universityRoutes];
  }
}
