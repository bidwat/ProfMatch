'use client';

import type { LocalUser, MatchResponse, StudentProfile } from './types';

const keys = {
  user: 'profmatch:user',
  profile: 'profmatch:studentProfile',
  matches: 'profmatch:lastMatches',
  saved: 'profmatch:savedProfessorIds',
  tracker: 'profmatch:tracker',
};

function read<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) as T : fallback;
  } catch {
    return fallback;
  }
}

function write<T>(key: string, value: T) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(key, JSON.stringify(value));
  window.dispatchEvent(new Event('profmatch:state'));
}

export const localStore = {
  getUser: () => read<LocalUser | null>(keys.user, null),
  setUser: (user: LocalUser | null) => {
    if (user) write(keys.user, user);
    else if (typeof window !== 'undefined') { window.localStorage.removeItem(keys.user); window.dispatchEvent(new Event('profmatch:state')); }
  },
  getProfile: () => read<StudentProfile | null>(keys.profile, null),
  setProfile: (profile: StudentProfile) => write(keys.profile, profile),
  getMatches: () => read<MatchResponse | null>(keys.matches, null),
  setMatches: (matches: MatchResponse) => write(keys.matches, matches),
  getSaved: () => read<number[]>(keys.saved, []),
  setSaved: (ids: number[]) => write(keys.saved, ids),
  getTracker: () => read<any[]>(keys.tracker, []),
  setTracker: (rows: any[]) => write(keys.tracker, rows),
  clearPrivateState: () => {
    if (typeof window === 'undefined') return;
    Object.values(keys).forEach(key => window.localStorage.removeItem(key));
    window.dispatchEvent(new Event('profmatch:state'));
  },
};
