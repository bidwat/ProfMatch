'use client';

import Link from 'next/link';
import { Card, Chip } from '@heroui/react';

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

export default function PricingPage() {
  return (
    <div className="page narrow">
      <div style={{ textAlign: 'center', margin: '40px 0 28px' }}>
        <h1 style={{ fontSize: 34 }}>Browsing is free. Personalization and workflow are paid.</h1>
        <p className="muted" style={{ maxWidth: 620, margin: '10px auto 0', lineHeight: 1.65 }}>
          Public professor discovery stays free forever — it is how ProfMatch earns trust.
          Paid plans unlock matching and application workflow built on your research profile.
        </p>
      </div>

      <div className="grid two" style={{ alignItems: 'stretch' }}>
        <Card style={{ padding: 24 }}>
          <Chip>Free</Chip>
          <h2 style={{ marginTop: 12 }}>Public discovery</h2>
          <p className="muted">For every prospective research student.</p>
          <ul style={{ margin: '16px 0 20px', padding: 0, listStyle: 'none', display: 'grid', gap: 9 }}>
            {freeFeatures.map(f => <li key={f} style={{ paddingLeft: 18, position: 'relative' }}><span style={{ position: 'absolute', left: 0, color: 'var(--olive-400)' }}>✓</span>{f}</li>)}
          </ul>
          <Link className="button secondary" href="/professors">Start searching</Link>
        </Card>

        <Card style={{ padding: 24, borderColor: 'var(--gold-300)' }}>
          <Chip color="accent">Pro · pricing coming soon</Chip>
          <h2 style={{ marginTop: 12 }}>Personalized workflow</h2>
          <p className="muted">For applicants who want research-fit matching and an organized outreach pipeline.</p>
          <ul style={{ margin: '16px 0 20px', padding: 0, listStyle: 'none', display: 'grid', gap: 9 }}>
            {paidFeatures.map(f => <li key={f} style={{ paddingLeft: 18, position: 'relative' }}><span style={{ position: 'absolute', left: 0, color: 'var(--gold-300)' }}>✓</span>{f}</li>)}
          </ul>
          <Link className="button primary" href="/signup">Create your research profile</Link>
        </Card>
      </div>

      <div className="card soft" style={{ marginTop: 24 }}>
        <h3>Trust comes first</h3>
        <p className="muted" style={{ lineHeight: 1.65, marginTop: 8 }}>
          Professors and universities never pay for ranking or visibility. Match scores measure
          <b> research fit</b> — the overlap between your interests and a professor&apos;s recent,
          source-backed work. They are not admission chances and never a guarantee of a reply.
        </p>
      </div>
    </div>
  );
}
