import type { Metadata } from 'next';
import { DM_Sans, Rubik } from 'next/font/google';
import './globals.css';
import AppShell from '@/components/AppShell';

const dmSans = DM_Sans({ subsets: ['latin'], variable: '--font-dm-sans' });
const rubik = Rubik({ subsets: ['latin'], variable: '--font-rubik' });

export const metadata: Metadata = {
  title: 'ProfMatch',
  description: 'Research advisor discovery with evidence-backed professor profiles and research-fit matching',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="light" data-theme="light">
      <body className={`${dmSans.variable} ${rubik.variable}`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
