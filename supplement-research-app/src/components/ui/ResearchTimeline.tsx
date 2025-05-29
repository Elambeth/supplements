"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Calendar, TrendingUp, Award, Users, ExternalLink, ChevronUp, ChevronDown } from 'lucide-react';

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

interface ResearchTimelineProps {
  studies: Study[];
  supplementName: string;
  onHeightChange?: (height: number) => void; // New callback prop
}

const ResearchTimeline: React.FC<ResearchTimelineProps> = ({ studies, supplementName, onHeightChange }) => {
  const [selectedPeriod, setSelectedPeriod] = useState('all');
  const [isExpanded, setIsExpanded] = useState(false);
  
  // Maximum number of cards to show when collapsed
  const MAX_COLLAPSED_CARDS = 3;
  
  // Group studies by year and calculate metrics
  const timelineData = studies.reduce((acc, study) => {
    const year = new Date(study.publication_date).getFullYear();
    if (!acc[year]) {
      acc[year] = {
        year,
        studies: [],
        qualityScore: 0,
        participants: 0,
        breakthroughs: 0
      };
    }
    
    acc[year].studies.push(study);
    acc[year].qualityScore += study.quality_score || 0;
    acc[year].participants += study.participant_count || 0;
    
    // Mark breakthrough studies
    if (study.publication_types?.includes('Meta-Analysis') || 
        study.citation_count && study.citation_count > 100) {
      acc[year].breakthroughs++;
    }
    
    return acc;
  }, {} as Record<number, {
    year: number;
    studies: Study[];
    qualityScore: number;
    participants: number;
    breakthroughs: number;
  }>);
  
  const timeline = Object.values(timelineData).sort((a, b) => b.year - a.year);

  // Filter timeline based on selected period
  const filteredTimeline = timeline.filter(yearData => {
    const currentYear = new Date().getFullYear();
    switch (selectedPeriod) {
      case 'recent':
        return yearData.year >= currentYear - 5;
      case 'decade':
        return yearData.year >= currentYear - 10;
      default:
        return true;
    }
  });

  // Limit displayed timeline when collapsed
  const displayedTimeline = isExpanded 
    ? filteredTimeline 
    : filteredTimeline.slice(0, MAX_COLLAPSED_CARDS);

  const hasMoreCards = filteredTimeline.length > MAX_COLLAPSED_CARDS;

  // Calculate and communicate height changes
  useEffect(() => {
    const calculateHeight = () => {
      const baseHeight = 100; // Header and padding
      const cardHeight = 320; // Height per card when expanded
      const collapsedHeight = 200; // Height when collapsed
      const indicatorHeight = hasMoreCards && !isExpanded ? 60 : 0; // Height for "more years" indicator
      
      if (isExpanded) {
        return baseHeight + (displayedTimeline.length * cardHeight) + indicatorHeight;
      } else {
        return baseHeight + collapsedHeight + indicatorHeight;
      }
    };

    const height = calculateHeight();
    onHeightChange?.(height);
  }, [isExpanded, displayedTimeline.length, hasMoreCards, onHeightChange]);

  const getStackedStyle = (index: number) => {
    if (isExpanded) {
      return {
        y: 0,
        rotate: 0,
        scale: 1,
        zIndex: index,
      };
    }

    // When collapsed, limit the stacking offset to prevent overflow
    const maxVisibleIndex = Math.min(index, MAX_COLLAPSED_CARDS - 1);
    return {
      y: -maxVisibleIndex * 12, // Increased from 8 to 12 for more visible stacking
      rotate: 0,
      scale: 1 - maxVisibleIndex * 0.025, // Slightly increased scale difference
      zIndex: displayedTimeline.length - index,
    };
  };

  // Generate subtle gray shades for each year
  const getGrayShade = (index: number) => {
    const shades = [
      'bg-gray-50',
      'bg-gray-100',
      'bg-slate-50',
      'bg-slate-100',
      'bg-zinc-50',
      'bg-zinc-100',
      'bg-neutral-50',
      'bg-neutral-100'
    ];
    return shades[index % shades.length];
  };
  
  // Helper function to determine research focus
  const getResearchFocus = (studies: Study[]) => {
    const topics = studies.reduce((acc, study) => {
      // Extract key terms from titles/abstracts
      const text = (study.title + ' ' + (study.abstract || '')).toLowerCase();
      
      if (text.includes('dosage') || text.includes('dose')) acc.dosage++;
      if (text.includes('safety') || text.includes('adverse')) acc.safety++;
      if (text.includes('efficacy') || text.includes('effectiveness')) acc.efficacy++;
      if (text.includes('mechanism') || text.includes('pathway')) acc.mechanism++;
      if (text.includes('population') || text.includes('demographic')) acc.population++;
      
      return acc;
    }, { dosage: 0, safety: 0, efficacy: 0, mechanism: 0, population: 0 });
    
    const maxTopic = Object.entries(topics).reduce((a, b) => topics[a[0] as keyof typeof topics] > topics[b[0] as keyof typeof topics] ? a : b);
    
    const focusMap: Record<string, string> = {
      dosage: 'Optimal dosing strategies',
      safety: 'Safety and tolerability',
      efficacy: 'Clinical effectiveness',
      mechanism: 'Mechanisms of action',
      population: 'Population-specific effects'
    };
    
    return focusMap[maxTopic[0]] || 'General research';
  };

  if (!studies || studies.length === 0) {
    return (
      <div className="space-y-6">
        <h3 className="text-lg font-semibold flex items-center">
          <Calendar className="w-5 h-5 mr-2 text-blue-500" />
          Research Timeline
        </h3>
        <div className="p-8 text-center text-gray-500">
          <Calendar className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>No research studies available for timeline visualization.</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center">
          <Calendar className="w-5 h-5 mr-2 text-blue-500" />
          Research Timeline
        </h3>
        
        <div className="flex items-center space-x-3">
          
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 px-3 py-1 text-sm border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                Collapse
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                {hasMoreCards ? `Show All (${filteredTimeline.length})` : 'Expand'}
              </>
            )}
          </button>
        </div>
      </div>
      
      <div className="relative w-full">
        <AnimatePresence>
          {displayedTimeline.map((yearData, index) => (
            <motion.div
              key={yearData.year}
              className="absolute w-full"
              initial={getStackedStyle(index)}
              animate={getStackedStyle(index)}
              whileHover={
                isExpanded
                  ? {
                      scale: 1.01,
                      zIndex: 999,
                      y: -5,
                      transition: { duration: 0.2 },
                    }
                  : {}
              }
              transition={{
                duration: 0.6,
                ease: [0.25, 0.46, 0.45, 0.94],
                delay: isExpanded ? index * 0.1 : (displayedTimeline.length - index - 1) * 0.1,
              }}
              style={{
                top: isExpanded ? index * 324 : 0, // Increased spacing from 240 to 280
              }}
            >
              <div className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-300 cursor-pointer overflow-hidden">
                {/* Year Header */}
                <div className={`${getGrayShade(index)} p-4 border-b border-gray-200`}>
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-xl flex items-center text-gray-800">
                      <Calendar className="w-5 h-5 mr-2" />
                      {yearData.year}
                    </h4>
                    <div className="flex items-center space-x-3 text-sm">
                      <span className="flex items-center bg-gray-100 text-gray-700 rounded-full px-2 py-1">
                        <TrendingUp className="w-4 h-4 mr-1" />
                        {yearData.studies.length} studies
                      </span>
                      {yearData.participants > 0 && (
                        <span className="flex items-center bg-gray-100 text-gray-700 rounded-full px-2 py-1">
                          <Users className="w-4 h-4 mr-1" />
                          {yearData.participants.toLocaleString()}
                        </span>
                      )}
                      {yearData.breakthroughs > 0 && (
                        <span className="flex items-center bg-amber-100 text-amber-800 rounded-full px-2 py-1">
                          <Award className="w-4 h-4 mr-1" />
                          {yearData.breakthroughs}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Content */}
                <div className="p-4">
                  {/* Research focus */}
                  <div className="mb-3">
                    <p className="text-sm font-medium text-gray-700">
                      Research Focus: <span className="text-blue-600">{getResearchFocus(yearData.studies)}</span>
                    </p>
                  </div>
                  
                  {/* Notable studies */}
                  <div className="space-y-2">
                    <h5 className="text-sm font-semibold text-gray-800 mb-2">Notable Studies:</h5>
                    {yearData.studies
                      .slice(0, 2)
                      .map(study => (
                        <div key={study.id} className="bg-gray-50 rounded-md p-2 text-sm hover:bg-gray-100 transition-colors">
                          <div className="font-medium text-gray-900 mb-1 text-xs leading-tight">
                            {study.title.slice(0, 70)}...
                          </div>
                          <div className="flex items-center justify-between">
                            <div className="text-gray-600 text-xs truncate mr-2">{study.journal}</div>
                            {study.pmid && (
                              <a 
                                href={`https://pubmed.ncbi.nlm.nih.gov/${study.pmid}/`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center text-blue-600 hover:text-blue-800 transition-colors text-xs whitespace-nowrap"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <ExternalLink className="w-3 h-3 mr-1" />
                                PubMed
                              </a>
                            )}
                          </div>
                        </div>
                      ))
                    }
                  </div>
                  
                  {/* Research momentum indicator */}
                  <div className="mt-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium text-gray-600">Research Activity</span>
                      <span className="text-xs text-gray-500">
                        {yearData.studies.length > 5 ? 'High' : yearData.studies.length > 2 ? 'Medium' : 'Low'}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
                        style={{ 
                          width: `${Math.min(100, (yearData.studies.length / Math.max(...displayedTimeline.map(t => t.studies.length))) * 100)}%` 
                        }}
                      ></div>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Spacer to prevent layout shift */}
        <div
          className="transition-all duration-600"
          style={{
            height: isExpanded ? displayedTimeline.length * 280 - 20 : 200, // Updated to match new spacing
          }}
        />
        
        {/* Show indicator when cards are hidden */}
        {!isExpanded && hasMoreCards && (
          <div className="mt-4 text-center">
            <div className="inline-flex items-center px-3 py-2 text-sm text-gray-600 bg-gray-50 rounded-full border border-gray-200">
              <Calendar className="w-4 h-4 mr-2" />
              {filteredTimeline.length - MAX_COLLAPSED_CARDS} more years available
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResearchTimeline;