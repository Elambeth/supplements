"use client";

import React, { useState } from 'react';
import { Calendar, TrendingUp, Award, Users, ExternalLink } from 'lucide-react';

const ResearchTimeline = ({ studies, supplementName }) => {
  const [selectedPeriod, setSelectedPeriod] = useState('all');
  
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
        study.citation_count > 100) {
      acc[year].breakthroughs++;
    }
    
    return acc;
  }, {});
  
  const timeline = Object.values(timelineData).sort((a, b) => b.year - a.year);
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center">
          <Calendar className="w-5 h-5 mr-2 text-blue-500" />
          Research Timeline
        </h3>
        
        <select 
          value={selectedPeriod}
          onChange={(e) => setSelectedPeriod(e.target.value)}
          className="px-3 py-1 rounded-md border border-gray-200 text-sm"
        >
          <option value="all">All Years</option>
          <option value="recent">Last 5 Years</option>
          <option value="decade">Last Decade</option>
        </select>
      </div>
      
      <div className="relative">
        {/* Timeline line - smaller and black */}
        <div className="absolute left-1.5 top-0 bottom-0 w-0.5 bg-black"></div>
        
        <div className="space-y-6">
          {timeline.map((yearData, index) => (
            <div key={yearData.year} className="relative flex items-start">
              {/* Year marker - much smaller solid black circle */}
              <div className="flex-shrink-0 w-3 h-3 bg-black rounded-full relative z-10">
              </div>
              
              {/* Content */}
              <div className="ml-4 flex-grow">
                <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-lg">{yearData.year}</h4>
                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <span className="flex items-center">
                        <TrendingUp className="w-4 h-4 mr-1" />
                        {yearData.studies.length} studies
                      </span>
                      {yearData.participants > 0 && (
                        <span className="flex items-center">
                          <Users className="w-4 h-4 mr-1" />
                          {yearData.participants.toLocaleString()} participants
                        </span>
                      )}
                      {yearData.breakthroughs > 0 && (
                        <span className="flex items-center text-amber-600">
                          <Award className="w-4 h-4 mr-1" />
                          {yearData.breakthroughs} breakthrough{yearData.breakthroughs > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  {/* Key findings for the year */}
                  <div className="text-sm text-gray-700">
                    <p className="mb-2">
                      Research focus: {getResearchFocus(yearData.studies)}
                    </p>
                    
                    {/* Notable studies with clickable PubMed links - show ALL studies, not just RCTs */}
                    {yearData.studies
                      .slice(0, 3) // Show up to 3 studies per year
                      .map(study => (
                        <div key={study.id} className="bg-gray-50 rounded p-2 mb-2 text-xs">
                          <div className="font-medium">{study.title.slice(0, 80)}...</div>
                          <div className="flex items-center justify-between mt-1">
                            <div className="text-gray-500">{study.journal}</div>
                            {study.pmid && (
                              <a 
                                href={`https://pubmed.ncbi.nlm.nih.gov/${study.pmid}/`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center text-blue-600 hover:text-blue-800 transition-colors"
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
                  <div className="mt-3 flex items-center">
                    <div className="flex-grow bg-gray-200 rounded-full h-2">
                      <div 
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-300"
                        style={{ 
                          width: `${Math.min(100, (yearData.studies.length / Math.max(...timeline.map(t => t.studies.length))) * 100)}%` 
                        }}
                      ></div>
                    </div>
                    <span className="ml-2 text-xs text-gray-500">
                      {yearData.studies.length > 5 ? 'High' : yearData.studies.length > 2 ? 'Medium' : 'Low'} activity
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Helper function to determine research focus
const getResearchFocus = (studies) => {
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
  
  const maxTopic = Object.entries(topics).reduce((a, b) => topics[a[0]] > topics[b[0]] ? a : b);
  
  const focusMap = {
    dosage: 'Optimal dosing strategies',
    safety: 'Safety and tolerability',
    efficacy: 'Clinical effectiveness',
    mechanism: 'Mechanisms of action',
    population: 'Population-specific effects'
  };
  
  return focusMap[maxTopic[0]] || 'General research';
};

export default ResearchTimeline;