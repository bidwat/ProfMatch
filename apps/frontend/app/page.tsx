'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getStats } from '@/lib/api';
import type { ExplorerStatsResponse } from '@/lib/types';

function formatStat(value?: number) {
  if (typeof value !== 'number') return '—';
  return new Intl.NumberFormat('en-US').format(value);
}

export default function LandingPage() {
  const [stats, setStats] = useState<ExplorerStatsResponse | null>(null);
  useEffect(() => { getStats().then(setStats).catch(() => {}); }, []);

  return (
    <div className="landing-page">
      <header className="landing-public-nav">
        <Link className="brand" href="/">
          <span className="brand-mark">PM</span><span>ProfMatch</span>
        </Link>
        <div className="row">
          <Link className="ghost small" href="/signin" prefetch={false}>Sign in</Link>
          <Link className="button primary" href="/signup" prefetch={false}>Get started →</Link>
        </div>
      </header>

      <section className="landing-hero">
        <div className="landing-copy">
          <div className="badge">✦ Research-fit professor discovery</div>
          <h1>Build a shortlist of professors who match your research story.</h1>
          <div className="landing-accent-line" />
          <p className="lead">Turn your academic background, interests, and degree goals into a focused list of advisors — with clear match explanations and recent paper context.</p>
          <div className="row landing-actions">
            <Link className="button primary landing-cta" href="/signup" prefetch={false}>Get started →</Link>
            <Link className="button secondary landing-cta" href="/signin" prefetch={false}>Sign in</Link>
          </div>
          <div className="landing-stats" aria-label="Dataset statistics">
            <div className="landing-stat"><strong>{formatStat(stats?.professor_count)}</strong><span>Professors</span></div>
            <div className="landing-stat olive"><strong>{formatStat(stats?.publication_count)}</strong><span>Papers indexed</span></div>
            <div className="landing-stat peach"><strong>{formatStat(stats?.professors_with_publications)}</strong><span>Profiles</span></div>
          </div>
        </div>

        <div className="landing-preview-card" aria-label="Match preview">
          <div className="t-label">Match preview</div>
          <svg className="landing-match-svg" viewBox="0 0 360 160" role="img" aria-label="Research fit overlap illustration">
            <defs>
              <radialGradient id="gYou" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#F5E2BC" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#F5E2BC" stopOpacity="0" />
              </radialGradient>
              <radialGradient id="gLab" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#DDE3A8" stopOpacity="0.8" />
                <stop offset="100%" stopColor="#DDE3A8" stopOpacity="0" />
              </radialGradient>
            </defs>
            <circle cx="110" cy="80" r="62" fill="url(#gYou)" stroke="#E8B860" strokeWidth="1" strokeDasharray="4 3" />
            <circle cx="250" cy="80" r="52" fill="url(#gLab)" stroke="#B8C265" strokeWidth="1" strokeDasharray="4 3" />
            <path d="M158 50Q180 30 202 50Q218 65 218 80Q218 95 202 110Q180 130 158 110Q142 95 142 80Q142 65 158 50Z" fill="#FBF4E4" opacity=".7" />
            <path d="M110 80Q180 20 250 80" fill="none" stroke="#C9973A" strokeWidth="1.5" strokeDasharray="5 3" />
            <circle cx="110" cy="80" r="28" fill="#FBF4E4" stroke="#E8B860" strokeWidth="1.5" />
            <text x="110" y="76" textAnchor="middle" fontSize="10" fontWeight="600" fill="#6E4F18">You</text>
            <text x="110" y="89" textAnchor="middle" fontSize="8" fill="#A07528">HCI · ML · AR</text>
            <circle cx="250" cy="80" r="24" fill="#F2F5E3" stroke="#B8C265" strokeWidth="1.5" />
            <text x="250" y="76" textAnchor="middle" fontSize="10" fontWeight="600" fill="#454A1C">Lab</text>
            <text x="250" y="89" textAnchor="middle" fontSize="8" fill="#6A722E">Prof. Davis</text>
            <rect x="153" y="58" width="54" height="44" rx="4" fill="#fff" stroke="rgba(37,34,28,.10)" />
            <text x="180" y="80" textAnchor="middle" fontSize="18" fontWeight="800" fill="#A07528">92%</text>
            <text x="180" y="94" textAnchor="middle" fontSize="8" fill="rgba(37,34,28,.65)">research fit</text>
          </svg>
          <div className="landing-preview-result">
            <div>
              <strong>Randall Davis · MIT</strong>
              <p>Recent papers align with trustworthy ML & HCI systems.</p>
            </div>
            <span>74%</span>
          </div>
        </div>
      </section>

      <section className="landing-feature-band">
        <div className="landing-feature-grid">
          <div className="landing-feature-card"><span>✦</span><h3>Explainable matches</h3><p>See exactly why each professor fits your background and interests.</p></div>
          <div className="landing-feature-card"><span>▤</span><h3>Recent paper context</h3><p>Read concise summaries of recent work before saving.</p></div>
          <div className="landing-feature-card"><span>◇</span><h3>Personal shortlist</h3><p>Refine your profile at any time and re-run matching.</p></div>
        </div>
      </section>
    </div>
  );
}
