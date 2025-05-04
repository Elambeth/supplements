#!/usr/bin/env node

const path = require('path');
// Load .env file from the scripts directory where the script is located
require('dotenv').config({ path: path.resolve(__dirname, '.env') });
const fs = require('fs');
const { createClient } = require('@supabase/supabase-js');

// Supabase configuration
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

// Validate Supabase credentials
if (!supabaseUrl || !supabaseKey) {
  console.error('Error: Missing Supabase credentials.');
  console.error('Please create a .env file with NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY variables.');
  process.exit(1);
}

// Initialize Supabase client
const supabase = createClient(supabaseUrl, supabaseKey);

/**
 * Processes the JSON file and inserts supplements into Supabase
 * @param {string} filePath - Path to the JSON file containing supplements
 */
async function importSupplements(filePath) {
  try {
    // Read and parse the JSON file
    const rawData = fs.readFileSync(filePath, 'utf8');
    const data = JSON.parse(rawData);
    
    // Extract all supplements from the alphabetical organization
    const allSupplements = [];
    const interventionsByLetter = data.interventions_by_letter;
    
    // Collect all supplements from different letter categories
    for (const letter in interventionsByLetter) {
      const supplements = interventionsByLetter[letter];
      supplements.forEach(supplement => {
        allSupplements.push({
          name: supplement,
          description: null, // No description available in the JSON
          is_popular: false, // Default value
          last_research_check: new Date().toISOString(),
          sentiment_score: null, // No sentiment score available in the JSON
        });
      });
    }
    
    // Track progress
    let insertedCount = 0;
    let errorCount = 0;
    
    console.log(`Found ${allSupplements.length} supplements to import...`);
    
    // Process supplements in batches to avoid rate limits
    const BATCH_SIZE = 100;
    for (let i = 0; i < allSupplements.length; i += BATCH_SIZE) {
      const batch = allSupplements.slice(i, i + BATCH_SIZE);
      
      // Insert the batch with upsert to handle duplicates
      const { data: insertedData, error } = await supabase
        .from('supplements')
        .upsert(batch, { 
          onConflict: 'name',
          ignoreDuplicates: false
        });
      
      if (error) {
        console.error(`Error inserting batch ${i/BATCH_SIZE + 1}:`, error);
        errorCount += batch.length;
      } else {
        console.log(`Successfully processed batch ${i/BATCH_SIZE + 1} (${i} - ${Math.min(i + BATCH_SIZE, allSupplements.length)})`);
        insertedCount += batch.length;
      }
      
      // Add a small delay to avoid overwhelming the database
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    console.log('\nImport summary:');
    console.log(`- Total supplements found: ${allSupplements.length}`);
    console.log(`- Successfully processed: ${insertedCount}`);
    console.log(`- Errors: ${errorCount}`);
    
  } catch (error) {
    if (error.code === 'ENOENT') {
      console.error(`Error: File "${filePath}" not found.`);
    } else {
      console.error('Error processing supplements:', error);
    }
    process.exit(1);
  }
}

// Main execution
(async () => {
  // Default path points to the correct location of supplements.json based on project structure
  const defaultPath = path.resolve(__dirname, '../src/data/supplements.json');
  const filePath = process.argv[2] || defaultPath;
  
  console.log('Starting Supplements Import...');
  console.log(`Using file: ${filePath}`);
  
  try {
    await importSupplements(filePath);
    console.log('Import process completed!');
  } catch (error) {
    console.error('Failed to import supplements:', error);
    process.exit(1);
  }
})();