// src/app/supplement/[name]/page.tsx
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft, ExternalLink, ThumbsUp, ThumbsDown, Calendar, BookOpen, FileText, Info, FileSearch, Book, ChevronRight } from 'lucide-react';
import { countAggregateRecords, getSupplementWithResearch } from '@/lib/supabase';
import { Badge } from '@/components/ui/badge';
import { lazy, Suspense } from 'react';

// Lazy load below-fold components
const GaugeChart = lazy(() => import('@/components/ui/gauge-chart'));
const TimelineCard = lazy(() => import('@/components/ui/timeline-card').then(module => ({ default: module.TimelineCard })));

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
  let sentimentLabel = 'Not analyzed';
  
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
    <main className="container max-w-7xl mx-auto px-6 py-8">
      {/* Header Navigation */}
      <div className="mb-8">
        <Link href="/" className="inline-flex items-center text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to all supplements
        </Link>
      </div>

      {/* Page Header */}
      <div className="mb-8 text-center">
        <div className="flex items-center justify-center gap-4 mb-4">
          <h1 className="text-4xl font-bold">{supplement.name}</h1>
          {supplement.is_popular && (
            <Badge className="bg-blue-100 text-blue-800 border-blue-200">
              Popular
            </Badge>
          )}
        </div>
        
        {/* Small centered research stats */}
        {hasResearchData && (
          <div className="flex justify-center gap-6 mb-6">
            <div className="text-center">
              <div className="text-lg font-bold text-blue-600">
                {supplement.supplement_research[0].research_count.toLocaleString()}
              </div>
              <div className="text-xs text-gray-600">Studies</div>
            </div>
            
            {supplement.supplement_research[0].rank_position && (
              <div className="text-center">
                <div className="text-lg font-bold text-green-600">
                  #{supplement.supplement_research[0].rank_position}
                </div>
                <div className="text-xs text-gray-600">Rank</div>
              </div>
            )}
            
            {supplement.supplement_research[0].rank_percentile && (
              <div className="text-center">
                <div className="text-lg font-bold text-purple-600">
                  Top {supplement.supplement_research[0].rank_percentile}%
                </div>
                <div className="text-xs text-gray-600">Percentile</div>
              </div>
            )}
          </div>
        )}

        <div className="flex justify-center flex-wrap gap-3 mb-6">
          {supplement.sentiment_score !== null && (
            <div className={`flex items-center px-4 py-2 rounded-full text-sm font-medium ${sentimentBgColor} ${sentimentColor}`}>
              {sentimentIcon}
              {sentimentLabel} ({supplement.sentiment_score}/10)
            </div>
          )}
          
          <div className="flex items-center px-4 py-2 rounded-full text-sm font-medium bg-gray-100 text-gray-700">
            <Calendar className="w-4 h-4 mr-2" />
            Updated {formattedDate}
          </div>
        </div>
      </div>

      {/* Main Content Area - Graph and Info Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
        {/* Left Side - Graph Placeholder */}
        <div className="bg-blue-500 rounded-xl h-120 flex items-center justify-center">
          <div className="text-white text-center">
            <div className="text-6xl mb-4">📊</div>
            <h3 className="text-xl font-semibold mb-2">Research Visualization</h3>
            <p className="text-blue-100">Graph will be implemented here</p>
          </div>
        </div>

        {/* Right Side - Description and Research Quality Metrics */}
        <div className="space-y-6">
          {/* Description */}
          {supplement.description && (
            <div>
              <h3 className="text-xl font-semibold mb-3">About {supplement.name}</h3>
              <p className="text-muted-foreground leading-relaxed">
                {supplement.description}
              </p>
            </div>
          )}

          {/* Research Quality Metrics */}
          {supplement.supplement_research_aggregates && supplement.supplement_research_aggregates.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-4 flex items-center">
                <FileText className="w-4 h-4 mr-2" />
                Research Quality Metrics
              </h3>
              <div className="grid grid-cols-2 gap-6">
                {/* Safety Score */}
                <div className="flex flex-col items-center">
                  <div className="mb-3">
                    <Suspense fallback={<div className="w-16 h-16 bg-gray-100 animate-pulse rounded-full" />}>
                      <GaugeChart
                        size={64}
                        gap={50}
                        progress={supplement.supplement_research_aggregates[0].avg_safety_score ? supplement.supplement_research_aggregates[0].avg_safety_score * 100 : 0}
                        progressClassName="text-green-500"
                        trackClassName="text-green-100"
                        circleWidth={4}
                        progressWidth={4}
                        showValue={true}
                      />
                    </Suspense>
                  </div>
                  <h4 className="font-medium text-green-700 mb-1 text-sm">Safety</h4>
                  <p className="text-xs text-muted-foreground text-center">
                    {supplement.supplement_research_aggregates[0].safety_score_count} studies
                  </p>
                </div>

                {/* Efficacy Score */}
                <div className="flex flex-col items-center">
                  <div className="mb-3">
                    <Suspense fallback={<div className="w-16 h-16 bg-gray-100 animate-pulse rounded-full" />}>
                      <GaugeChart
                        size={64}
                        gap={50}
                        progress={supplement.supplement_research_aggregates[0].avg_efficacy_score ? supplement.supplement_research_aggregates[0].avg_efficacy_score * 100 : 0}
                        progressClassName="text-blue-500"
                        trackClassName="text-blue-100"
                        circleWidth={4}
                        progressWidth={4}
                        showValue={true}
                      />
                    </Suspense>
                  </div>
                  <h4 className="font-medium text-blue-700 mb-1 text-sm">Efficacy</h4>
                  <p className="text-xs text-muted-foreground text-center">
                    {supplement.supplement_research_aggregates[0].efficacy_score_count} studies
                  </p>
                </div>

                {/* Quality Score */}
                <div className="flex flex-col items-center">
                  <div className="mb-3">
                    <Suspense fallback={<div className="w-16 h-16 bg-gray-100 animate-pulse rounded-full" />}>
                      <GaugeChart
                        size={64}
                        gap={50}
                        progress={supplement.supplement_research_aggregates[0].avg_quality_score ? supplement.supplement_research_aggregates[0].avg_quality_score * 100 : 0}
                        progressClassName="text-purple-500"
                        trackClassName="text-purple-100"
                        circleWidth={4}
                        progressWidth={4}
                        showValue={true}
                      />
                    </Suspense>
                  </div>
                  <h4 className="font-medium text-purple-700 mb-1 text-sm">Quality</h4>
                  <p className="text-xs text-muted-foreground text-center">
                    {supplement.supplement_research_aggregates[0].quality_score_count} studies
                  </p>
                </div>

                {/* Consistency Score */}
                {supplement.supplement_research_aggregates[0].findings_consistency_score && (
                  <div className="flex flex-col items-center">
                    <div className="mb-3">
                      <Suspense fallback={<div className="w-16 h-16 bg-gray-100 animate-pulse rounded-full" />}>
                        <GaugeChart
                          size={64}
                          gap={50}
                          progress={supplement.supplement_research_aggregates[0].findings_consistency_score * 100}
                          progressClassName="text-amber-500"
                          trackClassName="text-amber-100"
                          circleWidth={4}
                          progressWidth={4}
                          showValue={true}
                        />
                      </Suspense>
                    </div>
                    <h4 className="font-medium text-amber-700 mb-1 text-sm">Consistency</h4>
                    <p className="text-xs text-muted-foreground text-center">Findings alignment</p>
                  </div>
                )}
              </div>

              {/* Findings and Research Summary */}
              {(supplement.supplement_research_aggregates[0].findings_summary || supplement.supplement_research_aggregates[0].research_summary) && (
                <div className="mt-6 space-y-3">
                  {supplement.supplement_research_aggregates[0].findings_summary && (
                    <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                      <h4 className="font-medium text-amber-800 mb-2 text-sm">Key Findings</h4>
                      <p className="text-xs text-amber-700">
                        {supplement.supplement_research_aggregates[0].findings_summary}
                      </p>
                    </div>
                  )}
                  
                  {supplement.supplement_research_aggregates[0].research_summary && (
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                      <h4 className="font-medium mb-2 text-sm">Research Summary</h4>
                      <p className="text-xs text-gray-700">
                        {supplement.supplement_research_aggregates[0].research_summary}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Research Timeline Card */}
      {supplement.supplement_studies && supplement.supplement_studies.length > 0 && (
        <div className="mb-8">
          <Suspense fallback={<div className="h-96 bg-gray-100 animate-pulse rounded-lg" />}>
            <TimelineCard 
              studies={supplement.supplement_studies}
              supplementName={supplement.name}
            />
          </Suspense>
        </div>
      )}

      {/* Studies Table/Data Grid */}
      {importantStudies.length > 0 && (
        <Card className="bg-gray-900 text-white">
          <CardHeader>
            <CardTitle className="flex items-center text-white">
              <FileSearch className="w-5 h-5 mr-2" />
              Key Research Studies
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <div className="grid gap-4">
                {importantStudies.slice(0, 5).map((study: Study, index: number) => (
                  <div 
                    key={study.id} 
                    className={`grid grid-cols-12 gap-4 py-3 px-4 rounded-lg ${
                      index % 2 === 0 ? 'bg-blue-900/30' : 'bg-gray-800/50'
                    }`}
                  >
                    {/* Study Type */}
                    <div className="col-span-2">
                      {study.publication_types
                        .filter((type: string) => importantStudyTypes.includes(type))
                        .slice(0, 1)
                        .map((type: string) => (
                          <span key={type} className="text-xs px-2 py-1 bg-blue-600 rounded">
                            {type.replace('Randomized Controlled Trial', 'RCT')}
                          </span>
                        ))
                      }
                    </div>
                    
                    {/* Title */}
                    <div className="col-span-5">
                      <h4 className="text-sm font-medium text-white leading-tight">
                        {truncateText(study.title, 80)}
                      </h4>
                    </div>
                    
                    {/* Journal */}
                    <div className="col-span-2">
                      <p className="text-xs text-gray-300">{study.journal}</p>
                    </div>
                    
                    {/* Date */}
                    <div className="col-span-1">
                      <p className="text-xs text-gray-400">{formatPublicationDate(study.publication_date)}</p>
                    </div>
                    
                    {/* Link */}
                    <div className="col-span-2 text-right">
                      <Link 
                        href={`https://pubmed.ncbi.nlm.nih.gov/${study.pmid}/`}
                        target="_blank"
                        className="text-xs text-blue-400 hover:text-blue-300 flex items-center justify-end"
                      >
                        View <ExternalLink className="w-3 h-3 ml-1" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
              
              {importantStudies.length > 5 && (
                <div className="mt-6 text-center">
                  <Button variant="outline" className="bg-transparent border-gray-600 text-white hover:bg-gray-800">
                    View all {importantStudies.length} studies
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </main>
  );
}