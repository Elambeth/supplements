import { createClient } from '@supabase/supabase-js';

// Initialize the Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Helper functions for supplements
export async function getAllSupplements() {
  const { data, error } = await supabase
    .from('supplements')
    .select('*')
    .order('name');
  
  if (error) {
    console.error('Error fetching supplements:', error);
    return [];
  }
  
  return data || [];
}

export async function getPopularSupplements() {
  const { data, error } = await supabase
    .from('supplements')
    .select('*')
    .eq('is_popular', true)
    .order('name');
  
  if (error) {
    console.error('Error fetching popular supplements:', error);
    return [];
  }
  
  return data || [];
}

export async function getSupplementsByFirstLetter() {
  const { data, error } = await supabase
    .from('supplements')
    .select('name')
    .order('name');
  
  if (error) {
    console.error('Error fetching supplements by letter:', error);
    return {};
  }
  
  // Process the data to get supplements organized by first letter
  const supplementsByLetter: Record<string, string[]> = {};
  
  (data || []).forEach(supplement => {
    let firstChar = supplement.name.charAt(0).toLowerCase();
    
    // Check if the first character is a number
    if (!isNaN(parseInt(firstChar))) {
      // Group all numeric first characters under '0-9'
      if (!supplementsByLetter['0-9']) {
        supplementsByLetter['0-9'] = [];
      }
      supplementsByLetter['0-9'].push(supplement.name);
    } else {
      // Group alphabetic first characters
      if (!supplementsByLetter[firstChar]) {
        supplementsByLetter[firstChar] = [];
      }
      supplementsByLetter[firstChar].push(supplement.name);
    }
  });
  
  return supplementsByLetter;
}

export async function getSupplementByName(name: string) {
  const { data, error } = await supabase
    .from('supplements')
    .select('*')
    .eq('name', name)
    .single();
  
  if (error) {
    console.error(`Error fetching supplement with name ${name}:`, error);
    return null;
  }
  
  return data;
}
// Add this to your supabase.ts file or replace the existing function

// Replace your existing getSupplementWithResearch function with this one

export async function getSupplementWithResearch(name: string) {
  console.log(`Fetching supplement data for: ${name}`);
  
  // First get the basic supplement data with research and studies
  const { data: supplement, error: supplementError } = await supabase
    .from('supplements')
    .select(`
      *,
      supplement_research (
        research_count,
        retrieved_count,
        search_date,
        last_updated,
        query,
        rank_position,
        rank_total,
        rank_percentile
      ),
      supplement_studies (
        id,
        pmid,
        title,
        abstract,
        journal,
        publication_date,
        publication_types,
        authors
      )
    `)
    .eq('name', name)
    .single();
  
  if (supplementError) {
    console.error(`Error fetching supplement with research for ${name}:`, supplementError);
    return null;
  }
  
  // Then get the aggregates separately - this is more reliable
  const { data: aggregates, error: aggregatesError } = await supabase
    .from('supplement_research_aggregates')
    .select('*')
    .eq('supplement_id', supplement.id);
  
  if (aggregatesError) {
    console.error(`Error fetching aggregates for supplement ID ${supplement.id}:`, aggregatesError);
  } else {
    // Add the aggregates to the supplement object
    if (aggregates && aggregates.length > 0) {
      console.log(`Found aggregates data for ${name} (ID: ${supplement.id})`);
      supplement.supplement_research_aggregates = aggregates;
    } else {
      console.log(`No aggregates found for ${name} (ID: ${supplement.id})`);
      supplement.supplement_research_aggregates = null;
    }
  }
  
  return supplement;
}
// Function to get studies by publication type
export async function getSupplementStudiesByType(supplementId: number, publicationTypes: string[] = []) {
  let query = supabase
    .from('supplement_studies')
    .select('*')
    .eq('supplement_id', supplementId);

  if (publicationTypes.length > 0) {
    // Create an OR condition for each publication type
    const conditions = publicationTypes.map(type => `publication_types.cs.{${type}}`);
    query = query.or(conditions.join(','));
  }

  const { data, error } = await query.order('publication_date', { ascending: false });
  
  if (error) {
    console.error(`Error fetching supplement studies for ID ${supplementId}:`, error);
    return [];
  }
  
  return data || [];
}

// Add this to your supabase.ts file
export async function countAggregateRecords() {
  const { count, error } = await supabase
    .from('supplement_research_aggregates')
    .select('*', { count: 'exact', head: true });
  
  if (error) {
    console.error("Error counting aggregate records:", error);
    return 0;
  }
  
  return count;
}


// Add these functions to your existing supabase.ts file

/**
 * Get total count of supplements in the database
 */
export async function getTotalSupplementsCount() {
  const { count, error } = await supabase
    .from('supplements')
    .select('*', { count: 'exact', head: true });
  
  if (error) {
    console.error('Error counting supplements:', error);
    return 0;
  }
  
  return count || 0;
}

/**
 * Get total count of research papers across all supplements
 */
export async function getTotalResearchPapersCount() {
  const { data, error } = await supabase
    .from('supplement_research')
    .select('research_count');
  
  if (error) {
    console.error('Error fetching research counts:', error);
    return 0;
  }
  
  // Sum up all research_count values
  const totalPapers = (data || []).reduce((sum, item) => sum + (item.research_count || 0), 0);
  
  return totalPapers;
}

/**
 * Get both counts in a single function for efficiency
 */
export async function getDatabaseStats() {
  const [supplementsCount, papersCount] = await Promise.all([
    getTotalSupplementsCount(),
    getTotalResearchPapersCount()
  ]);
  
  return {
    totalSupplements: supplementsCount,
    totalPapers: papersCount
  };
}

// Function to get important studies (RCTs, meta-analyses, etc.)
export async function getImportantStudies(supplementId: number) {
  const importantTypes = [
    "Randomized Controlled Trial", 
    "Multicenter Study", 
    "Systematic Review", 
    "Meta-Analysis"
  ];

  return getSupplementStudiesByType(supplementId, importantTypes);
}

// Add this function to your /lib/supabase.ts file

// ✅ Optimized function - only fetch what search needs
export async function getSupplementsForSearch() {
  const { data, error } = await supabase
    .from('supplements')
    .select('id, name') // Only name for search, id for navigation
    .order('name');
    
  if (error) {
    console.error('Error fetching supplements for search:', error);
    return [];
  }
  
  return data || [];
}

// Add these new optimized functions to your supabase.ts file

/**
 * ✅ Get basic supplement info only - fast and lightweight
 */
export async function getBasicSupplement(name: string) {
  const { data, error } = await supabase
    .from('supplements')
    .select('*')
    .eq('name', name)
    .single();
  
  if (error) {
    console.error(`Error fetching basic supplement ${name}:`, error);
    return null;
  }
  
  return data;
}

/**
 * ✅ Get research statistics only - targeted for metrics display
 */
export async function getResearchStats(name: string) {
  // First get the supplement ID
  const { data: supplement, error: supplementError } = await supabase
    .from('supplements')
    .select('id')
    .eq('name', name)
    .single();
    
  if (supplementError || !supplement) {
    console.error(`Error fetching supplement ID for ${name}:`, supplementError);
    return null;
  }

  // Get research stats and aggregates in parallel
  const [researchResult, aggregatesResult] = await Promise.all([
    supabase
      .from('supplement_research')
      .select('*')
      .eq('supplement_id', supplement.id)
      .single(),
    supabase
      .from('supplement_research_aggregates')
      .select('*')
      .eq('supplement_id', supplement.id)
  ]);

  const research = researchResult.data;
  const aggregates = aggregatesResult.data;

  if (researchResult.error) {
    console.error(`Error fetching research stats for ${name}:`, researchResult.error);
  }
  
  if (aggregatesResult.error) {
    console.error(`Error fetching aggregates for ${name}:`, aggregatesResult.error);
  }

  return {
    research,
    aggregates: aggregates && aggregates.length > 0 ? aggregates[0] : null
  };
}

/**
 * ✅ Get key studies only - limited and filtered for performance
 */
export async function getKeyStudies(name: string, limit: number = 5) {
  // First get the supplement ID
  const { data: supplement, error: supplementError } = await supabase
    .from('supplements')
    .select('id')
    .eq('name', name)
    .single();
    
  if (supplementError || !supplement) {
    console.error(`Error fetching supplement ID for ${name}:`, supplementError);
    return [];
  }

  // Important study types for filtering
  const importantTypes = [
    "Randomized Controlled Trial", 
    "Multicenter Study", 
    "Systematic Review", 
    "Meta-Analysis"
  ];

  const { data, error } = await supabase
    .from('supplement_studies')
    .select('*')
    .eq('supplement_id', supplement.id)
    .order('publication_date', { ascending: false })
    .limit(limit * 3); // Get more than needed since we'll filter
  
  if (error) {
    console.error(`Error fetching key studies for ${name}:`, error);
    return [];
  }

  // Filter for important study types and limit results
  const keyStudies = (data || [])
    .filter(study => 
      study.publication_types?.some((type: string) => importantTypes.includes(type))
    )
    .slice(0, limit);

  return keyStudies;
}

/**
 * ✅ Get all studies for a supplement (for dedicated studies page)
 */
export async function getAllStudies(name: string) {
  // First get the supplement ID
  const { data: supplement, error: supplementError } = await supabase
    .from('supplements')
    .select('id')
    .eq('name', name)
    .single();
    
  if (supplementError || !supplement) {
    console.error(`Error fetching supplement ID for ${name}:`, supplementError);
    return [];
  }

  const { data, error } = await supabase
    .from('supplement_studies')
    .select('*')
    .eq('supplement_id', supplement.id)
    .order('publication_date', { ascending: false });
  
  if (error) {
    console.error(`Error fetching all studies for ${name}:`, error);
    return [];
  }
  
  return data || [];
}

/**
 * ✅ Get timeline data for research timeline component
 */
export async function getTimelineData(name: string, limit: number = 20) {
  // First get the supplement ID
  const { data: supplement, error: supplementError } = await supabase
    .from('supplements')
    .select('id')
    .eq('name', name)
    .single();
    
  if (supplementError || !supplement) {
    console.error(`Error fetching supplement ID for ${name}:`, supplementError);
    return [];
  }

  const { data, error } = await supabase
    .from('supplement_studies')
    .select('id, title, publication_date, publication_types, journal')
    .eq('supplement_id', supplement.id)
    .order('publication_date', { ascending: false })
    .limit(limit);
  
  if (error) {
    console.error(`Error fetching timeline data for ${name}:`, error);
    return [];
  }
  
  return data || [];
}

// New function to get top researched supplements
export async function getMostResearchedSupplements(limit: number = 10) {
  const { data, error } = await supabase
    .from('supplement_research')
    .select(`
      research_count,
      rank_position,
      supplement_id,
      supplements (
        name
      )
    `)
    .order('research_count', { ascending: false })
    .limit(limit);
  
  if (error) {
    console.error('Error fetching most researched supplements:', error);
    return [];
  }
  
  return data || [];
}

/**
 * Fetches all supplements with their research data
 */
export async function getAllSupplementsWithResearch() {
  const { data, error } = await supabase
    .from('supplements')
    .select(`
      *,
      supplement_research (
        research_count,
        retrieved_count,
        search_date,
        last_updated,
        query,
        rank_position,
        rank_total,
        rank_percentile
      )
    `)
    .order('name');

  if (error) {
    console.error('Error fetching supplements with research:', error);
    return [];
  }


  
  return data || [];
}