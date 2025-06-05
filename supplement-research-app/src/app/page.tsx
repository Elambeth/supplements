// src/app/page.tsx
import Link from 'next/link';
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { SupplementSearch } from "@/components/ui/supplement-search";
import { AnimatedStats } from "@/components/ui/animated-stats";
import { 
  getSupplementsByFirstLetter, 
  getSupplementsForSearch, // ✅ Import the new optimized function
  getDatabaseStats 
} from '@/lib/supabase';

// ✅ App Router ISR - revalidate every hour
export const revalidate = 3600;

// Define types for supplement data
interface Supplement {
  id: number;
  name: string;
  description: string | null;
  is_popular: boolean;
  last_research_check: string;
  sentiment_score: number | null;
  created_at: string;
}

// ✅ Add type for search-optimized data
interface SupplementSearchData {
  id: number;
  name: string;
}

export default async function HomePage() {
  // ✅ Fetch data in parallel for better performance
  const [supplementsByLetter, supplementsForSearch, stats] = await Promise.all([
    getSupplementsByFirstLetter(),
    getSupplementsForSearch(), // ✅ Use optimized function
    getDatabaseStats()
  ]);
  
  // Get the sorted keys for alphabetical sections (like '0-9', 'a', 'b', ...)
  const sortedKeys = Object.keys(supplementsByLetter).sort((a, b) => {
    // Ensure '0-9' comes first, then alphabetical
    if (a === '0-9') return -1;
    if (b === '0-9') return 1;
    return a.localeCompare(b);
  });

  return (
    <main className="container mx-auto px-4 py-12 max-w-6xl">
      <div className="space-y-12">
        {/* Hero Section with Larger Title */}
        <section className="text-center space-y-6 mb-16">
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight">Supplement & Intervention Explorer</h1>
          <p className="text-muted-foreground text-lg max-w-3xl mx-auto">
            Discover and learn about various supplements and health interventions, backed by scientific research.
          </p>
          
          {/* Animated Stats Display */}
          <AnimatedStats 
            totalSupplements={stats.totalSupplements} 
            totalPapers={stats.totalPapers} 
          />
          
          {/* Larger Search Component */}
          <div className="mt-12 max-w-3xl mx-auto">
            <SupplementSearch supplements={supplementsForSearch} /> {/* ✅ Use optimized data */}
          </div>
        </section>

        {/* A-Z Interventions Section */}
        <section className="mt-12">
          <Card>
            <CardContent className="pt-6">
              <h2 className="text-xl font-semibold mb-4 flex items-center">
                <span className="inline-block w-2 h-2 bg-primary rounded-full mr-2"></span>
                All Interventions (A-Z)
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {sortedKeys.map((letterKey) => (
                  <div key={letterKey} className="mb-2">
                    <h3 className="text-lg font-lg mb-2 uppercase flex items-center">
                      <span className="text-secondary-foreground font-semibold mr-8">
                        {letterKey}
                      </span>
                    </h3>
                    <div className="flex flex-wrap gap-1.5">
                      {supplementsByLetter[letterKey].map((supplement) => (
                        <Link href={`/supplement/${encodeURIComponent(supplement)}`} key={supplement} legacyBehavior>
                          <Badge
                            variant="outline"
                            className="cursor-pointer hover:bg-accent hover:text-accent-foreground transition-colors text-xs px-2 py-0.5 rounded"
                          >
                            {supplement}
                          </Badge>
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}