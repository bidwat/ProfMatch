import type { MetadataRoute } from 'next';

const SITE_URL = process.env.SITE_URL || 'https://prof-match-chi.vercel.app';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/admin', '/dashboard', '/profile', '/saved', '/board', '/compare', '/match', '/results'],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
