// src/app/supplement/[name]/page.tsx
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, ExternalLink, ThumbsUp, ThumbsDown, Calendar, BookOpen, FileText, Info, FileSearch, Book, ChevronRight } from 'lucide-react';
import { countAggregateRecords, getSupplementWithResearch } from '@/lib/supabase';
import { Badge } from '@/components/ui/badge';
import ResearchTimeline from '@/components/ui/ResearchTimeline';
import { TimelineCard } from '@/components/ui/timeline-card';
import GaugeChart from '@/components/ui/gauge-chart';

// Define types for supplement data
interface Study {
  id: number;
  pmid: string;
  title: string;
  abstract: string;
  journal: string;
  publication_date: string;
  publication_types: string[];
  authors: string[];
}

interface SupplementResearch {
  research_count: number;
  retrieved_count: number;
  search_date: string;
  last_updated: string;
  query: string;
  rank_position: number;
  rank_total: number;
  rank_percentile: number;
}

interface SupplementResearchAggregates {
  avg_safety_score: number | null;
  avg_efficacy_score: number | null;
  avg_quality_score: number | null;
  safety_score_count: number;
  efficacy_score_count: number;
  quality_score_count: number;
  findings_consistency_score: number | null;
  findings_summary: string | null;
  research_summary: string | null;
  populations_studied: string[] | null;
  common_dosages: string[] | null;
  typical_duration: string | null;
  common_interactions: string[] | null;
}

interface Supplement {
  id: number;
  name: string;
  description: string | null;
  is_popular: boolean;
  last_research_check: string;
  sentiment_score: number | null;
  created_at: string;
  supplement_research?: SupplementResearch[];
  supplement_studies?: Study[];
  supplement_research_aggregates?: SupplementResearchAggregates[];
}

// This enables dynamic segments to be statically generated at build time
export const dynamicParams = true;

// Define the props for the page component
interface SupplementPageProps {
  params: {
    name: string;
  };
}

// Add near the top of your component
const recordCount = await countAggregateRecords();
console.log(`Total supplement_research_aggregates records: ${recordCount}`);

export default async function SupplementPage({ params }: SupplementPageProps) {
  // Decode the URL parameter
  const { name } = await params;
  const supplementName = decodeURIComponent(name);
  
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

  // Filter studies by publication type
  const importantStudyTypes = [
    "Randomized Controlled Trial", 
    "Multicenter Study", 
    "Systematic Review", 
    "Meta-Analysis"
  ];
  
  const importantStudies = supplement.supplement_studies?.filter((study: Study) => 
    study.publication_types?.some((type: string) => importantStudyTypes.includes(type))
  ) || [];

  // Helper function to format publication date
  const formatPublicationDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
    });
  };

  // Helper function to get publication type badge color
  const getPublicationTypeBadgeColor = (type: string) => {
    switch (type) {
      case "Randomized Controlled Trial":
        return "bg-emerald-100 text-emerald-800";
      case "Multicenter Study":
        return "bg-purple-100 text-purple-800";
      case "Systematic Review":
        return "bg-blue-100 text-blue-800";
      case "Meta-Analysis":
        return "bg-indigo-100 text-indigo-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };
  
  // Helper function to truncate text
  const truncateText = (text: string, maxLength: number) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

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
              {['Vitamin D', 'Magnesium', 'Omega-3'].map((related: string, index: number) => (
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
      
     {/* Effectiveness & Research Card with Gauge Charts */}
      <div className="mb-6">
        <Card className="border-none shadow-md">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xl font-semibold flex items-center">
                <FileText className="w-5 h-5 mr-2 text-primary/70" />
                Effectiveness & Research
              </CardTitle>
              
              {/* Info button with Tooltip */}
              <div className="relative flex items-center group">
                <Link 
                  href="/research-methodology" 
                  className="w-6 h-6 rounded-full bg-muted hover:bg-muted/80 flex items-center justify-center transition-colors"
                  aria-label="Research methodology information"
                >
                  <Info className="w-5.5 h-5.5 text-muted-foreground" />
                </Link>
                <div className="absolute z-10 right-0 top-8 w-64 p-2 bg-popover rounded-md shadow-md text-xs opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200">
                  <p className="text-popover-foreground">Learn about our research methodology and how we assess supplement effectiveness.</p>
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            <div>
              {/* Research Quality Metrics Section */}
              <div>
                <h3 className="text-lg font-medium mb-6">Research Quality Metrics</h3>
                
                {/* Check if we have aggregate data */}
                {supplement.supplement_research_aggregates && supplement.supplement_research_aggregates.length > 0 ? (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
                      {/* Safety Score with Gauge Chart */}
                      <div className="flex flex-col items-center">
                        <div className="mb-4">
                          <GaugeChart
                            size={120}
                            gap={50}
                            progress={supplement.supplement_research_aggregates[0].avg_safety_score ? supplement.supplement_research_aggregates[0].avg_safety_score * 10 : 0}
                            progressClassName="text-green-500"
                            trackClassName="text-green-100"
                            circleWidth={8}
                            progressWidth={8}
                            showValue={true}
                            className="mb-2"
                          />
                        </div>
                        <div className="text-center">
                          <h4 className="text-sm font-semibold text-green-700 mb-1">Safety Score</h4>
                          <p className="text-xs text-muted-foreground">
                            Based on {supplement.supplement_research_aggregates[0].safety_score_count} {supplement.supplement_research_aggregates[0].safety_score_count === 1 ? 'study' : 'studies'}
                          </p>
                        </div>
                      </div>
                      
                      {/* Efficacy Score with Gauge Chart */}
                      <div className="flex flex-col items-center">
                        <div className="mb-4">
                          <GaugeChart
                            size={120}
                            gap={50}
                            progress={supplement.supplement_research_aggregates[0].avg_efficacy_score ? supplement.supplement_research_aggregates[0].avg_efficacy_score * 10 : 0}
                            progressClassName="text-blue-500"
                            trackClassName="text-blue-100"
                            circleWidth={8}
                            progressWidth={8}
                            showValue={true}
                            className="mb-2"
                          />
                        </div>
                        <div className="text-center">
                          <h4 className="text-sm font-semibold text-blue-700 mb-1">Efficacy Score</h4>
                          <p className="text-xs text-muted-foreground">
                            Based on {supplement.supplement_research_aggregates[0].efficacy_score_count} {supplement.supplement_research_aggregates[0].efficacy_score_count === 1 ? 'study' : 'studies'}
                          </p>
                        </div>
                      </div>
                      
                      {/* Quality Score with Gauge Chart */}
                      <div className="flex flex-col items-center">
                        <div className="mb-4">
                          <GaugeChart
                            size={120}
                            gap={50}
                            progress={supplement.supplement_research_aggregates[0].avg_quality_score ? supplement.supplement_research_aggregates[0].avg_quality_score * 10 : 0}
                            progressClassName="text-purple-500"
                            trackClassName="text-purple-100"
                            circleWidth={8}
                            progressWidth={8}
                            showValue={true}
                            className="mb-2"
                          />
                        </div>
                        <div className="text-center">
                          <h4 className="text-sm font-semibold text-purple-700 mb-1">Quality Score</h4>
                          <p className="text-xs text-muted-foreground">
                            Based on {supplement.supplement_research_aggregates[0].quality_score_count} {supplement.supplement_research_aggregates[0].quality_score_count === 1 ? 'study' : 'studies'}
                          </p>
                        </div>
                      </div>
                      
                      {/* Findings Consistency with Gauge Chart */}
                      {supplement.supplement_research_aggregates[0].findings_consistency_score && (
                        <div className="flex flex-col items-center">
                          <div className="mb-4">
                            <GaugeChart
                              size={120}
                              gap={50}
                              progress={supplement.supplement_research_aggregates[0].findings_consistency_score * 10}
                              progressClassName="text-amber-500"
                              trackClassName="text-amber-100"
                              circleWidth={8}
                              progressWidth={8}
                              showValue={true}
                              className="mb-2"
                            />
                          </div>
                          <div className="text-center">
                            <h4 className="text-sm font-semibold text-amber-700 mb-1">Consistency</h4>
                            <p className="text-xs text-muted-foreground">
                              Findings alignment
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {/* Findings Summary if available */}
                    {supplement.supplement_research_aggregates[0].findings_summary && (
                      <div className="mb-6 p-4 border border-amber-100 rounded-lg bg-amber-50">
                        <h4 className="text-sm font-medium text-amber-800 mb-2">Key Findings</h4>
                        <p className="text-sm text-amber-700">
                          {supplement.supplement_research_aggregates[0].findings_summary}
                        </p>
                      </div>
                    )}
                    
                    {/* Research Summary if available */}
                    {supplement.supplement_research_aggregates[0].research_summary && (
                      <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                        <h4 className="text-sm font-medium mb-2">Research Summary</h4>
                        <p className="text-sm">
                          {supplement.supplement_research_aggregates[0].research_summary}
                        </p>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="p-4 bg-amber-50 rounded-lg">
                    <div className="flex items-center">
                      <Info className="w-4 h-4 text-amber-500 mr-2" />
                      <p className="text-sm text-amber-800">
                        Detailed research metrics are being processed for {supplement.name}. Check back later for safety, efficacy, and quality scores based on scientific studies.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Research Timeline Card - Dynamic Height Container */}
      {supplement.supplement_studies && supplement.supplement_studies.length > 0 && (
        <div className="mb-6">
          <TimelineCard 
            studies={supplement.supplement_studies}
            supplementName={supplement.name}
          />
        </div>
      )}

      {/* Key Studies Card - New section for important studies - MOVED TO BOTTOM */}
      {importantStudies.length > 0 && (
        <div className="mb-6">
          <Card className="border-none shadow-md">
            <CardHeader className="pb-2">
              <CardTitle className="text-xl font-semibold flex items-center">
                <FileSearch className="w-5 h-5 mr-2 text-primary/70" />
                Key Research Studies
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-4">
                High-quality research studies for {supplement.name} including randomized controlled trials, systematic reviews, and meta-analyses.
              </p>
              
              <div className="space-y-4">
                {importantStudies.slice(0, 5).map((study: Study) => (
                  <div key={study.id} className="p-4 rounded-lg border border-muted hover:border-muted-foreground/20 transition-colors">
                    <div className="flex flex-wrap gap-2 mb-2">
                      {study.publication_types
                        .filter((type: string) => importantStudyTypes.includes(type))
                        .map((type: string, index: number) => (
                          <span 
                            key={index} 
                            className={`px-2 py-1 rounded-md text-xs font-medium ${getPublicationTypeBadgeColor(type)}`}
                          >
                            {type}
                          </span>
                        ))
                      }
                      <span className="px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
                        {formatPublicationDate(study.publication_date)}
                      </span>
                    </div>
                    
                    <h3 className="text-base font-medium mb-2">{study.title}</h3>
                    
                    <p className="text-sm text-muted-foreground mb-3">
                      {truncateText(study.abstract || "No abstract available", 200)}
                    </p>
                    
                    <div className="flex items-center justify-between">
                      <div className="text-xs text-muted-foreground">
                        <span className="font-medium">{study.journal}</span>
                        {study.authors && study.authors.length > 0 && (
                          <span> • {study.authors[0]}{study.authors.length > 1 ? ` et al.` : ''}</span>
                        )}
                      </div>
                      
                      <Link 
                        href={`https://pubmed.ncbi.nlm.nih.gov/${study.pmid}/`}
                        target="_blank"
                        className="text-xs text-primary hover:text-primary/80 flex items-center transition-colors"
                      >
                        View on PubMed
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
              
              {importantStudies.length > 5 && (
                <div className="mt-4 text-center">
                  <Link 
                    href={`/supplement/${encodeURIComponent(supplement.name)}/studies`}
                    className="inline-flex items-center text-primary hover:text-primary/80 transition-colors"
                  >
                    View all {importantStudies.length} key studies
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
      
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