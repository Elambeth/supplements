// src/components/ui/animated-stats.tsx
'use client';
import { useState, useEffect } from 'react';
import NumberFlow from '@number-flow/react';

interface AnimatedStatsProps {
  totalSupplements: number;
  totalPapers: number;
}

export function AnimatedStats({ totalSupplements, totalPapers }: AnimatedStatsProps) {
  const [mounted, setMounted] = useState(false);
  const [animated, setAnimated] = useState(false);

  // Ensure component is mounted before showing animations
  useEffect(() => {
    setMounted(true);
    // Auto-animate on mount after a shorter delay for faster feel
    const timer = setTimeout(() => {
      setAnimated(true);
    }, 10); // Reduced from 500ms to 200ms
    return () => clearTimeout(timer);
  }, []);

  if (!mounted) {
    return (
      <div className="flex flex-col sm:flex-row gap-6 sm:gap-12 justify-center items-center">
        <div className="text-center">
          <div className="text-3xl md:text-4xl font-bold text-primary mb-2" style={{ fontVariantNumeric: 'tabular-nums' }}>
            0
          </div>
          <div className="text-sm md:text-base text-muted-foreground font-medium">Supplements Tracked</div>
        </div>
        <div className="hidden sm:block w-px bg-border h-16"></div>
        <div className="text-center">
          <div className="text-3xl md:text-4xl font-bold text-primary mb-2" style={{ fontVariantNumeric: 'tabular-nums' }}>
            0
          </div>
          <div className="text-sm md:text-base text-muted-foreground font-medium">Research Papers</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col sm:flex-row gap-6 sm:gap-12 justify-center items-center">
      <div className="text-center">
        <div className="text-3xl md:text-4xl font-bold text-primary mb-2" style={{ fontVariantNumeric: 'tabular-nums' }}>
          <NumberFlow 
            value={animated ? totalSupplements : 0}
            format={{ useGrouping: true }}
            locales="en-US"
            transformTiming={{ duration: 6, easing: 'ease-out' }} // Faster: 600ms instead of 1000ms
            spinTiming={{ duration: 1000, easing: 'ease-out' }}
            opacityTiming={{ duration: 200, easing: 'ease-out' }}
          />
        </div>
        <div className="text-sm md:text-base text-muted-foreground font-medium">Supplements Tracked</div>
      </div>
      <div className="hidden sm:block w-px bg-border h-16"></div>
      <div className="text-center">
        <div className="text-3xl md:text-4xl font-bold text-primary mb-2" style={{ fontVariantNumeric: 'tabular-nums' }}>
          <NumberFlow 
            value={animated ? totalPapers : 0}
            format={{ useGrouping: true }}
            locales="en-US"
            transformTiming={{ duration: 700, easing: 'ease-out' }} // Slightly staggered: 700ms
            spinTiming={{ duration: 700, easing: 'ease-out' }}
            opacityTiming={{ duration: 200, easing: 'ease-out' }}
          />
        </div>
        <div className="text-sm md:text-base text-muted-foreground font-medium">Research Papers</div>
      </div>
    </div>
  );
}