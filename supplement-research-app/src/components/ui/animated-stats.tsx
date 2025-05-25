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
    // Auto-animate on mount after a brief delay
    const timer = setTimeout(() => {
      setAnimated(true);
    }, 500);
    return () => clearTimeout(timer);
  }, []);

  if (!mounted) {
    return (
      <div className="flex justify-center gap-8">
        <div className="text-center">
          <div className="text-3xl font-bold text-primary" style={{ fontVariantNumeric: 'tabular-nums' }}>
            0
          </div>
          <div className="text-sm text-muted-foreground">Supplements</div>
        </div>
        <div className="w-px bg-border h-12"></div>
        <div className="text-center">
          <div className="text-3xl font-bold text-primary" style={{ fontVariantNumeric: 'tabular-nums' }}>
            0
          </div>
          <div className="text-sm text-muted-foreground">Research Papers</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-center gap-8">
      <div className="text-center">
        <div className="text-3xl font-bold text-primary" style={{ fontVariantNumeric: 'tabular-nums' }}>
          <NumberFlow 
            value={animated ? totalSupplements : 0}
            format={{ useGrouping: true }}
            locales="en-US"
            transformTiming={{ duration: 1000, easing: 'ease-out' }}
            spinTiming={{ duration: 1000, easing: 'ease-out' }}
            opacityTiming={{ duration: 300, easing: 'ease-out' }}
          />
        </div>
        <div className="text-sm text-muted-foreground">Supplements</div>
      </div>
      <div className="w-px bg-border h-12"></div>
      <div className="text-center">
        <div className="text-3xl font-bold text-primary" style={{ fontVariantNumeric: 'tabular-nums' }}>
          <NumberFlow 
            value={animated ? totalPapers : 0}
            format={{ useGrouping: true }}
            locales="en-US"
            transformTiming={{ duration: 1200, easing: 'ease-out' }}
            spinTiming={{ duration: 1200, easing: 'ease-out' }}
            opacityTiming={{ duration: 300, easing: 'ease-out' }}
          />
        </div>
        <div className="text-sm text-muted-foreground">Research Papers</div>
      </div>
    </div>
  );
}