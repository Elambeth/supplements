import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { SiteHeader } from '@/components/ui/site-header';
import { SiteFooter } from '@/components/ui/site-footer';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Supplement Explorer',
  description: 'Explore supplements and health interventions with scientific research',
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen flex flex-col antialiased bg-gradient-to-br from-background via-background/95 to-background/90`}>
        <SiteHeader />
        <div className="flex-1">{children}</div>
        <SiteFooter />
      </body>
    </html>
  );
}