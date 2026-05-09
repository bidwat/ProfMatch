'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getStats } from '@/lib/api';
import type { ExplorerStatsResponse } from '@/lib/types';

function formatStat(value?: number) {
  if (typeof value !== 'number') return '—';
  return new Intl.NumberFormat('en-US').format(value);
}

const productShots = [
  {
    src: '/landing/discover.png',
    label: 'Discover',
    title: 'Browse professors without opening dozens of tabs',
    body: 'Search by name, university, department, research area, publication coverage, and recruiting signal from one focused directory.',
  },
  {
    src: '/landing/matches.png',
    label: 'Matches',
    title: 'See why each professor fits your profile',
    body: 'Ranked results explain the overlap between your interests and a professor’s recent work, including relevant paper evidence and caveats.',
  },
  {
    src: '/landing/profile.png',
    label: 'Profiles',
    title: 'Review the details before you shortlist',
    body: 'Open a profile to scan research summaries, tags, recent publications, contact links, and source confidence in one place.',
  },
];

const studentFeatures = [
  ['Academic profile', 'Describe your research interests, background, target degree, and university or location preferences once.'],
  ['Smart ranked recommendations', 'Get a focused list of professors ordered by research fit, publication overlap, and profile completeness.'],
  ['Evidence-backed explanations', 'Understand what matched, which papers support the match, and where the system is uncertain.'],
  ['Saved professors', 'Keep promising faculty in a personal shortlist so you can return to them while preparing applications.'],
];

const researchChecks = [
  ['Recent work first', 'Profiles emphasize current publications and research summaries, not only static department bios.'],
  ['Clear uncertainty', 'Recruiting status is shown cautiously; unknown means unknown, not a hidden negative.'],
  ['Less manual scanning', 'Compare faculty across universities from the same interface instead of maintaining a spreadsheet from scratch.'],
];

export default function LandingPage() {
  const [stats, setStats] = useState<ExplorerStatsResponse | null>(null);
  useEffect(() => { getStats().then(setStats).catch(() => {}); }, []);

  return (
    <div className="landing-page landing-page-expanded">
      <header className="landing-public-nav landing-nav-sticky">
        <Link className="brand" href="/">
          <span className="brand-mark">PM</span><span>ProfMatch</span>
        </Link>
        <nav className="landing-nav-links" aria-label="Landing navigation">
          <a href="#discover">Discover</a>
          <a href="#workflow">How it works</a>
          <a href="#features">Features</a>
        </nav>
        <div className="row">
          <Link className="ghost small" href="/signin" prefetch={false}>Sign in</Link>
          <Link className="button primary" href="/signup" prefetch={false}>Get started →</Link>
        </div>
      </header>

      <main>
        <section className="landing-hero landing-hero-expanded">
          <div className="landing-copy">
            <div className="badge">✦ Research-fit professor discovery</div>
            <h1>Find professors whose recent work matches your research story.</h1>
            <div className="landing-accent-line" />
            <p className="lead">ProfMatch turns your academic background, interests, degree goals, and preferences into an explainable shortlist of potential MS/PhD advisors — with recent paper context, profile summaries, and clear reasons for every recommendation.</p>
            <div className="row landing-actions">
              <Link className="button primary landing-cta" href="/signup" prefetch={false}>Start matching →</Link>
              <Link className="button secondary landing-cta" href="/signin" prefetch={false}>Sign in</Link>
            </div>
            <div className="landing-stats landing-stats-cards" aria-label="Dataset statistics">
              <div className="landing-stat"><strong>{formatStat(stats?.professor_count)}</strong><span>Professors indexed</span></div>
              <div className="landing-stat olive"><strong>{formatStat(stats?.publication_count)}</strong><span>Papers indexed</span></div>
              <div className="landing-stat peach"><strong>{formatStat(stats?.professors_with_publications)}</strong><span>Profiles with papers</span></div>
            </div>
          </div>

          <div className="landing-preview-stack" aria-label="Match preview">
            <div className="landing-preview-card landing-preview-card-main">
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
                  <p>Recent papers align with HCI, machine learning, and mixed-reality systems.</p>
                </div>
                <span>74%</span>
              </div>
            </div>
            <div className="landing-mini-panel"><strong>Know why someone matched</strong><span>Topics · recent papers · fit reasons · uncertainty notes</span></div>
          </div>
        </section>

        <section id="discover" className="landing-section landing-showcase-section">
          <div className="landing-section-heading">
            <span className="t-label">Product preview</span>
            <h2>Everything you need to evaluate professor fit in one workflow.</h2>
            <p>Move from broad discovery to ranked matches to individual professor review without losing the evidence behind each recommendation.</p>
          </div>
          <div className="landing-shot-grid">
            {productShots.map((shot) => (
              <article className="landing-shot-card" key={shot.src}>
                <div className="landing-shot-frame"><Image src={shot.src} alt={`${shot.label} screen`} fill sizes="(max-width: 900px) 100vw, 33vw" /></div>
                <div className="landing-shot-copy"><span>{shot.label}</span><h3>{shot.title}</h3><p>{shot.body}</p></div>
              </article>
            ))}
          </div>
        </section>

        <section id="workflow" className="landing-section landing-workflow-section">
          <div className="landing-section-heading compact">
            <span className="t-label">How it works</span>
            <h2>From your interests to a focused advisor shortlist.</h2>
          </div>
          <div className="landing-workflow-grid">
            {['Describe your research goals', 'Browse matching faculty records', 'Review paper-backed reasons', 'Save professors for later'].map((step, index) => (
              <div className="landing-step-card" key={step}><span>0{index + 1}</span><strong>{step}</strong></div>
            ))}
          </div>
        </section>

        <section id="features" className="landing-section landing-two-column user-facing">
          <div className="landing-feature-panel">
            <span className="t-label">For applicants</span>
            <h2>Built around the decisions students actually make.</h2>
            <div className="landing-list-grid">
              {studentFeatures.map(([title, body]) => <div className="landing-list-item" key={title}><strong>{title}</strong><p>{body}</p></div>)}
            </div>
          </div>
          <div className="landing-feature-panel olive-panel">
            <span className="t-label">Why it helps</span>
            <h2>Spend more time evaluating fit, less time collecting links.</h2>
            <div className="landing-list-grid">
              {researchChecks.map(([title, body]) => <div className="landing-list-item" key={title}><strong>{title}</strong><p>{body}</p></div>)}
            </div>
          </div>
        </section>

        <section className="landing-final-cta">
          <div>
            <span className="badge">Ready to make your professor search more focused?</span>
            <h2>Build a shortlist backed by recent research evidence.</h2>
            <p>Create your profile, review explainable matches, and save the professors you want to revisit.</p>
          </div>
          <Link className="button primary landing-cta" href="/signup" prefetch={false}>Get started →</Link>
        </section>
      </main>
    </div>
  );
}
