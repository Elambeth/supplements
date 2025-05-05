'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowUpDown, ExternalLink, Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

type Supplement = {
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
};

type SortField = 'rank' | 'name' | 'studies' | 'evidence';
type SortDirection = 'asc' | 'desc';

interface ResearchTableProps {
  supplements: Supplement[];
}

export function ResearchTable({ supplements }: ResearchTableProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('studies');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [evidenceFilter, setEvidenceFilter] = useState('all');

  // Filter supplements based on search query and evidence filter
  const filteredSupplements = supplements.filter((supplement) => {
    const matchesSearch = supplement.name.toLowerCase().includes(searchQuery.toLowerCase());
    
    if (evidenceFilter === 'all') return matchesSearch;
    
    if (evidenceFilter === 'strong') {
      return matchesSearch && supplement.sentiment_score !== null && supplement.sentiment_score >= 7;
    }
    
    if (evidenceFilter === 'moderate') {
      return matchesSearch && supplement.sentiment_score !== null && supplement.sentiment_score >= 4 && supplement.sentiment_score < 7;
    }
    
    if (evidenceFilter === 'limited') {
      return matchesSearch && supplement.sentiment_score !== null && supplement.sentiment_score < 4;
    }
    
    if (evidenceFilter === 'not-analyzed') {
      return matchesSearch && supplement.sentiment_score === null;
    }
    
    return matchesSearch;
  });

  // Sort supplements based on selected field and direction
  const sortedSupplements = [...filteredSupplements].sort((a, b) => {
    if (sortField === 'rank') {
      const aPosition = a.supplement_research?.[0]?.rank_position || Infinity;
      const bPosition = b.supplement_research?.[0]?.rank_position || Infinity;
      return sortDirection === 'asc' ? aPosition - bPosition : bPosition - aPosition;
    }
    
    if (sortField === 'name') {
      return sortDirection === 'asc' 
        ? a.name.localeCompare(b.name)
        : b.name.localeCompare(a.name);
    }
    
    if (sortField === 'studies') {
      const aCount = a.supplement_research?.[0]?.research_count || 0;
      const bCount = b.supplement_research?.[0]?.research_count || 0;
      return sortDirection === 'asc' ? aCount - bCount : bCount - aCount;
    }
    
    if (sortField === 'evidence') {
      const aScore = a.sentiment_score || 0;
      const bScore = b.sentiment_score || 0;
      return sortDirection === 'asc' ? aScore - bScore : bScore - aScore;
    }
    
    return 0;
  });

  // Handle sort click
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction if clicking the same field
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // Set new field and default to desc for rank and studies, asc for name
      setSortField(field);
      if (field === 'rank' || field === 'studies' || field === 'evidence') {
        setSortDirection('desc');
      } else {
        setSortDirection('asc');
      }
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Search input */}
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search supplements..."
            className="pl-8"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        
        {/* Evidence filter */}
        <div className="w-full sm:w-48">
          <Select 
            value={evidenceFilter} 
            onValueChange={(value) => setEvidenceFilter(value)}
          >
            <SelectTrigger>
              <SelectValue placeholder="Evidence" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Evidence</SelectItem>
              <SelectItem value="strong">Strong Evidence</SelectItem>
              <SelectItem value="moderate">Moderate Evidence</SelectItem>
              <SelectItem value="limited">Limited Evidence</SelectItem>
              <SelectItem value="not-analyzed">Not Analyzed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[80px]">
                <Button
                  variant="ghost"
                  onClick={() => handleSort('rank')}
                  className="h-8 p-0 font-semibold"
                >
                  Rank
                  <ArrowUpDown className="ml-2 h-4 w-4" />
                </Button>
              </TableHead>
              
              <TableHead>
                <Button
                  variant="ghost"
                  onClick={() => handleSort('name')}
                  className="h-8 p-0 font-semibold"
                >
                  Supplement
                  <ArrowUpDown className="ml-2 h-4 w-4" />
                </Button>
              </TableHead>
              
              <TableHead className="text-center">
                <Button
                  variant="ghost"
                  onClick={() => handleSort('studies')}
                  className="h-8 p-0 font-semibold"
                >
                  Studies
                  <ArrowUpDown className="ml-2 h-4 w-4" />
                </Button>
              </TableHead>
              
              <TableHead className="text-center">Percentile</TableHead>
              
              <TableHead className="text-center">
                <Button
                  variant="ghost"
                  onClick={() => handleSort('evidence')}
                  className="h-8 p-0 font-semibold"
                >
                  Evidence Rating
                  <ArrowUpDown className="ml-2 h-4 w-4" />
                </Button>
              </TableHead>
              
              <TableHead className="text-center">Last Updated</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedSupplements.map((supplement, index) => {
              // Determine sentiment color and label based on sentiment score
              let sentimentColor = 'bg-gray-100 text-gray-500';
              let sentimentLabel = 'Not analyzed';
              
              if (supplement.sentiment_score !== null) {
                if (supplement.sentiment_score >= 7) {
                  sentimentColor = 'bg-green-100 text-green-700';
                  sentimentLabel = 'Strong';
                } else if (supplement.sentiment_score >= 4) {
                  sentimentColor = 'bg-amber-100 text-amber-700';
                  sentimentLabel = 'Moderate';
                } else {
                  sentimentColor = 'bg-red-100 text-red-700';
                  sentimentLabel = 'Limited';
                }
              }

              // Format date
              const formattedDate = new Date(supplement.last_research_check).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              });

              return (
                <TableRow 
                  key={supplement.id}
                  className="cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => window.location.href = `/supplement/${encodeURIComponent(supplement.name)}`}
                >
                  <TableCell className="font-medium text-center">
                    {supplement.supplement_research?.[0]?.rank_position || '-'}
                  </TableCell>
                  
                  <TableCell>
                    <div className="flex items-center">
                      <span className="font-medium">{supplement.name}</span>
                      {supplement.is_popular && (
                        <Badge variant="outline" className="ml-2 bg-blue-50 text-blue-700 border-0">
                          Popular
                        </Badge>
                      )}
                    </div>
                  </TableCell>

                  <TableCell className="text-center font-medium">
                    {supplement.supplement_research?.[0]?.research_count.toLocaleString() || '0'}
                  </TableCell>

                  <TableCell className="text-center">
                    {supplement.supplement_research?.[0]?.rank_percentile ? (
                      <Badge variant="outline" className="bg-purple-50 text-purple-700 border-0">
                        Top {supplement.supplement_research[0].rank_percentile}%
                      </Badge>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>

                  <TableCell className="text-center">
                    <Badge variant="outline" className={`${sentimentColor} border-0`}>
                      {sentimentLabel}
                      {supplement.sentiment_score !== null && ` (${supplement.sentiment_score}/10)`}
                    </Badge>
                  </TableCell>

                  <TableCell className="text-center text-muted-foreground text-sm">
                    {formattedDate}
                  </TableCell>

                  <TableCell className="text-right">
                    <Link 
                      href={`/supplement/${encodeURIComponent(supplement.name)}`}
                      className="inline-block"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                        <span className="sr-only">View details</span>
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </Link>
                  </TableCell>
                </TableRow>
              );
            })}
            
            {sortedSupplements.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="h-24 text-center">
                  No supplements found matching your criteria
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
      
      <div className="text-sm text-muted-foreground text-center">
        Showing {sortedSupplements.length} out of {supplements.length} supplements
      </div>
    </div>
  );
}