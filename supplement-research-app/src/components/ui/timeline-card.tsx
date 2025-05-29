// First, create a new client component file: components/timeline-card.tsx

"use client";

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import ResearchTimeline from '@/components/ui/ResearchTimeline';

interface Study {
  id: number;
  pmid: string;
  title: string;
  abstract: string;
  journal: string;
  publication_date: string;
  publication_types: string[];
  authors: string[];
  quality_score?: number;
  participant_count?: number;
  citation_count?: number;
}

interface TimelineCardProps {
  studies: Study[];
  supplementName: string;
}

export function TimelineCard({ studies, supplementName }: TimelineCardProps) {
  const [cardHeight, setCardHeight] = useState(450);

  const handleHeightChange = (height: number) => {
    // Add some padding to account for card padding and ensure smooth transitions
    setCardHeight(Math.max(450, height + 48)); // 48px for card padding
  };

  return (
    <Card 
      className="border-none shadow-md transition-all duration-700 ease-in-out overflow-visible"
      style={{ minHeight: `${cardHeight}px` }}
    >
      <CardContent>
        <ResearchTimeline 
          studies={studies} 
          supplementName={supplementName}
          onHeightChange={handleHeightChange}
        />
      </CardContent>
    </Card>
  );
}
