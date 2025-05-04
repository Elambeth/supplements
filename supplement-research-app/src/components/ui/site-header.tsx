import Link from 'next/link';
import { Leaf } from 'lucide-react';

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between max-w-6xl px-4">
        <Link href="/" className="flex items-center space-x-2">
          <Leaf className="h-5 w-5 text-primary" />
          <span className="font-bold text-lg tracking-tight">SupplementDB</span>
        </Link>
        
        <nav className="flex items-center space-x-6">
          <Link
            href="/"
            className="text-sm font-medium transition-colors hover:text-primary"
          >
            Home
          </Link>
          <Link
            href="https://pubmed.ncbi.nlm.nih.gov/"
            target="_blank"
            className="text-sm font-medium text-muted-foreground transition-colors hover:text-primary"
          >
            Research
          </Link>
        </nav>
      </div>
    </header>
  );
}