'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Search } from 'lucide-react';
import { 
  Command,
  CommandInput,
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList
} from '@/components/ui/command';
import { cn } from '@/lib/utils';

interface Supplement {
  name: string;
}

interface SupplementSearchProps {
  supplements: Array<Supplement>;
}

export function SupplementSearch({ supplements }: SupplementSearchProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const router = useRouter();
  const commandRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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

  // Handle container click to focus input
  const handleContainerClick = (e: React.MouseEvent) => {
    if (inputRef.current && e.target !== inputRef.current) {
      inputRef.current.focus();
    }
  };

  // Show dropdown when query exists
  useEffect(() => {
    setOpen(query.length > 0);
  }, [query]);

  return (
    <div className="relative w-full max-w-2xl mx-auto">
      <Command 
        ref={commandRef} 
        className={cn(
          "rounded-xl border shadow-md transition-all duration-300",
        )}
        onClick={handleContainerClick}
      >
        <div 
          className={cn(
            "flex items-center px-4 transition-all duration-300",
            isExpanded ? "pb-3 pt-3" : "pb-2 pt-2"
          )}
          onMouseEnter={() => setIsExpanded(true)}
          onMouseLeave={() => !open && setIsExpanded(false)}
        >
          <CommandInput
            ref={inputRef}
            value={query}
            onValueChange={setQuery}
            onFocus={() => setIsExpanded(true)}
            onBlur={() => !query && setIsExpanded(false)}
            className="flex h-14 w-full bg-transparent py-4 text-lg placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-0"
            placeholder="Search..."
          />
        </div>
        {open && (
          <CommandList className="max-h-80 overflow-auto">
            <CommandEmpty className="py-6 text-center text-sm">
              No supplements found.
            </CommandEmpty>
            <CommandGroup>
              {filteredSupplements.map((supplement) => (
                <CommandItem
                  key={supplement.name}
                  onSelect={() => handleSupplementSelect(supplement)}
                  className="cursor-pointer py-3 text-base hover:bg-accent hover:text-accent-foreground"
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