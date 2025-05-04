// src/app/supplement/[name]/not-found.tsx
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function SupplementNotFound() {
  return (
    <main className="container mx-auto p-4 md:p-8 lg:p-12 flex flex-col items-center justify-center min-h-[70vh]">
      <h1 className="text-3xl font-bold mb-4">Supplement Not Found</h1>
      <p className="mb-8 text-center max-w-md text-muted-foreground">
        Sorry, we couldn't find the supplement you were looking for. It may not exist in our database.
      </p>
      <Link href="/">
        <Button>Return to Supplement Explorer</Button>
      </Link>
    </main>
  );
}