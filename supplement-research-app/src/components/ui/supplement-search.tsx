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

// List of placeholder options to cycle through
const PLACEHOLDER_OPTIONS = [
  "Help me not feel like shit...", 
  "What's gonna make me swole?",
  "Search for energy that isn't coffee...",
  "Find vitamins I'll forget to take...",
  "Help me pretend I have my shit together...",
  "Search for legal performance enhancers...",
  "What's gonna make my joints stop creaking?",
  "Find something for my sad desk body...",
  "What do I need to not feel 100 years old?",
  "Search for willpower in pill form...",
  "Find something to fix my life...",
  "Find something that actually fucking works..."
];

// Custom typing component that types, waits, deletes, then calls onComplete
function CyclingTypingText({ 
  text, 
  onComplete, 
  className 
}: { 
  text: string; 
  onComplete: () => void; 
  className?: string; 
}) {
  const [displayText, setDisplayText] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [showCursor, setShowCursor] = useState(true);

  useEffect(() => {
    let timeout: NodeJS.Timeout;
    
    if (!isDeleting) {
      // Typing phase
      if (displayText.length < text.length) {
        timeout = setTimeout(() => {
          setDisplayText(text.slice(0, displayText.length + 1));
        }, 60); // Typing speed
      } else {
        // Finished typing, wait then start deleting
        timeout = setTimeout(() => {
          setIsDeleting(true);
        }, 1500); // Wait before deleting
      }
    } else {
      // Deleting phase
      if (displayText.length > 0) {
        timeout = setTimeout(() => {
          setDisplayText(displayText.slice(0, -1));
        }, 30); // Deletion speed (faster)
      } else {
        // Finished deleting, call onComplete to switch to next phrase
        onComplete();
      }
    }

    return () => clearTimeout(timeout);
  }, [displayText, isDeleting, text, onComplete]);

  // Cursor blinking effect
  useEffect(() => {
    const interval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);
    return () => clearInterval(interval);
  }, []);

  // Reset state when text changes (new phrase)
  useEffect(() => {
    setDisplayText('');
    setIsDeleting(false);
  }, [text]);

  return (
    <span className={className}>
      {displayText}
      <span className={showCursor ? "opacity-100" : "opacity-0"}>|</span>
    </span>
  );
}

export function SupplementSearch({ supplements }: SupplementSearchProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [currentPlaceholderIndex, setCurrentPlaceholderIndex] = useState(0);
  const [isFocused, setIsFocused] = useState(false);
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

  // Handle cycling to next placeholder
  const handleTypingComplete = () => {
    setCurrentPlaceholderIndex((prev) => 
      (prev + 1) % PLACEHOLDER_OPTIONS.length
    );
  };

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
            "flex items-center px-4 transition-all duration-300 border-0 border-b-0 relative",
            isExpanded ? "pb-3 pt-3" : "pb-2 pt-2"
          )}
          onMouseEnter={() => setIsExpanded(true)}
          onMouseLeave={() => !open && !isFocused && setIsExpanded(false)}
          style={{ borderBottom: 'none' }}
        >
          <CommandInput
            ref={inputRef}
            value={query}
            onValueChange={setQuery}
            onFocus={() => {
              setIsExpanded(true);
              setIsFocused(true);
            }}
            onBlur={() => {
              if (!query) setIsExpanded(false);
              setIsFocused(false);
            }}
            className="flex h-14 w-full bg-transparent py-4 text-lg placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-0 !border-0 !border-none !outline-none !border-b-0 [&_*]:!border-0 [&_*]:!border-none [&_*]:!outline-none [&_*]:!border-b-0"
            placeholder="" // Remove static placeholder
            style={{ border: 'none', borderBottom: 'none', outline: 'none' }}
          />
          
          {/* Custom Typing Effect Placeholder - only show when input is empty and not focused */}
          {!query && !isFocused && (
            <div className="absolute left-16 top-1/2 transform -translate-y-1/2 pointer-events-none">
              <CyclingTypingText
                text={PLACEHOLDER_OPTIONS[currentPlaceholderIndex]}
                onComplete={handleTypingComplete}
                className="text-lg text-muted-foreground/50 font-sans"
              />
            </div>
          )}
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