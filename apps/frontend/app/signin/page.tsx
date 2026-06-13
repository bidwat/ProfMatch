'use client';

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Button, Input, Label, TextField } from '@heroui/react';
import { ThemeToggle } from '@/components/ThemeToggle';
import { findMatches, getCurrentUser, getUserState, loginUser, patchUserState } from '@/lib/api';
import { localStore } from '@/lib/local-store';
import type { LocalUser } from '@/lib/types';

export default function SigninPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [redirecting, setRedirecting] = useState(false);

  useEffect(() => {
    if (!localStore.getUser()) return;
    getCurrentUser()
      .then(response => {
        const restored = { name: response.user.display_name, email: response.user.email, createdAt: response.user.created_at };
        localStore.setUser(restored);
      })
      .catch(() => undefined);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const response = await loginUser({ email: form.email, password: form.password });
      localStore.setUser({ name: response.user.display_name, email: response.user.email, createdAt: response.user.created_at, role: response.user.role });
      // Auth succeeded — leave the form and show the splash while we finish setup + navigate.
      setRedirecting(true);
      const state = await getUserState().catch(() => null);
      const next = searchParams.get('next');
      if (state?.student_profile) {
        try {
          const matchResponse = await findMatches(state.student_profile);
          localStore.setMatches(matchResponse);
          await patchUserState({ last_match_response: matchResponse });
        } catch {
          // Login should succeed even if match refresh temporarily fails.
        }
        router.push(next && next.startsWith('/') ? next : '/dashboard');
      } else {
        router.push('/profile');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign in.');
      setRedirecting(false);
      setSubmitting(false);
    }
  }

  if (redirecting) {
    return (
      <div className="splash" role="status" aria-live="polite">
        <div className="splash-inner">
          <div className="brand"><span>Univya<span className="brand-dot">.</span></span></div>
          <div className="splash-spinner" aria-hidden="true" />
          <p className="splash-msg">Signing you in and refreshing your matches…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page narrow">
      <div className="row between" style={{ maxWidth: 430, margin: '20px auto 0' }}>
        <Link className="muted small-text" href="/">← Back to home</Link>
        <ThemeToggle />
      </div>
      <div className="card" style={{ maxWidth: 430, margin: '18px auto 60px', borderRadius: 20, padding: 36 }}>
        <div className="brand" style={{ padding: 0, fontSize: 21 }}><span>Univya<span className="brand-dot">.</span></span></div>
        <h2>Welcome back</h2>
        <p className="muted" style={{ marginBottom: 20 }}>Sign in to continue building your professor shortlist.</p>
        <form className="form" onSubmit={submit} style={{ marginTop: 16 }}>
          <TextField type="email">
            <Label>Email</Label>
            <Input value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} placeholder="you@university.edu" />
          </TextField>
          <TextField type="password">
            <Label>Password</Label>
            <Input value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} placeholder="Password" />
          </TextField>
          {error && <div className="error">{error}</div>}
          <Button type="submit" isDisabled={submitting} isPending={submitting}>{submitting ? 'Signing in and refreshing matches…' : 'Sign in →'}</Button>
        </form>
        <p className="muted small-text" style={{ marginTop: 18 }}>Need an account? <Link className="accent" href="/signup">Create one</Link></p>
      </div>
    </div>
  );
}
