import type { Metadata } from 'next';
import { Plus_Jakarta_Sans } from 'next/font/google';
import './globals.css';
import AppShell from '@/components/AppShell';

const jakarta = Plus_Jakarta_Sans({ subsets: ['latin'], variable: '--font-jakarta', weight: ['400', '500', '600', '700', '800'] });

export const metadata: Metadata = {
  title: 'Univya',
  description: 'Research advisor discovery with evidence-backed professor profiles and research-fit matching',
};

// Apply the persisted theme before first paint to avoid a flash.
const themeInit = `(function(){try{var t=localStorage.getItem('univya-theme')||'light';document.documentElement.dataset.theme=t;document.documentElement.classList.toggle('dark',t==='dark');document.documentElement.classList.toggle('light',t!=='dark');}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="light" data-theme="light" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
      </head>
      <body className={jakarta.variable}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
