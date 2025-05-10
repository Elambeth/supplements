import Link from 'next/link';
import { Leaf } from 'lucide-react';

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between max-w-6xl px-8">
        <Link href="/" className="flex items-center space-x-2">
          <span className="font-bold text-lg tracking-tight">SupplementDB</span>
        </Link>
        
        <nav className="flex items-center space-x-10">
          <Link
            href="/"
            className="text-sm font-medium transition-colors hover:text-primary"
          >
            Home
          </Link>
          <Link
            href="/research-ranking"
            className="text-sm font-medium transition-colors hover:text-primary"
          >
            Research-Rankings
          </Link>
          <Link
            href="/research-methodology"
            target="_blank"
            className="text-sm font-medium transition-colors hover:text-primary"
          >
            Methodology
          </Link>
        </nav>
      </div>
    </header>
  );
}