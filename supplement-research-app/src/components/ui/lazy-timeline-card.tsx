'use client';

import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Loader2, Calendar, FileText } from 'lucide-react';

interface Study {
  id: number;
  title: string;
  publication_date: string;
  publication_types: string[];
  journal: string;
}

interface TimelineData {
  yearCounts: Record<number, number>;
  totalStudies: number;
  dateRange: { start: number; end: number } | null;
  initialStudies: Study[];
  hasMore: boolean;
}

interface LazyTimelineCardProps {
  supplementName: string;
  initialData: TimelineData;
}

export default function LazyTimelineCard({ supplementName, initialData }: LazyTimelineCardProps) {
  const [studies, setStudies] = useState<Study[]>(initialData.initialStudies);
  const [currentPage, setCurrentPage] = useState(0);
  const [hasMore, setHasMore] = useState(initialData.hasMore);
  const [loading, setLoading] = useState(false);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);

  const loadMoreStudies = useCallback(async () => {
    if (loading || !hasMore) return;
    
    setLoading(true);
    try {
      const params = new URLSearchParams({
        supplement: supplementName,
        page: (currentPage + 1).toString(),
        pageSize: '30'
      });
      
      if (selectedYear) {
        params.append('startYear', selectedYear.toString());
        params.append('endYear', selectedYear.toString());
      }
      
      const response = await fetch(`/api/timeline?${params}`);
      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.error || 'Failed to load data');
      }
      
      setStudies(prev => [...prev, ...result.data]);
      setCurrentPage(currentPage + 1);
      setHasMore(result.hasMore);
    } catch (error) {
      console.error('Error loading more studies:', error);
    } finally {
      setLoading(false);
    }
  }, [supplementName, currentPage, hasMore, loading, selectedYear]);

  const filterByYear = useCallback(async (year: number | null) => {
    setLoading(true);
    setSelectedYear(year);
    setCurrentPage(0);
    
    try {
      const params = new URLSearchParams({
        supplement: supplementName,
        page: '0',
        pageSize: '30'
      });
      
      if (year) {
        params.append('startYear', year.toString());
        params.append('endYear', year.toString());
      }
      
      const response = await fetch(`/api/timeline?${params}`);
      const result = await response.json();
      
      if (!response.ok) {
        throw new Error(result.error || 'Failed to load data');
      }
      
      setStudies(result.data);
      setHasMore(result.hasMore);
    } catch (error) {
      console.error('Error filtering by year:', error);
    } finally {
      setLoading(false);
    }
  }, [supplementName]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short'
    });
  };

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

  // Generate year options
  const years = initialData.dateRange ? 
    Array.from(
      { length: initialData.dateRange.end - initialData.dateRange.start + 1 }, 
      (_, i) => initialData.dateRange.end - i
    ) : [];

  return (
    <Card className="border-none shadow-md">
      <CardHeader className="pb-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <CardTitle className="text-xl font-semibold flex items-center">
            <Calendar className="w-5 h-5 mr-2 text-primary/70" />
            Research Timeline
          </CardTitle>
          
          {/* Year Filter */}
          <div className="flex items-center gap-2">
            <select
              value={selectedYear || ''}
              onChange={(e) => filterByYear(e.target.value ? parseInt(e.target.value) : null)}
              className="px-3 py-1 text-sm border rounded-md bg-white"
              disabled={loading}
            >
              <option value="">All Years</option>
              {years.map(year => (
                <option key={year} value={year}>
                  {year} ({initialData.yearCounts[year] || 0})
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>Total: {initialData.totalStudies.toLocaleString()} studies</span>
          {initialData.dateRange && (
            <span>
              {initialData.dateRange.start} - {initialData.dateRange.end}
            </span>
          )}
          {selectedYear && (
            <span className="text-primary">
              Filtered: {selectedYear}
            </span>
          )}
        </div>
      </CardHeader>
      
      <CardContent>
        {/* Studies List */}
        <div className="space-y-4 mb-6">
          {studies.map((study, index) => (
            <div key={study.id} className="flex gap-4 p-4 rounded-lg border border-muted/50">
              <div className="flex-shrink-0 w-16 text-center">
                <div className="text-sm font-medium text-primary">
                  {formatDate(study.publication_date)}
                </div>
              </div>
              
              <div className="flex-grow min-w-0">
                <div className="flex flex-wrap gap-1 mb-2">
                  {study.publication_types.slice(0, 2).map((type, idx) => (
                    <span 
                      key={idx}
                      className={`px-2 py-0.5 rounded text-xs font-medium ${getPublicationTypeBadgeColor(type)}`}
                    >
                      {type}
                    </span>
                  ))}
                  {study.publication_types.length > 2 && (
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                      +{study.publication_types.length - 2} more
                    </span>
                  )}
                </div>
                
                <h4 className="text-sm font-medium mb-1 line-clamp-2">
                  {study.title}
                </h4>
                
                <p className="text-xs text-muted-foreground">
                  {study.journal}
                </p>
              </div>
            </div>
          ))}
        </div>
        
        {/* Load More Button */}
        {hasMore && (
          <div className="text-center">
            <Button 
              onClick={loadMoreStudies}
              disabled={loading}
              variant="outline"
              className="w-full sm:w-auto"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4 mr-2" />
                  Load More Studies
                </>
              )}
            </Button>
          </div>
        )}
        
        {!hasMore && studies.length > 0 && (
          <div className="text-center text-sm text-muted-foreground">
            {selectedYear ? 
              `All studies from ${selectedYear} loaded` : 
              'All studies loaded'
            }
          </div>
        )}
        
        {studies.length === 0 && !loading && (
          <div className="text-center text-muted-foreground py-8">
            {selectedYear ? 
              `No studies found for ${selectedYear}` : 
              'No studies available'
            }
          </div>
        )}
      </CardContent>
    </Card>
  );
}