// src/app/research-ranking/page.tsx
import Link from 'next/link';
import { Metadata } from 'next';
import { ArrowLeft, BookOpen } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { getAllSupplementsWithResearch } from '@/lib/supabase';
import { ResearchTable } from '@/components/ui/research-table';

export const metadata: Metadata = {
  title: 'Research Ranking | Supplement Database',
  description: 'Explore supplements ranked by research volume'
};

export default async function ResearchRankingPage() {
  // Fetch all supplements with their research data
  const supplements = await getAllSupplementsWithResearch();
  
  // Sort supplements by research count (descending)
  const sortedSupplements = supplements
    .filter(supp => supp.supplement_research && supp.supplement_research.length > 0)
    .sort((a, b) => {
      const aCount = a.supplement_research?.[0]?.research_count || 0;
      const bCount = b.supplement_research?.[0]?.research_count || 0;
      return bCount - aCount;
    });

  return (
    <main className="container max-w-6xl mx-auto px-4 py-8">
      <div className="mb-6">
        <Link href="/" className="inline-flex items-center text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to all supplements
        </Link>
      </div>

      <div className="mb-6">
        <h1 className="text-3xl font-bold">Research Ranking</h1>
        <p className="text-muted-foreground mt-2">
          Supplements ranked by research volume in the PubMed database
        </p>
      </div>

      <Card className="border-none shadow-md mb-6">
        <CardContent>
          <ResearchTable supplements={sortedSupplements} />
        </CardContent>
      </Card>

      {/* Additional stats card */}
      <Card className="border-none shadow-md bg-gradient-to-r from-blue-50 to-purple-50">
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <h3 className="text-lg font-medium mb-2">Total Supplements</h3>
              <p className="text-3xl font-bold">{supplements.length}</p>
            </div>
            
            <div>
              <h3 className="text-lg font-medium mb-2">With Research Data</h3>
              <p className="text-3xl font-bold">{sortedSupplements.length}</p>
            </div>
            
            <div>
              <h3 className="text-lg font-medium mb-2">Top Researched</h3>
              {sortedSupplements.length > 0 ? (
                <div className="flex items-center">
                  <Link href={`/supplement/${encodeURIComponent(sortedSupplements[0].name)}`}>
                    <span className="text-primary hover:underline">
                      {sortedSupplements[0].name}
                    </span>
                  </Link>
                  <span className="mx-2 text-muted-foreground">•</span>
                  <span className="text-muted-foreground">
                    {sortedSupplements[0].supplement_research?.[0]?.research_count.toLocaleString()} studies
                  </span>
                </div>
              ) : (
                <p className="text-muted-foreground">No data available</p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}