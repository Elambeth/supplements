// src/components/ui/lazy-supplement-list.tsx
'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getSupplementsByFirstLetter } from '@/lib/supabase';

interface SupplementsByLetter {
  [key: string]: string[];
}

export function LazySupplementList() {
  const [supplementsByLetter, setSupplementsByLetter] = useState<SupplementsByLetter | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [hasLoaded, setHasLoaded] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const [entry] = entries;
        if (entry.isIntersecting && !hasLoaded && !isLoading) {
          loadSupplements();
        }
      },
      {
        threshold: 0.1, // Trigger when 10% of the component is visible
        rootMargin: '100px', // Start loading 100px before it comes into view
      }
    );

    if (sectionRef.current) {
      observer.observe(sectionRef.current);
    }

    return () => {
      if (sectionRef.current) {
        observer.unobserve(sectionRef.current);
      }
    };
  }, [hasLoaded, isLoading]);

  const loadSupplements = async () => {
    if (hasLoaded || isLoading) return;
    
    setIsLoading(true);
    try {
      const data = await getSupplementsByFirstLetter();
      setSupplementsByLetter(data);
      setHasLoaded(true);
    } catch (error) {
      console.error('Error loading supplements:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const renderLoadingSkeleton = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="space-y-3">
          <Skeleton className="h-6 w-8" />
          <div className="flex flex-wrap gap-2">
            {Array.from({ length: Math.floor(Math.random() * 8) + 4 }).map((_, j) => (
              <Skeleton key={j} className="h-6 w-20" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );

  const renderSupplements = () => {
    if (!supplementsByLetter) return null;

    const sortedKeys = Object.keys(supplementsByLetter).sort((a, b) => {
      if (a === '0-9') return -1;
      if (b === '0-9') return 1;
      return a.localeCompare(b);
    });

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {sortedKeys.map((letterKey) => (
          <div key={letterKey} className="space-y-3 animate-in fade-in-50 duration-300">
            <h3 className="text-xl font-semibold text-primary border-b border-border pb-2">
              {letterKey.toUpperCase()}
            </h3>
            <div className="flex flex-wrap gap-2">
              {supplementsByLetter[letterKey].map((supplement) => (
                <Link 
                  href={`/supplement/${encodeURIComponent(supplement)}`} 
                  key={supplement} 
                  legacyBehavior
                >
                  <Badge
                    variant="outline"
                    className="cursor-pointer hover:bg-primary hover:text-primary-foreground transition-all duration-200 text-sm px-3 py-1 rounded-lg hover:scale-105"
                  >
                    {supplement}
                  </Badge>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <section ref={sectionRef} className="container mx-auto px-4 py-16 max-w-6xl">
      <Card className="shadow-lg">
        <CardContent className="pt-8">
          <div className="text-center mb-8">
            <h2 className="text-3xl font-bold mb-4">All Interventions</h2>
            <p className="text-muted-foreground text-lg">
              Browse our complete database of supplements and interventions
            </p>
          </div>
          
          {isLoading && renderLoadingSkeleton()}
          {hasLoaded && renderSupplements()}
          
          {!hasLoaded && !isLoading && (
            <div className="text-center py-12">
              <div className="animate-pulse">
                <div className="text-muted-foreground">Loading supplements...</div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}