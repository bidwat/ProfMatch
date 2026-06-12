'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Button, Input, Label, TextField } from '@heroui/react';
import { registerUser } from '@/lib/api';
import { localStore } from '@/lib/local-store';

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim() || !form.email.trim() || form.password.length < 8) {
      return setError('Enter your name, email, and a password with at least 8 characters.');
    }
    setSubmitting(true);
    setError('');
    try {
      const response = await registerUser({
        display_name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
      });
      localStore.setUser({ name: response.user.display_name, email: response.user.email, createdAt: response.user.created_at, role: response.user.role });
      router.push('/profile');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create account.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page narrow">
      <div className="card" style={{ maxWidth: 430, margin: '60px auto' }}>
        <Link className="accent small-text" href="/">← Back to home</Link>
        <div className="brand" style={{ padding: 0, marginTop: 14 }}><span>Univya<span className="brand-dot">.</span></span></div>
        <h2>Create your profile</h2>
        <p className="muted" style={{ marginBottom: 20 }}>Start your professor matching workspace with a few account details.</p>
        <form className="form" onSubmit={submit}>
          <TextField>
            <Label>Full name</Label>
            <Input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} placeholder="Jordan Lee" />
          </TextField>
          <TextField type="email">
            <Label>Email</Label>
            <Input value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} placeholder="you@university.edu" />
          </TextField>
          <TextField type="password">
            <Label>Password</Label>
            <Input value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} placeholder="At least 8 characters" />
          </TextField>
          {error && <div className="error">{error}</div>}
          <Button type="submit" isDisabled={submitting} isPending={submitting}>{submitting ? 'Creating account…' : 'Continue to profile →'}</Button>
        </form>
        <p className="muted small-text" style={{ marginTop: 18 }}>Already have an account? <Link className="accent" href="/signin">Sign in</Link></p>
      </div>
    </div>
  );
}
