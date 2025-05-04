'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  Command,
  CommandInput,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList
} from '@/components/ui/command';
import { Search } from 'lucide-react';

interface Supplement {
  name: string;
}

interface SupplementSearchProps {
  supplements: Array<Supplement>;
}

export function SupplementSearch({ supplements }: SupplementSearchProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const router = useRouter();

  const filteredSupplements = supplements
    .filter((supplement) => 
      supplement.name.toLowerCase().includes(query.toLowerCase())
    )
    .slice(0, 5); // Limit results to 5 for better performance

  function handleSupplementSelect(supplement: Supplement) {
    router.push(`/supplement/${encodeURIComponent(supplement.name)}`);
    setOpen(false);
    setQuery('');
  }

  return (
    <div className="relative w-full max-w-2xl mx-auto">
      <Command className="rounded-lg border shadow-md">
        <div className="flex items-center border-b px-4">
          <CommandInput
            value={query}
            onValueChange={setQuery}
            className="flex h-14 w-full rounded-md bg-transparent py-4 text-base outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
            placeholder="Search supplements..."
          />
        </div>
        {query.length > 0 && (
          <CommandList>
            <CommandEmpty>No supplements found.</CommandEmpty>
            <CommandGroup>
              {filteredSupplements.map((supplement) => (
                <CommandItem
                  key={supplement.name}
                  onSelect={() => handleSupplementSelect(supplement)}
                  className="cursor-pointer py-3 text-base"
                >
                  {supplement.name}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        )}
      </Command>
    </div>
  );
}