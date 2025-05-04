// src/app/supplement/[name]/page.tsx
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, ExternalLink, ThumbsUp, ThumbsDown, Calendar, BookOpen, FileText } from 'lucide-react';
import { getSupplementWithResearch } from '@/lib/supabase';

// Define types for supplement data
interface Supplement {
  id: number;
  name: string;
  description: string | null;
  is_popular: boolean;
  last_research_check: string;
  sentiment_score: number | null;
  created_at: string;
  supplement_research?: {
    research_count: number;
    retrieved_count: number;
    search_date: string;
    last_updated: string;
    query: string;
    rank_position: number;
    rank_total: number;
    rank_percentile: number;
  }[];
}

// This enables dynamic segments to be statically generated at build time
export const dynamicParams = true;

// Define the props for the page component
interface SupplementPageProps {
  params: {
    name: string;
  };
}

export default async function SupplementPage({ params }: SupplementPageProps) {
  // Decode the URL parameter
  const supplementName = decodeURIComponent(params.name);
  
  // Fetch supplement data from Supabase with research data
  const supplement = await getSupplementWithResearch(supplementName);
  
  // If no supplement found, show 404
  if (!supplement) {
    notFound();
  }

  // Format the last research check date
  const formattedDate = new Date(supplement.last_research_check).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  // Determine sentiment color, icon, and label based on sentiment score
  let sentimentColor = 'text-gray-500';
  let sentimentBgColor = 'bg-gray-100';
  let sentimentIcon = null;
  let sentimentLabel = 'Not analyzed'; // Keeping this for the safety profile section only
  
  if (supplement.sentiment_score !== null) {
    if (supplement.sentiment_score >= 7) {
      sentimentColor = 'text-green-600';
      sentimentBgColor = 'bg-green-50';
      sentimentIcon = <ThumbsUp className="w-4 h-4 mr-1" />;
      sentimentLabel = 'Positive';
    } else if (supplement.sentiment_score >= 4) {
      sentimentColor = 'text-amber-600';
      sentimentBgColor = 'bg-amber-50';
      sentimentLabel = 'Neutral';
    } else {
      sentimentColor = 'text-red-600';
      sentimentBgColor = 'bg-red-50';
      sentimentIcon = <ThumbsDown className="w-4 h-4 mr-1" />;
      sentimentLabel = 'Negative';
    }
  }

  // Check if we have research data
  const hasResearchData = supplement.supplement_research && 
                         supplement.supplement_research.length > 0 && 
                         supplement.supplement_research[0].research_count > 0;

  return (
    <main className="container max-w-6xl mx-auto px-4 py-8">
      <div className="mb-6">
        <Link href="/" className="inline-flex items-center text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to all supplements
        </Link>
      </div>

      {/* Improved Header with Better Space Utilization */}
      <div className="mb-6">
        <Card className="overflow-hidden border-none shadow-md">
          <CardContent className="p-6">
            <div className="flex flex-col md:flex-row items-center md:items-start gap-6">              
              {/* Center - Supplement info */}
              <div className="flex-grow flex flex-col items-center md:items-start">
                <div className="flex items-center gap-3 mb-2">
                  <h1 className="text-3xl font-bold">{supplement.name}</h1>
                  {supplement.is_popular && (
                    <div className="px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      Popular
                    </div>
                  )}
                </div>
                
                {/* Tags/metadata */}
                <div className="flex flex-wrap gap-2">
                  {supplement.sentiment_score !== null && (
                    <div className={`flex items-center px-3 py-1.5 rounded-full text-xs font-medium ${sentimentBgColor} ${sentimentColor}`}>
                      {sentimentIcon}
                      {sentimentLabel}
                      {` (${supplement.sentiment_score}/10)`}
                    </div>
                  )}
                  
                  <div className="flex items-center px-3 py-1.5 rounded-full text-xs font-medium bg-purple-50 text-purple-700">
                    <Calendar className="w-3 h-3 mr-1" />
                    Updated {formattedDate}
                  </div>
                  
                  {hasResearchData && (
                    <div className="flex items-center px-3 py-1.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700">
                      <FileText className="w-3 h-3 mr-1" />
                      {supplement.supplement_research[0].research_count.toLocaleString()} Studies
                    </div>
                  )}
                </div>
              </div>
              
              {/* Right side - Quick actions */}
              <div className="flex-shrink-0 flex flex-col gap-2 mt-4 md:mt-0">
                <Link 
                  href={`https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(`${supplement.name}[Title] AND (therapy[Title/Abstract] OR treatment[Title/Abstract] OR intervention[Title/Abstract])`)}`}
                  target="_blank"
                >
                  <Button variant="outline" size="sm" className="w-full">
                    <ExternalLink className="w-4 h-4 mr-2" />
                    Research
                  </Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Research Stats Card - Shows key metrics at a glance */}
      {hasResearchData && (
        <div className="mb-6">
          <Card className="border-none shadow-md">
            <CardContent className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 rounded-lg p-4 flex flex-col items-center justify-center">
                  <span className="text-blue-500 text-xs uppercase font-semibold mb-1">Total Studies</span>
                  <span className="text-3xl font-bold">{supplement.supplement_research[0].research_count.toLocaleString()}</span>
                </div>
                
                {supplement.supplement_research[0].rank_position && (
                  <div className="bg-green-50 rounded-lg p-4 flex flex-col items-center justify-center">
                    <span className="text-green-500 text-xs uppercase font-semibold mb-1">Research Rank</span>
                    <span className="text-3xl font-bold">#{supplement.supplement_research[0].rank_position}</span>
                    <span className="text-xs text-green-700">of {supplement.supplement_research[0].rank_total}</span>
                  </div>
                )}
                
                {supplement.supplement_research[0].rank_percentile && (
                  <div className="bg-purple-50 rounded-lg p-4 flex flex-col items-center justify-center">
                    <span className="text-purple-500 text-xs uppercase font-semibold mb-1">Percentile</span>
                    <div className="flex items-center">
                      <span className="text-3xl font-bold">Top {supplement.supplement_research[0].rank_percentile}%</span>
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
      
      {/* Bento Grid Layout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* About Card - Expanded with more content */}
        <Card className="border-none shadow-md md:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-xl font-semibold flex items-center">
              <BookOpen className="w-5 h-5 mr-2 text-primary/70" />
              About {supplement.name}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {supplement.description ? (
              <>
                <p className="text-muted-foreground mb-4">{supplement.description}</p>
                
                {/* Show full description if it was truncated in the header */}
                {/* Full description */}
                
                {/* Safety profile based on sentiment */}
                <h3 className="text-lg font-medium mb-2">Safety Profile</h3>
                <div className={`inline-flex items-center px-3 py-1.5 rounded-md text-sm font-medium mb-4 ${sentimentBgColor} ${sentimentColor}`}>
                  {sentimentIcon}
                  {sentimentLabel} {supplement.sentiment_score !== null && `(${supplement.sentiment_score}/10)`}
                </div>
              </>
            ) : (
              <p className="text-muted-foreground italic">No description available for this supplement yet.</p>
            )}
          </CardContent>
        </Card>
        
        {/* Related Supplements Card - New Component */}
        <Card className="border-none shadow-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-xl font-semibold flex items-center">
              <ExternalLink className="w-5 h-5 mr-2 text-primary/70" />
              Related Supplements
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-3">
              {/* This would be dynamically populated from your database */}
              {['Vitamin D', 'Magnesium', 'Omega-3'].map((related, index) => (
                <Link href={`/supplement/${encodeURIComponent(related)}`} key={index}>
                  <div className="flex items-center p-3 rounded-lg hover:bg-muted/50 transition-colors">
                    <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center mr-3">
                      <BookOpen className="w-4 h-4 text-primary" />
                    </div>
                    <span>{related}</span>
                  </div>
                </Link>
              ))}
              
              <div className="mt-2">
                <Link href="/" className="text-sm text-primary hover:text-primary/80 transition-colors">
                  View all supplements →
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Effectiveness & Research Card */}
      <div className="mb-6">
        <Card className="border-none shadow-md">
          <CardHeader className="pb-2">
            <CardTitle className="text-xl font-semibold flex items-center">
              <FileText className="w-5 h-5 mr-2 text-primary/70" />
              Effectiveness & Research
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h3 className="text-lg font-medium mb-3">Research Summary</h3>
                <p className="text-muted-foreground mb-4">
                  There {hasResearchData && supplement.supplement_research[0].research_count === 1 ? 'is' : 'are'} {hasResearchData ? supplement.supplement_research[0].research_count.toLocaleString() : 'no'} published {hasResearchData && supplement.supplement_research[0].research_count === 1 ? 'study' : 'studies'} about {supplement.name} in the PubMed database.
                </p>
                
                <div className="flex flex-col gap-2 mb-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Last research check</span>
                    <span className="font-medium">{formattedDate}</span>
                  </div>
                  
                  {hasResearchData && supplement.supplement_research[0].rank_position && (
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-muted-foreground">Research Rank</span>
                      <div className="flex items-center">
                        <span className="font-medium">
                          #{supplement.supplement_research[0].rank_position} of {supplement.supplement_research[0].rank_total}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="flex flex-col justify-center">
                {supplement.sentiment_score !== null && (
                  <>
                    <div className="relative h-8 bg-gray-200 rounded-full overflow-hidden mb-2">
                      <div 
                        className={`absolute top-0 left-0 h-full ${
                          supplement.sentiment_score >= 7 ? 'bg-green-500' :
                          supplement.sentiment_score >= 4 ? 'bg-amber-500' :
                          'bg-red-500'
                        }`}
                        style={{ width: `${supplement.sentiment_score * 10}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Limited Evidence</span>
                      <span>Strong Evidence</span>
                    </div>
                  </>
                )}
                
                <div className="mt-4">
                  <Link 
                    href={`https://pubmed.ncbi.nlm.nih.gov/?term=${encodeURIComponent(`${supplement.name}[Title] AND (therapy[Title/Abstract] OR treatment[Title/Abstract] OR intervention[Title/Abstract])`)}`}
                    target="_blank"
                    className="w-full"
                  >
                    <Button className="w-full flex items-center justify-center">
                      View Full Research
                      <ExternalLink className="w-4 h-4 ml-2" />
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Explore More Card - Improved */}
      <div>
        <Card className="border-none shadow-md bg-gradient-to-r from-blue-50 to-purple-50">
          <CardContent className="p-6">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div>
                <h3 className="text-lg font-medium mb-1">Explore More Supplements</h3>
                <p className="text-sm text-muted-foreground">
                  Discover other supplements and their research profiles
                </p>
              </div>
              <div className="flex gap-2">
                <Link href="/" legacyBehavior>
                  <Button variant="outline" size="sm">
                    All Supplements
                  </Button>
                </Link>
                <Link href="/popular" legacyBehavior>
                  <Button variant="default" size="sm">
                    Popular Supplements
                  </Button>
                </Link>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </main>
  );
}