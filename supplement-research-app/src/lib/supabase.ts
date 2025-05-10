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

// Function to get supplement with research data and studies
export async function getSupplementWithResearch(name: string) {
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
  
  if (error) {
    console.error(`Error fetching supplement with research for ${name}:`, error);
    return null;
  }
  
  return data;
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