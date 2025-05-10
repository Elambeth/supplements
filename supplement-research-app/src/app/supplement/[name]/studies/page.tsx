// src/app/supplement/[name]/studies/page.tsx
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { ArrowLeft, ExternalLink, Filter, Download, Calendar, BookOpen, FileSearch, ChevronDown } from 'lucide-react';
import { getSupplementWithResearch } from '@/lib/supabase';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

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
}

// Define the props for the page component
interface StudiesPageProps {
  params: {
    name: string;
  };
}

export default async function StudiesPage({ params }: StudiesPageProps) {
  // Decode the URL parameter
  const supplementName = decodeURIComponent(params.name);
  
  // Fetch supplement data from Supabase with research data
  const supplement = await getSupplementWithResearch(supplementName);
  
  // If no supplement found, show 404
  if (!supplement) {
    notFound();
  }

  // Important study types we want to highlight
  const importantStudyTypes = [
    "Randomized Controlled Trial", 
    "Multicenter Study", 
    "Systematic Review", 
    "Meta-Analysis"
  ];
  
  // Filter studies by publication type
  const importantStudies = supplement.supplement_studies?.filter((study: Study) => 
    study.publication_types?.some((type: string) => importantStudyTypes.includes(type))
  ) || [];

  // Helper function to format publication date
  const formatPublicationDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
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
    if (!text) return "No abstract available";
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  // Group studies by type
  const rctStudies = importantStudies.filter((study: Study) => 
    study.publication_types?.includes("Randomized Controlled Trial")
  );
  
  const metaAnalysisStudies = importantStudies.filter((study: Study) => 
    study.publication_types?.includes("Meta-Analysis")
  );
  
  const systematicReviewStudies = importantStudies.filter((study: Study) => 
    study.publication_types?.includes("Systematic Review") && 
    !study.publication_types?.includes("Meta-Analysis")
  );
  
  const multicenterStudies = importantStudies.filter((study: Study) => 
    study.publication_types?.includes("Multicenter Study") && 
    !study.publication_types?.includes("Randomized Controlled Trial")
  );

  // Count total studies by type (for tabs)
  const typeCountMap = {
    "all": importantStudies.length,
    "rct": rctStudies.length,
    "meta": metaAnalysisStudies.length,
    "systematic": systematicReviewStudies.length,
    "multicenter": multicenterStudies.length
  };

  return (
    <main className="container max-w-6xl mx-auto px-4 py-8">
      <div className="mb-6">
        <Link href={`/supplement/${encodeURIComponent(supplementName)}`} className="inline-flex items-center text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to {supplementName}
        </Link>
      </div>

      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">
          Key Research Studies: {supplementName}
        </h1>
        <p className="text-muted-foreground max-w-3xl">
          High-quality research studies including randomized controlled trials, meta-analyses, 
          systematic reviews, and multicenter studies. These represent the most rigorous scientific 
          evidence available for {supplementName}.
        </p>
      </div>

      {/* Studies Filter Tabs */}
      <div className="mb-6">
        <Tabs defaultValue="all" className="w-full">
          <div className="flex items-center justify-between mb-4">
            <TabsList className="bg-muted/60">
              <TabsTrigger value="all" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
                All Studies ({typeCountMap.all})
              </TabsTrigger>
              {rctStudies.length > 0 && (
                <TabsTrigger value="rct" className="data-[state=active]:bg-emerald-600 data-[state=active]:text-white">
                  RCTs ({typeCountMap.rct})
                </TabsTrigger>
              )}
              {metaAnalysisStudies.length > 0 && (
                <TabsTrigger value="meta" className="data-[state=active]:bg-indigo-600 data-[state=active]:text-white">
                  Meta-Analyses ({typeCountMap.meta})
                </TabsTrigger>
              )}
              {systematicReviewStudies.length > 0 && (
                <TabsTrigger value="systematic" className="data-[state=active]:bg-blue-600 data-[state=active]:text-white">
                  Systematic Reviews ({typeCountMap.systematic})
                </TabsTrigger>
              )}
              {multicenterStudies.length > 0 && (
                <TabsTrigger value="multicenter" className="data-[state=active]:bg-purple-600 data-[state=active]:text-white">
                  Multicenter ({typeCountMap.multicenter})
                </TabsTrigger>
              )}
            </TabsList>
            
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" className="hidden md:flex">
                <Filter className="w-4 h-4 mr-2" />
                Filter
              </Button>
              <Button variant="outline" size="sm" className="hidden md:flex">
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            </div>
          </div>

          {/* All Studies Tab */}
          <TabsContent value="all" className="mt-0">
            <div className="space-y-4">
              {importantStudies.length > 0 ? importantStudies.map((study: Study) => (
                <Card key={study.id} className="overflow-hidden border-none shadow-sm hover:shadow-md transition-shadow">
                  <CardContent className="p-5">
                    <div className="flex flex-wrap gap-2 mb-3">
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
                    
                    <h3 className="text-lg font-medium mb-2">{study.title}</h3>
                    
                    <div className="mb-3">
                      <details className="group">
                        <summary className="list-none flex justify-between items-center cursor-pointer">
                          <span className="text-sm text-muted-foreground">
                            {truncateText(study.abstract || "No abstract available", 150)}
                          </span>
                          <ChevronDown className="h-5 w-5 text-muted-foreground group-open:rotate-180 transition-transform" />
                        </summary>
                        <div className="mt-3 text-sm text-muted-foreground">
                          {study.abstract || "No abstract available"}
                        </div>
                      </details>
                    </div>
                    
                    <div className="flex items-center justify-between pt-2 border-t border-muted">
                      <div className="text-xs text-muted-foreground">
                        <span className="font-medium">{study.journal}</span>
                        {study.authors && study.authors.length > 0 && (
                          <span> • {study.authors[0]}{study.authors.length > 1 ? ` et al.` : ''}</span>
                        )}
                      </div>
                      
                      <Link 
                        href={`https://pubmed.ncbi.nlm.nih.gov/${study.pmid}/`}
                        target="_blank"
                        className="inline-flex items-center text-sm text-primary hover:text-primary/80 transition-colors"
                      >
                        View on PubMed
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              )) : (
                <div className="text-center py-12">
                  <FileSearch className="w-12 h-12 text-muted-foreground/50 mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No studies found</h3>
                  <p className="text-muted-foreground">There are no high-quality studies available for this supplement.</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* RCTs Tab */}
          <TabsContent value="rct" className="mt-0">
            <div className="space-y-4">
              {rctStudies.length > 0 ? rctStudies.map((study: Study) => (
                <Card key={study.id} className="overflow-hidden border-none shadow-sm hover:shadow-md transition-shadow">
                  <CardContent className="p-5">
                    <div className="flex flex-wrap gap-2 mb-3">
                      <span className={`px-2 py-1 rounded-md text-xs font-medium ${getPublicationTypeBadgeColor("Randomized Controlled Trial")}`}>
                        Randomized Controlled Trial
                      </span>
                      <span className="px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
                        {formatPublicationDate(study.publication_date)}
                      </span>
                    </div>
                    
                    <h3 className="text-lg font-medium mb-2">{study.title}</h3>
                    
                    <div className="mb-3">
                      <details className="group">
                        <summary className="list-none flex justify-between items-center cursor-pointer">
                          <span className="text-sm text-muted-foreground">
                            {truncateText(study.abstract || "No abstract available", 150)}
                          </span>
                          <ChevronDown className="h-5 w-5 text-muted-foreground group-open:rotate-180 transition-transform" />
                        </summary>
                        <div className="mt-3 text-sm text-muted-foreground">
                          {study.abstract || "No abstract available"}
                        </div>
                      </details>
                    </div>
                    
                    <div className="flex items-center justify-between pt-2 border-t border-muted">
                      <div className="text-xs text-muted-foreground">
                        <span className="font-medium">{study.journal}</span>
                        {study.authors && study.authors.length > 0 && (
                          <span> • {study.authors[0]}{study.authors.length > 1 ? ` et al.` : ''}</span>
                        )}
                      </div>
                      
                      <Link 
                        href={`https://pubmed.ncbi.nlm.nih.gov/${study.pmid}/`}
                        target="_blank"
                        className="inline-flex items-center text-sm text-primary hover:text-primary/80 transition-colors"
                      >
                        View on PubMed
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              )) : (
                <div className="text-center py-12">
                  <FileSearch className="w-12 h-12 text-muted-foreground/50 mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No RCTs found</h3>
                  <p className="text-muted-foreground">There are no randomized controlled trials available for this supplement.</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Meta-Analyses Tab */}
          <TabsContent value="meta" className="mt-0">
            <div className="space-y-4">
              {metaAnalysisStudies.length > 0 ? metaAnalysisStudies.map((study: Study) => (
                <Card key={study.id} className="overflow-hidden border-none shadow-sm hover:shadow-md transition-shadow">
                  <CardContent className="p-5">
                    <div className="flex flex-wrap gap-2 mb-3">
                      <span className={`px-2 py-1 rounded-md text-xs font-medium ${getPublicationTypeBadgeColor("Meta-Analysis")}`}>
                        Meta-Analysis
                      </span>
                      <span className="px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
                        {formatPublicationDate(study.publication_date)}
                      </span>
                    </div>
                    
                    <h3 className="text-lg font-medium mb-2">{study.title}</h3>
                    
                    <div className="mb-3">
                      <details className="group">
                        <summary className="list-none flex justify-between items-center cursor-pointer">
                          <span className="text-sm text-muted-foreground">
                            {truncateText(study.abstract || "No abstract available", 150)}
                          </span>
                          <ChevronDown className="h-5 w-5 text-muted-foreground group-open:rotate-180 transition-transform" />
                        </summary>
                        <div className="mt-3 text-sm text-muted-foreground">
                          {study.abstract || "No abstract available"}
                        </div>
                      </details>
                    </div>
                    
                    <div className="flex items-center justify-between pt-2 border-t border-muted">
                      <div className="text-xs text-muted-foreground">
                        <span className="font-medium">{study.journal}</span>
                        {study.authors && study.authors.length > 0 && (
                          <span> • {study.authors[0]}{study.authors.length > 1 ? ` et al.` : ''}</span>
                        )}
                      </div>
                      
                      <Link 
                        href={`https://pubmed.ncbi.nlm.nih.gov/${study.pmid}/`}
                        target="_blank"
                        className="inline-flex items-center text-sm text-primary hover:text-primary/80 transition-colors"
                      >
                        View on PubMed
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              )) : (
                <div className="text-center py-12">
                  <FileSearch className="w-12 h-12 text-muted-foreground/50 mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No Meta-Analyses found</h3>
                  <p className="text-muted-foreground">There are no meta-analyses available for this supplement.</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Systematic Reviews Tab */}
          <TabsContent value="systematic" className="mt-0">
            <div className="space-y-4">
              {systematicReviewStudies.length > 0 ? systematicReviewStudies.map((study: Study) => (
                <Card key={study.id} className="overflow-hidden border-none shadow-sm hover:shadow-md transition-shadow">
                  <CardContent className="p-5">
                    <div className="flex flex-wrap gap-2 mb-3">
                      <span className={`px-2 py-1 rounded-md text-xs font-medium ${getPublicationTypeBadgeColor("Systematic Review")}`}>
                        Systematic Review
                      </span>
                      <span className="px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
                        {formatPublicationDate(study.publication_date)}
                      </span>
                    </div>
                    
                    <h3 className="text-lg font-medium mb-2">{study.title}</h3>
                    
                    <div className="mb-3">
                      <details className="group">
                        <summary className="list-none flex justify-between items-center cursor-pointer">
                          <span className="text-sm text-muted-foreground">
                            {truncateText(study.abstract || "No abstract available", 150)}
                          </span>
                          <ChevronDown className="h-5 w-5 text-muted-foreground group-open:rotate-180 transition-transform" />
                        </summary>
                        <div className="mt-3 text-sm text-muted-foreground">
                          {study.abstract || "No abstract available"}
                        </div>
                      </details>
                    </div>
                    
                    <div className="flex items-center justify-between pt-2 border-t border-muted">
                      <div className="text-xs text-muted-foreground">
                        <span className="font-medium">{study.journal}</span>
                        {study.authors && study.authors.length > 0 && (
                          <span> • {study.authors[0]}{study.authors.length > 1 ? ` et al.` : ''}</span>
                        )}
                      </div>
                      
                      <Link 
                        href={`https://pubmed.ncbi.nlm.nih.gov/${study.pmid}/`}
                        target="_blank"
                        className="inline-flex items-center text-sm text-primary hover:text-primary/80 transition-colors"
                      >
                        View on PubMed
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              )) : (
                <div className="text-center py-12">
                  <FileSearch className="w-12 h-12 text-muted-foreground/50 mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No Systematic Reviews found</h3>
                  <p className="text-muted-foreground">There are no systematic reviews available for this supplement.</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Multicenter Studies Tab */}
          <TabsContent value="multicenter" className="mt-0">
            <div className="space-y-4">
              {multicenterStudies.length > 0 ? multicenterStudies.map((study: Study) => (
                <Card key={study.id} className="overflow-hidden border-none shadow-sm hover:shadow-md transition-shadow">
                  <CardContent className="p-5">
                    <div className="flex flex-wrap gap-2 mb-3">
                      <span className={`px-2 py-1 rounded-md text-xs font-medium ${getPublicationTypeBadgeColor("Multicenter Study")}`}>
                        Multicenter Study
                      </span>
                      <span className="px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
                        {formatPublicationDate(study.publication_date)}
                      </span>
                    </div>
                    
                    <h3 className="text-lg font-medium mb-2">{study.title}</h3>
                    
                    <div className="mb-3">
                      <details className="group">
                        <summary className="list-none flex justify-between items-center cursor-pointer">
                          <span className="text-sm text-muted-foreground">
                            {truncateText(study.abstract || "No abstract available", 150)}
                          </span>
                          <ChevronDown className="h-5 w-5 text-muted-foreground group-open:rotate-180 transition-transform" />
                        </summary>
                        <div className="mt-3 text-sm text-muted-foreground">
                          {study.abstract || "No abstract available"}
                        </div>
                      </details>
                    </div>
                    
                    <div className="flex items-center justify-between pt-2 border-t border-muted">
                      <div className="text-xs text-muted-foreground">
                        <span className="font-medium">{study.journal}</span>
                        {study.authors && study.authors.length > 0 && (
                          <span> • {study.authors[0]}{study.authors.length > 1 ? ` et al.` : ''}</span>
                        )}
                      </div>
                      
                      <Link 
                        href={`https://pubmed.ncbi.nlm.nih.gov/${study.pmid}/`}
                        target="_blank"
                        className="inline-flex items-center text-sm text-primary hover:text-primary/80 transition-colors"
                      >
                        View on PubMed
                        <ExternalLink className="w-3 h-3 ml-1" />
                      </Link>
                    </div>
                  </CardContent>
                </Card>
              )) : (
                <div className="text-center py-12">
                  <FileSearch className="w-12 h-12 text-muted-foreground/50 mx-auto mb-4" />
                  <h3 className="text-lg font-medium mb-2">No Multicenter Studies found</h3>
                  <p className="text-muted-foreground">There are no multicenter studies available for this supplement.</p>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Back to Supplement Button */}
      <div className="mt-8 text-center">
        <Link href={`/supplement/${encodeURIComponent(supplementName)}`}>
          <Button variant="outline" className="mx-auto">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to {supplementName}
          </Button>
        </Link>
      </div>
    </main>
  );
}