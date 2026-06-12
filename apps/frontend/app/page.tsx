'use client';

import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { getStats } from '@/lib/api';
import { ThemeToggle } from '@/components/ThemeToggle';
import type { ExplorerStatsResponse } from '@/lib/types';

function formatStat(value?: number) {
  if (typeof value !== 'number') return '—';
  return new Intl.NumberFormat('en-US').format(value);
}

const productShots = [
  { src: '/landing/discover.png', title: 'Browse professors without opening dozens of tabs', body: 'Search by name, university, department, research area, and recruiting signal from one directory.' },
  { src: '/landing/matches.png', title: 'See why each professor fits your profile', body: 'Ranked results explain the overlap with paper evidence and honest caveats.' },
  { src: '/landing/profile.png', title: 'Review the details before you shortlist', body: 'Summaries, tags, publications, contact links, and source confidence in one place.' },
];

const exampleTopics = ['Artificial Intelligence', 'Computational Biology', 'Public Health', 'Robotics', 'Climate Science'];

const steps = [
  ['01', 'Describe your research goals', 'Interests, background, target degree, and preferences — once.'],
  ['02', 'Browse matching faculty records', 'A ranked shortlist drawn from source-backed profiles.'],
  ['03', 'Review paper-backed reasons', 'What matched, which papers, and where the system is uncertain.'],
  ['04', 'Save professors for later', 'Shortlist, compare, and track outreach on your board.'],
];

const faqEntries = [
  ['Is Univya free?', 'Browsing, keyword search, and filters are free without an account. An account adds saved shortlists and personalized matching.'],
  ['What does the match percentage mean?', 'A research-fit score — overlap between your interests and a professor’s recent, source-backed work. Not an admission chance.'],
  ['Where does professor data come from?', 'Public faculty pages, personal and lab websites, and OpenAlex — each profile keeps source links and a confidence label.'],
  ['Can I report incorrect data?', 'Yes. Every profile has a report path reviewed by admins before public data changes.'],
];

export default function LandingPage() {
  const router = useRouter();
  const [stats, setStats] = useState<ExplorerStatsResponse | null>(null);
  const [query, setQuery] = useState('');
  useEffect(() => { getStats().then(setStats).catch(() => {}); }, []);

  const searchProfessors = (term: string) => {
    const trimmed = term.trim();
    router.push(trimmed ? `/professors?q=${encodeURIComponent(trimmed)}` : '/professors');
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--uv-bg)' }}>
      <header style={{ position: 'sticky', top: 0, zIndex: 50, background: 'color-mix(in oklab, var(--uv-bg) 86%, transparent)', backdropFilter: 'blur(14px)', borderBottom: '1px solid var(--uv-border)' }}>
        <div className="uv-wrap" style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24 }}>
          <Link className="brand" href="/" style={{ fontSize: 20 }}><span>Univya<span className="brand-dot">.</span></span></Link>
          <nav className="uv-nav-desktop" aria-label="Landing navigation">
            <Link className="muted" href="/professors" prefetch={false}>Browse professors</Link>
            <Link className="muted" href="/universities" prefetch={false}>Universities</Link>
            <a className="muted" href="#how">How it works</a>
            <Link className="muted" href="/pricing" prefetch={false}>Pricing</Link>
            <a className="muted" href="#faq">FAQ</a>
          </nav>
          <div className="row" style={{ gap: 10 }}>
            <ThemeToggle />
            <Link className="button secondary uv-hide-sm" href="/signin" prefetch={false}>Sign in</Link>
            <Link className="button primary" href="/signup" prefetch={false}>Get started →</Link>
          </div>
        </div>
      </header>

      <main className="uv-wrap">
        <section aria-label="Hero" className="uv-hero">
          <div style={{ display: 'grid', gap: 22, justifyItems: 'start' }}>
            <span className="uv-pill"><i />Research-fit advisor discovery</span>
            <h1 style={{ margin: 0, fontSize: 'clamp(36px, 4.6vw, 52px)', lineHeight: 1.06, letterSpacing: '-0.025em' }}>Find professors whose recent work matches your research story.</h1>
            <p className="muted" style={{ margin: 0, fontSize: 17, lineHeight: 1.6, maxWidth: 520 }}>Univya turns your background, interests, and degree goals into an explainable shortlist of potential MS/PhD advisors — with recent-paper evidence and clear reasons for every match.</p>
            <form role="search" className="uv-search-row" onSubmit={e => { e.preventDefault(); searchProfessors(query); }}>
              <input
                type="search"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Professor, university, department, or topic…"
                aria-label="Search professors"
                style={{ flex: 1, minWidth: 0, padding: '14px 18px', border: '1px solid var(--uv-border)', borderRadius: 12, fontSize: 15, background: 'var(--uv-surface)', color: 'var(--uv-text)', boxShadow: 'var(--uv-shadow)' }}
              />
              <button className="button primary" type="submit" style={{ padding: '14px 22px', fontSize: 15 }}>Search</button>
            </form>
            <div className="row" style={{ gap: 8 }} aria-label="Example topics">
              {exampleTopics.map(topic => (
                <button key={topic} type="button" className="uv-chip-outline" onClick={() => searchProfessors(topic)}>{topic}</button>
              ))}
            </div>
            <div className="uv-stats" aria-label="Dataset stats">
              <div><strong>{formatStat(stats?.professor_count)}</strong><span>Professors indexed</span></div>
              <div><strong>{formatStat(stats?.publication_count)}</strong><span>Papers indexed</span></div>
              <div><strong>{formatStat(stats?.professors_with_publications)}</strong><span>Profiles with papers</span></div>
            </div>
          </div>

          <div aria-label="Match preview" className="uv-preview-panel">
            <div className="t-label" style={{ letterSpacing: '.1em' }}>Match preview</div>
            <div className="uv-card" style={{ padding: 20, display: 'flex', alignItems: 'center', gap: 16 }}>
              <div className="uv-score-ring" style={{ background: 'conic-gradient(var(--uv-accent) 78%, var(--uv-surface2) 0)' }}><div>78%</div></div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: 15.5 }}>Ada Lovelace · Stanford</div>
                <div className="muted" style={{ fontSize: 13, lineHeight: 1.5 }}>Recent papers align with robot learning, computer vision, and sim-to-real transfer.</div>
              </div>
            </div>
            <div className="uv-card" style={{ padding: '18px 20px' }}>
              <div className="uv-eyebrow" style={{ marginBottom: 8 }}>Why matched</div>
              <div className="row" style={{ gap: 7 }}>
                <span className="tag">robot learning</span>
                <span className="tag">vision foundation models</span>
                <span className="tag">3 relevant papers</span>
              </div>
            </div>
            <div className="uv-deep" style={{ padding: '18px 20px' }}>
              <div style={{ fontWeight: 700, fontSize: 14.5 }}>Know why someone matched</div>
              <div className="uv-deep-muted" style={{ fontSize: 12.5, marginTop: 3 }}>Topics · recent papers · fit reasons · uncertainty notes</div>
            </div>
          </div>
        </section>

        <section className="uv-section" aria-label="Product preview">
          <div className="uv-eyebrow">Product preview</div>
          <h2 className="uv-h2" style={{ maxWidth: 640 }}>Everything you need to evaluate professor fit, in one workflow.</h2>
          <div className="uv-grid3">
            {productShots.map(shot => (
              <article className="uv-card" key={shot.src} style={{ padding: 16, display: 'grid', gap: 14 }}>
                <div style={{ position: 'relative', height: 150, borderRadius: 10, border: '1px solid var(--uv-border)', overflow: 'hidden', background: 'var(--uv-surface2)' }}>
                  <Image src={shot.src} alt="" fill sizes="(max-width: 900px) 100vw, 33vw" style={{ objectFit: 'cover', objectPosition: 'top center' }} />
                </div>
                <div style={{ padding: '0 6px 8px' }}>
                  <div style={{ fontWeight: 700, fontSize: 15.5, lineHeight: 1.35 }}>{shot.title}</div>
                  <p className="muted" style={{ margin: '6px 0 0', fontSize: 13.5, lineHeight: 1.55 }}>{shot.body}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="uv-section" aria-label="Problem comparison">
          <div className="uv-eyebrow">The problem</div>
          <h2 className="uv-h2">Finding an advisor shouldn’t require dozens of tabs and a spreadsheet.</h2>
          <div className="uv-grid2">
            <div style={{ background: 'var(--uv-surface2)', border: '1px solid var(--uv-border)', borderRadius: 16, padding: 30 }}>
              <h3 className="muted" style={{ margin: '0 0 18px', fontSize: 17, fontWeight: 700 }}>The old way</h3>
              <div className="muted" style={{ display: 'grid', gap: 14, fontSize: 14.5, lineHeight: 1.5 }}>
                {['Search department faculty pages one university at a time', 'Read bios that may be years out of date', 'Guess whether a professor’s current work fits your interests', 'Track candidates in a spreadsheet you maintain by hand'].map(line => (
                  <div key={line} style={{ display: 'flex', gap: 12 }}><span style={{ color: 'var(--uv-bad)', fontWeight: 700 }}>✕</span><span>{line}</span></div>
                ))}
              </div>
            </div>
            <div className="uv-deep" style={{ padding: 30 }}>
              <h3 style={{ margin: '0 0 18px', fontSize: 17, fontWeight: 700 }}>With Univya</h3>
              <div style={{ display: 'grid', gap: 14, fontSize: 14.5, lineHeight: 1.5 }}>
                {['Search professor profiles across universities in one place', 'AI summaries informed by recent publications, with sources', 'Explainable research-fit scores with paper evidence', 'Save a shortlist tied to your account'].map(line => (
                  <div key={line} style={{ display: 'flex', gap: 12 }}><span style={{ color: 'var(--uv-accent)', fontWeight: 700 }}>✓</span><span>{line}</span></div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section id="how" className="uv-section" aria-label="How it works">
          <div className="uv-eyebrow">How it works</div>
          <h2 className="uv-h2" style={{ maxWidth: 640 }}>From your interests to a focused advisor shortlist.</h2>
          <div className="uv-grid4">
            {steps.map(([num, title, body]) => (
              <div className="uv-card" key={num} style={{ display: 'grid', gap: 10, alignContent: 'start', padding: 24, boxShadow: 'none' }}>
                <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--uv-accent-text)' }}>{num}</div>
                <div style={{ fontWeight: 700, fontSize: 15.5, lineHeight: 1.35 }}>{title}</div>
                <p className="muted" style={{ margin: 0, fontSize: 13, lineHeight: 1.55 }}>{body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="uv-section uv-grid2" aria-label="Audience features">
          <div className="uv-card" style={{ padding: 30 }}>
            <div className="uv-eyebrow">For applicants</div>
            <h2 style={{ margin: '10px 0 18px', fontSize: 22, letterSpacing: '-0.015em' }}>Built around the decisions students actually make.</h2>
            <div className="muted" style={{ display: 'grid', gap: 13, fontSize: 14, lineHeight: 1.55 }}>
              <div><strong style={{ color: 'var(--uv-text)' }}>Academic profile</strong> — interests, background, degree, preferences, once.</div>
              <div><strong style={{ color: 'var(--uv-text)' }}>Ranked recommendations</strong> — ordered by research fit and evidence.</div>
              <div><strong style={{ color: 'var(--uv-text)' }}>Evidence-backed explanations</strong> — what matched and where the system is uncertain.</div>
              <div><strong style={{ color: 'var(--uv-text)' }}>Saved professors</strong> — a shortlist you can return to anytime.</div>
            </div>
          </div>
          <div className="uv-card" style={{ padding: 30 }}>
            <div className="uv-eyebrow">Why it helps</div>
            <h2 style={{ margin: '10px 0 18px', fontSize: 22, letterSpacing: '-0.015em' }}>Spend time evaluating fit, not collecting links.</h2>
            <div className="muted" style={{ display: 'grid', gap: 13, fontSize: 14, lineHeight: 1.55 }}>
              <div><strong style={{ color: 'var(--uv-text)' }}>Recent work first</strong> — current publications, not stale bios.</div>
              <div><strong style={{ color: 'var(--uv-text)' }}>Clear uncertainty</strong> — unknown means unknown, never glossed over.</div>
              <div><strong style={{ color: 'var(--uv-text)' }}>Less manual scanning</strong> — compare faculty across universities at once.</div>
            </div>
          </div>
        </section>

        <section aria-label="Department request" style={{ padding: '0 0 64px' }}>
          <div className="uv-card" style={{ padding: '24px 30px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap', boxShadow: 'none' }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 16 }}>Don’t see your university or department?</div>
              <div className="muted" style={{ fontSize: 13.5, marginTop: 3 }}>Request it with the faculty page URL and our admins will review it for import.</div>
            </div>
            <Link className="button secondary" href="/recommend" prefetch={false}>Request a department →</Link>
          </div>
        </section>

        <section id="faq" className="uv-section" aria-label="FAQ">
          <div className="uv-eyebrow">FAQ</div>
          <h2 className="uv-h2" style={{ marginBottom: 32 }}>Common questions, answered plainly.</h2>
          <div className="uv-grid2" style={{ gap: 16, alignItems: 'start' }}>
            {faqEntries.map(([question, answer]) => (
              <details className="uv-faq" key={question}>
                <summary>{question}</summary>
                <p>{answer}</p>
              </details>
            ))}
          </div>
        </section>

        <section aria-label="Final CTA" style={{ padding: '0 0 80px' }}>
          <div className="uv-deep uv-cta-deep">
            <h2 style={{ margin: '0 auto', fontSize: 34, maxWidth: 560 }}>Build a shortlist backed by recent research evidence.</h2>
            <p className="uv-deep-muted" style={{ margin: '14px auto 28px', fontSize: 15.5, lineHeight: 1.6, maxWidth: 480 }}>Create your profile, review explainable matches, and save the professors you want to revisit.</p>
            <div className="row center" style={{ gap: 12 }}>
              <Link className="uv-btn-accent" href="/signup" prefetch={false}>Get started →</Link>
              <Link className="uv-btn-deepline" href="/professors" prefetch={false}>Browse professors</Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="uv-footer">
        <div className="uv-wrap" style={{ padding: '32px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap' }}>
          <span className="brand" style={{ fontSize: 16 }}><span>Univya<span className="brand-dot">.</span></span></span>
          <nav className="row" style={{ gap: 22, fontSize: 13 }}>
            <Link className="muted" href="/professors" prefetch={false}>Browse professors</Link>
            <Link className="muted" href="/universities" prefetch={false}>Universities</Link>
            <Link className="muted" href="/pricing" prefetch={false}>Pricing</Link>
          </nav>
          <span style={{ fontSize: 12.5, color: 'var(--uv-faint)' }}>© 2026 Univya</span>
        </div>
      </footer>
    </div>
  );
}
