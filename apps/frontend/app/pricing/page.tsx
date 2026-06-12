'use client';

import Link from 'next/link';

const freeFeatures = [
  'Browse professor profiles',
  'Keyword search and filters',
  'AI summaries with source links',
  'Recent publications with confidence labels',
  'Report incorrect data',
  'Request missing departments',
];

const paidFeatures = [
  'Personalized research-fit matching',
  'Match threshold controls and evidence',
  'Saved professor shortlists',
  'Professor comparison',
  'Application board with outreach stages',
  'Outreach email drafts (never auto-sent)',
];

function CheckList({ items }: { items: string[] }) {
  return (
    <div style={{ display: 'grid', gap: 12, fontSize: 14, lineHeight: 1.5, marginBottom: 28 }}>
      {items.map(item => (
        <div key={item} style={{ display: 'flex', gap: 11 }}>
          <span style={{ color: 'var(--uv-accent)', fontWeight: 700 }}>✓</span>
          <span>{item}</span>
        </div>
      ))}
    </div>
  );
}

export default function PricingPage() {
  return (
    <main className="uv-wrap" style={{ maxWidth: 880, paddingTop: 32, paddingBottom: 32 }}>
      <div style={{ textAlign: 'center', padding: '48px 0 40px' }}>
        <div className="uv-eyebrow">Pricing</div>
        <h1 style={{ margin: '12px auto 0', fontSize: 'clamp(28px, 5.5vw, 38px)', letterSpacing: '-0.025em', maxWidth: 640 }}>Browsing is free. Personalization and workflow are paid.</h1>
        <p className="muted" style={{ margin: '16px auto 0', fontSize: 15.5, lineHeight: 1.6, maxWidth: 560 }}>
          Public professor discovery stays free forever — it’s how Univya earns trust.
          Paid plans unlock matching and application workflow built on your research profile.
        </p>
      </div>

      <div className="uv-grid2" style={{ alignItems: 'stretch' }}>
        <div className="uv-card" style={{ borderRadius: 20, padding: 32, display: 'flex', flexDirection: 'column' }}>
          <span style={{ alignSelf: 'start', padding: '5px 14px', borderRadius: 999, background: 'var(--uv-surface2)', color: 'var(--uv-muted)', fontSize: 12, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>Free</span>
          <h2 style={{ margin: '16px 0 4px', fontSize: 22, letterSpacing: '-0.015em' }}>Public discovery</h2>
          <p className="muted" style={{ margin: '0 0 22px', fontSize: 14 }}>For every prospective research student.</p>
          <CheckList items={freeFeatures} />
          <Link className="button secondary" href="/professors" style={{ marginTop: 'auto', display: 'block', textAlign: 'center', padding: 13, borderRadius: 12, fontSize: 14.5 }}>Start searching</Link>
        </div>

        <div className="uv-deep" style={{ borderRadius: 20, padding: 32, display: 'flex', flexDirection: 'column' }}>
          <span style={{ alignSelf: 'start', padding: '5px 14px', borderRadius: 999, background: 'var(--uv-accent)', color: '#06241F', fontSize: 12, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase' }}>Pro · pricing coming soon</span>
          <h2 style={{ margin: '16px 0 4px', fontSize: 22, letterSpacing: '-0.015em' }}>Personalized workflow</h2>
          <p className="uv-deep-muted" style={{ margin: '0 0 22px', fontSize: 14 }}>For applicants who want research-fit matching and an organized outreach pipeline.</p>
          <CheckList items={paidFeatures} />
          <Link className="uv-btn-accent" href="/signup" style={{ marginTop: 'auto', display: 'block', textAlign: 'center', padding: 13, fontSize: 14.5 }}>Create your research profile</Link>
        </div>
      </div>

      <div className="uv-card" style={{ margin: '20px 0 64px', padding: '26px 30px', display: 'flex', gap: 18, alignItems: 'start' }}>
        <div style={{ width: 40, height: 40, flexShrink: 0, borderRadius: 12, background: 'var(--uv-accent-soft)', color: 'var(--uv-accent-text)', display: 'grid', placeItems: 'center', fontWeight: 800, fontSize: 16 }}>✓</div>
        <div>
          <h3 style={{ margin: '0 0 6px', fontSize: 16, letterSpacing: '-0.01em' }}>Trust comes first</h3>
          <p className="muted" style={{ margin: 0, fontSize: 14, lineHeight: 1.65 }}>
            Professors and universities never pay for ranking or visibility. Match scores measure
            <strong style={{ color: 'var(--uv-text)' }}> research fit</strong> — the overlap between your interests and a professor’s recent,
            source-backed work. They are not admission chances and never a guarantee of a reply.
          </p>
        </div>
      </div>
    </main>
  );
}
