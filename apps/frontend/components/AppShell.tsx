'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { getCurrentUser, getUserState, logoutUser } from '@/lib/api';
import { localStore } from '@/lib/local-store';
import { Avatar } from '@/components/ProfessorCard';
import { Icon } from '@/components/Icon';
import type { LocalUser } from '@/lib/types';

const studentNav = [
  { href: '/dashboard', label: 'Home', icon: 'home' as const },
  { href: '/match', label: 'Matches', icon: 'sparkle' as const },
  { href: '/professors', label: 'Discover', icon: 'compass' as const },
  { href: '/saved', label: 'Saved', icon: 'bookmark' as const },
];

const publicRoutes = new Set(['/', '/signin', '/signup']);

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<LocalUser | null>(null);
  const [open, setOpen] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setAuthChecked(false);

    const localUser = localStore.getUser();
    if (publicRoutes.has(pathname) && !localUser) {
      setAuthChecked(true);
      return () => { cancelled = true; };
    }

    getCurrentUser()
      .then(response => {
        if (cancelled) return;
        const localProfile = localStore.getProfile();
        const restored = {
          name: localProfile?.name || response.user.display_name,
          email: response.user.email,
          createdAt: response.user.created_at,
          role: response.user.role,
          photo_url: localProfile?.photo_url,
        };
        localStore.setUser(restored);
        setUser(restored);
        Promise.resolve(getUserState()).then(state => {
          if (cancelled || !state?.student_profile) return;
          const withProfile = {
            ...restored,
            name: state.student_profile.name || restored.name,
            photo_url: state.student_profile.photo_url || restored.photo_url,
          };
          localStore.setProfile(state.student_profile);
          localStore.setUser(withProfile);
          setUser(withProfile);
        }).catch(() => undefined);
        setAuthChecked(true);
        if (pathname === '/') router.replace('/dashboard');
      })
      .catch(() => {
        if (cancelled) return;
        localStore.clearPrivateState();
        setUser(null);
        setAuthChecked(true);
        if (!publicRoutes.has(pathname)) router.replace(`/signin?next=${encodeURIComponent(pathname)}`);
      });

    return () => { cancelled = true; };
  }, [pathname, router]);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    const syncProfilePhoto = () => {
      const localUser = localStore.getUser();
      const localProfile = localStore.getProfile();
      if (!localUser) return;
      const next = { ...localUser, name: localProfile?.name || localUser.name, photo_url: localProfile?.photo_url || localUser.photo_url };
      setUser(next);
    };
    window.addEventListener('profmatch:state', syncProfilePhoto);
    return () => window.removeEventListener('profmatch:state', syncProfilePhoto);
  }, []);

  const signOut = async () => {
    try {
      await logoutUser();
    } catch {
      // Still clear local browser state if the backend session is already gone.
    }
    localStore.clearPrivateState();
    setUser(null);
    router.push('/');
  };

  const nav = user?.role === 'admin' ? [...studentNav, { href: '/admin', label: 'Admin', icon: 'shield' as const }] : studentNav;
  const displayName = user?.name || 'Profile';

  if (publicRoutes.has(pathname) && !user) {
    return <main className="public-main">{children}</main>;
  }

  if (!authChecked && !publicRoutes.has(pathname)) {
    return <main className="public-main"><div className="page narrow"><div className="card"><p className="muted">Checking your session…</p></div></div></main>;
  }

  if (!user && !publicRoutes.has(pathname)) {
    return <main className="public-main"><div className="page narrow"><div className="card"><p className="muted">Redirecting to sign in…</p></div></div></main>;
  }

  return (
    <div className="app-shell">
      <header className="app-top-nav">
        <Link className="brand top-brand" href="/dashboard">
          <span className="brand-mark">PM</span><span>ProfMatch</span>
        </Link>

        <nav className="top-nav-links" aria-label="Primary navigation">
          {nav.map(item => (
            <Link key={item.href} className={`top-nav-link ${pathname === item.href || (item.href === '/match' && pathname === '/results') || (item.href === '/admin' && pathname.startsWith('/admin')) ? 'active' : ''}`} href={item.href}>
              <Icon name={item.icon} size={13} /> {item.label}
            </Link>
          ))}
        </nav>

        <div className="top-nav-actions">
          {user ? (
            <>
              <Link className="profile-link profile-link-with-photo" href="/profile"><Avatar name={displayName} photoUrl={user.photo_url} /> <span>{displayName}</span></Link>
              <button className="ghost small" onClick={signOut}>Sign Out</button>
            </>
          ) : (
            <>
              <Link className="button secondary" href="/signin">Sign in</Link>
              <Link className="button primary" href="/signup">Sign up</Link>
            </>
          )}
          <button className="ghost mobile-nav-toggle" aria-label="Open navigation menu" aria-expanded={open} aria-controls="mobile-navigation" onClick={() => setOpen(v => !v)}><Icon name={open ? 'close' : 'menu'} size={16} /></button>
        </div>
      </header>
      {open && (
        <nav id="mobile-navigation" className="mobile-menu" aria-label="Mobile navigation">
          {nav.map(item => <Link key={item.href} className={pathname === item.href || (item.href === '/admin' && pathname.startsWith('/admin')) ? 'active' : ''} href={item.href}><Icon name={item.icon} size={14} /> {item.label}</Link>) }
          <Link href="/profile" className="mobile-profile-link"><Avatar name={displayName} photoUrl={user?.photo_url} /> Profile</Link>
          {user && <button className="ghost" onClick={signOut}>Sign Out</button>}
        </nav>
      )}
      <main className="main">{children}</main>
    </div>
  );
}

