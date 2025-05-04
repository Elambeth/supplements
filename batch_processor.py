#!/usr/bin/env python3
"""
Batch processor for running the PubMed collector on multiple supplements
and uploading results to Supabase.
"""

import os
import json
import subprocess
import time
import dotenv
from supabase import create_client, Client

# Load environment variables from .env file
dotenv.load_dotenv()

# Supabase configuration - use the same variable names as in your .env file
supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# Check if environment variables are loaded
if not supabase_url or not supabase_key:
    print("Error: Supabase environment variables not found.")
    print(f"NEXT_PUBLIC_SUPABASE_URL: {'Found' if supabase_url else 'Missing'}")
    print(f"SUPABASE_SERVICE_ROLE_KEY: {'Found' if supabase_key else 'Missing'}")
    exit(1)

print(f"Connecting to Supabase at: {supabase_url}")
supabase: Client = create_client(supabase_url, supabase_key)

# Get list of supplements from Supabase
def get_supplements():
    response = supabase.table('supplements').select('id, name').execute()
    if hasattr(response, 'error') and response.error:
        print(f"Error fetching supplements: {response.error}")
        return []
    return response.data

# Upload results to Supabase
def upload_to_supabase(supplement_id, data):
    # Check if entry already exists
    response = supabase.table('supplement_research').select('id').eq('supplement_id', supplement_id).execute()
    
    if response.data and len(response.data) > 0:
        # Update existing entry
        research_id = response.data[0]['id']
        response = supabase.table('supplement_research').update({
            'research_count': data['research_count'],
            'retrieved_count': data['count'],
            'query': data['query'],
            'search_date': data['search_date'],
            'raw_data': data,
            'last_updated': 'now()'
        }).eq('id', research_id).execute()
    else:
        # Insert new entry
        response = supabase.table('supplement_research').insert({
            'supplement_id': supplement_id,
            'research_count': data['research_count'],
            'retrieved_count': data['count'],
            'query': data['query'],
            'search_date': data['search_date'],
            'raw_data': data
        }).execute()
    
    # Update supplement's last_research_check
    supabase.table('supplements').update({
        'last_research_check': 'now()'
    }).eq('id', supplement_id).execute()
    
    print(f"Updated research data for supplement ID {supplement_id}")

# Main processing function
def process_supplements(limit=None, skip_processed=True):
    supplements = get_supplements()
    
    if limit:
        supplements = supplements[:limit]
    
    print(f"Processing {len(supplements)} supplements")
    
    for supplement in supplements:
        supplement_id = supplement['id']
        supplement_name = supplement['name']
        
        # Skip already processed supplements if requested
        if skip_processed:
            response = supabase.table('supplement_research').select('id').eq('supplement_id', supplement_id).execute()
            if response.data and len(response.data) > 0:
                print(f"Skipping {supplement_name} (already processed)")
                continue
        
        print(f"Processing {supplement_name}...")
        
        # Output file path
        output_file = f"./data/{supplement_name.lower().replace(' ', '_')}.json"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Run the PubMed collector script
        try:
            cmd = [
                "python", "pubmed_data_collector.py",
                "--supplement", supplement_name,
                "--max_results", "100",
                "--output", output_file,
                "--email", "your_email@example.com"  # Replace with your email
            ]
            
            subprocess.run(cmd, check=True)
            
            # Load the results and upload to Supabase
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            upload_to_supabase(supplement_id, data)
            
            # Respect API rate limits
            time.sleep(2)
            
        except Exception as e:
            print(f"Error processing {supplement_name}: {e}")
    
    print("Batch processing complete!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Process supplements in batch')
    parser.add_argument('--limit', type=int, help='Maximum number of supplements to process')
    parser.add_argument('--process-all', action='store_true', help='Process all supplements, including already processed ones')
    
    args = parser.parse_args()
    
    process_supplements(limit=args.limit, skip_processed=not args.process_all)