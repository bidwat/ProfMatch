import type { MetadataRoute } from 'next';

const SITE_URL = process.env.SITE_URL || 'https://prof-match-chi.vercel.app';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export const dynamic = 'force-dynamic';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticRoutes: MetadataRoute.Sitemap = ['/', '/professors', '/pricing'].map(path => ({
    url: `${SITE_URL}${path === '/' ? '' : path}`,
    changeFrequency: 'weekly',
    priority: path === '/' ? 1 : 0.8,
  }));

  try {
    const response = await fetch(`${BACKEND_URL}/api/professors?limit=100&sort=name-asc`, { next: { revalidate: 3600 } });
    if (!response.ok) return staticRoutes;
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
      ...professors.map(p => ({
        url: `${SITE_URL}/professors/${p.id}`,
        changeFrequency: 'monthly' as const,
        priority: 0.6,
      })),
    ];
  } catch {
    return staticRoutes;
  }
}
