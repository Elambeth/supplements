// src/app/page.tsx
import { SupplementSearch } from "@/components/ui/supplement-search";
import { AnimatedStats } from "@/components/ui/animated-stats";
import { LazySupplementList } from "@/components/ui/lazy-supplement-list";
import { 
  getSupplementsForSearch,
  getDatabaseStats 
} from '@/lib/supabase';

// App Router ISR - revalidate every hour
export const revalidate = 3600;

interface SupplementSearchData {
  id: number;
  name: string;
}

export default async function HomePage() {
  // Only fetch essential data for initial page load
  const [supplementsForSearch, stats] = await Promise.all([
    getSupplementsForSearch(),
    getDatabaseStats()
  ]);

  return (
    <main className="min-h-screen">
      {/* Hero Section - Full Viewport Height */}
      <section className="min-h-screen flex flex-col justify-center items-center px-4 relative">
        <div className="container mx-auto max-w-6xl text-center space-y-8">
          
          {/* Main Title */}
          <div className="space-y-6">
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight">
              Supplement & Intervention Explorer
            </h1>
            <p className="text-muted-foreground text-lg md:text-xl max-w-4xl mx-auto leading-relaxed">
              Discover and learn about various supplements and health interventions, backed by scientific research.
            </p>
          </div>
          
          {/* Search Component - Larger and More Prominent */}
          <div className="max-w-4xl mx-auto">
            <SupplementSearch supplements={supplementsForSearch} />
          </div>
          
          {/* Animated Stats Display */}
          <div className="py-6">
            <AnimatedStats 
              totalSupplements={stats.totalSupplements} 
              totalPapers={stats.totalPapers} 
            />
          </div>
          
          {/* Scroll Indicator */}
          <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-bounce">
            <div className="w-6 h-10 border-2 border-muted-foreground rounded-full flex justify-center">
              <div className="w-1 h-3 bg-muted-foreground rounded-full mt-2"></div>
            </div>
          </div>
        </div>
      </section>

      {/* Lazy-Loaded A-Z Interventions Section */}
      <LazySupplementList />
    </main>
  );
}