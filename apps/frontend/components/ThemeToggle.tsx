'use client';

import { useEffect, useState } from 'react';

function applyTheme(theme: 'light' | 'dark') {
  document.documentElement.dataset.theme = theme;
  document.documentElement.classList.toggle('dark', theme === 'dark');
  document.documentElement.classList.toggle('light', theme !== 'dark');
  try { localStorage.setItem('univya-theme', theme); } catch { /* private mode */ }
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    try {
      const saved = localStorage.getItem('univya-theme');
      if (saved === 'dark') setTheme('dark');
    } catch { /* private mode */ }
  }, []);

  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    applyTheme(next);
  };

  return (
    <button type="button" className="theme-toggle" aria-label="Toggle dark mode" onClick={toggle}>
      {theme === 'dark' ? '☀' : '☾'}
    </button>
  );
}
