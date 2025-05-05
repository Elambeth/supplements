import os
import sys
import json
import time
import dotenv
from datetime import datetime
from dateutil import parser as date_parser
from supabase import create_client, Client

# Load environment variables from .env file
dotenv.load_dotenv()

# Supabase configuration
supabase_url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_url or not supabase_key:
    print("Error: Supabase environment variables not found.")
    exit(1)

print(f"Connecting to Supabase at: {supabase_url}")
supabase: Client = create_client(supabase_url, supabase_key)

def check_if_table_exists(table_name):
    """Check if a table exists in the database"""
    try:
        # This will fail if the table doesn't exist
        response = supabase.table(table_name).select('id').limit(1).execute()
        return True
    except Exception as e:
        if "relation" in str(e) and "does not exist" in str(e):
            return False
        else:
            # If it's a different error, raise it
            raise e

def get_all_supplement_research(batch_size=100):
    """Get all supplement research records with raw_data"""
    offset = 0
    all_records = []
    
    while True:
        try:
            # Simpler query without filters that cause errors
            response = supabase.table('supplement_research') \
                .select('id, supplement_id, raw_data') \
                .range(offset, offset + batch_size - 1) \
                .execute()
            
            records = response.data
            # Filter records with raw_data in Python
            filtered_records = [r for r in records if r.get('raw_data') is not None]
            all_records.extend(filtered_records)
            
            print(f"Fetched {len(all_records)} valid records so far...")
            
            if len(records) < batch_size:
                break
                
            offset += batch_size
            
        except Exception as e:
            print(f"Error fetching records at offset {offset}: {e}")
            break
    
    return all_records

def parse_date(date_str):
    """Parse dates in various formats and return a valid datetime object"""
    if not date_str:
        return None
    
    try:
        # Handle specific formats we've seen in the data
        # Example: "2025-May-02" or "2025-Apr"
        if '-' in date_str and any(month in date_str for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
            # Try to standardize format first
            parts = date_str.split('-')
            if len(parts) == 2:  # Year-Month format
                year, month = parts
                # Set day to 1 for just Year-Month format
                date_str = f"{year}-{month}-01"
            
        # Using dateutil's parser for flexible date parsing
        return date_parser.parse(date_str)
    except Exception as e:
        print(f"Error parsing date '{date_str}': {e}")
        # Try a more aggressive approach with fuzzy matching
        try:
            return date_parser.parse(date_str, fuzzy=True)
        except Exception:
            return None

def extract_and_normalize_studies(research_records):
    """Extract and normalize studies from raw data"""
    all_studies = []
    supplements_processed = set()
    studies_by_pmid = {}  # To track duplicates
    
    for record in research_records:
        supplement_id = record['supplement_id']
        supplements_processed.add(supplement_id)
        
        try:
            raw_data = record['raw_data']
            
            # Skip if raw_data doesn't have articles
            if not raw_data or 'articles' not in raw_data:
                continue
                
            articles = raw_data['articles']
            
            # Process each article
            for article in articles:
                # Skip if we've already processed this PMID for this supplement
                pmid = article.get('pmid')
                if not pmid:
                    continue
                    
                key = f"{supplement_id}_{pmid}"
                if key in studies_by_pmid:
                    continue
                    
                studies_by_pmid[key] = True
                
                # Extract authors - handle both string array and object array formats
                authors = []
                if 'authors' in article:
                    # Check if authors is already a string array
                    if isinstance(article['authors'], list) and all(isinstance(author, str) for author in article['authors']):
                        authors = article['authors']
                    # Handle object array with name property
                    elif isinstance(article['authors'], list) and all(isinstance(author, dict) for author in article['authors']):
                        authors = [author.get('name', '') for author in article['authors'] if 'name' in author]
                
                # Extract publication types
                pub_types = []
                if 'publication_types' in article and isinstance(article['publication_types'], list):
                    pub_types = [pub_type for pub_type in article['publication_types'] if pub_type]
                
                # Extract MeSH terms if available
                mesh_terms = []
                if 'mesh_terms' in article and isinstance(article['mesh_terms'], list):
                    mesh_terms = [term for term in article['mesh_terms'] if term]
                
                # Parse publication date
                pub_date = None
                if 'publication_date' in article and article['publication_date']:
                    pub_date = parse_date(article['publication_date'])
                
                # Create normalized study object
                study = {
                    'supplement_id': supplement_id,
                    'pmid': pmid,
                    'title': article.get('title', ''),
                    'abstract': article.get('abstract', ''),
                    'authors': authors,
                    'journal': article.get('journal', ''),
                    'publication_date': pub_date,
                    'publication_types': pub_types,
                    'mesh_terms': mesh_terms
                }
                
                all_studies.append(study)
        except Exception as e:
            print(f"Error processing research record {record['id']}: {e}")
    
    return all_studies, supplements_processed

def insert_studies_batch(studies, batch_size=50):
    """Insert studies in batches to avoid timeouts"""
    total_inserted = 0
    total_batches = (len(studies) + batch_size - 1) // batch_size
    
    for i in range(0, len(studies), batch_size):
        batch = studies[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"Inserting batch {batch_num}/{total_batches} ({len(batch)} studies)...")
        
        # Convert datetime objects to strings
        serializable_batch = []
        for study in batch:
            serializable_study = study.copy()
            # Convert publication_date to ISO format string if it's a datetime
            if isinstance(serializable_study.get('publication_date'), datetime):
                serializable_study['publication_date'] = serializable_study['publication_date'].isoformat()
            serializable_batch.append(serializable_study)
        
        try:
            response = supabase.table('supplement_studies').insert(serializable_batch).execute()
            
            if hasattr(response, 'error') and response.error:
                print(f"Error inserting batch: {response.error}")
            else:
                total_inserted += len(batch)
                print(f"Successfully inserted {len(batch)} studies.")
        except Exception as e:
            print(f"Exception inserting batch: {e}")
        
        # Add delay to avoid overwhelming the database
        if i + batch_size < len(studies):
            time.sleep(0.5)
    
    return total_inserted

def print_summary(studies, supplements_processed):
    """Print summary statistics about processed data"""
    if not studies:
        print("\nNo studies were found to process.")
        return
    
    # Count studies per supplement
    studies_per_supplement = {}
    for study in studies:
        supplement_id = study['supplement_id']
        if supplement_id in studies_per_supplement:
            studies_per_supplement[supplement_id] += 1
        else:
            studies_per_supplement[supplement_id] = 1
    
    # Find earliest and latest publication dates
    dates = [study['publication_date'] for study in studies if study['publication_date']]
    earliest_date = min(dates) if dates else None
    latest_date = max(dates) if dates else None
    
    # Count studies with abstracts
    with_abstract = sum(1 for study in studies if study.get('abstract'))
    
    # Count unique journals
    journals = set(study.get('journal', '') for study in studies if study.get('journal'))
    
    # Count MeSH terms and publication types
    mesh_term_counts = {}
    pub_type_counts = {}
    
    for study in studies:
        # Count MeSH terms
        if study.get('mesh_terms'):
            for term in study['mesh_terms']:
                if term in mesh_term_counts:
                    mesh_term_counts[term] += 1
                else:
                    mesh_term_counts[term] = 1
        
        # Count publication types
        if study.get('publication_types'):
            for pub_type in study['publication_types']:
                if pub_type in pub_type_counts:
                    pub_type_counts[pub_type] += 1
                else:
                    pub_type_counts[pub_type] = 1
    
    print("\n" + "=" * 50)
    print("SUMMARY STATISTICS")
    print("=" * 50)
    print(f"Total supplements processed: {len(supplements_processed)}")
    print(f"Total studies extracted: {len(studies)}")
    print(f"Studies with abstracts: {with_abstract} ({with_abstract/len(studies)*100:.1f}%)")
    print(f"Unique journals: {len(journals)}")
    
    if earliest_date and latest_date:
        print(f"Publication date range: {earliest_date.strftime('%Y-%m-%d')} to {latest_date.strftime('%Y-%m-%d')}")
    
    # Print top publication types
    if pub_type_counts:
        print("\nTop 5 publication types:")
        top_pub_types = sorted(pub_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (pub_type, count) in enumerate(top_pub_types, 1):
            print(f"{i}. {pub_type}: {count} studies ({count/len(studies)*100:.1f}%)")
    
    # Print top MeSH terms (if available)
    if mesh_term_counts:
        print("\nTop 10 MeSH terms:")
        top_mesh_terms = sorted(mesh_term_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for i, (term, count) in enumerate(top_mesh_terms, 1):
            print(f"{i}. {term}: {count} studies ({count/len(studies)*100:.1f}%)")
    
    print("\nTop 10 supplements by study count:")
    top_supplements = sorted(studies_per_supplement.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Get supplement names for top supplements
    if top_supplements:
        supplement_ids = [id for id, _ in top_supplements]
        try:
            supplements_response = supabase.table('supplements') \
                .select('id, name') \
                .in_('id', supplement_ids) \
                .execute()
            
            if not hasattr(supplements_response, 'error') or not supplements_response.error:
                supplement_names = {s['id']: s['name'] for s in supplements_response.data}
                
                for i, (supp_id, count) in enumerate(top_supplements, 1):
                    name = supplement_names.get(supp_id, f"Supplement ID {supp_id}")
                    print(f"{i}. {name}: {count} studies ({count/len(studies)*100:.1f}%)")
        except Exception as e:
            print(f"Error retrieving supplement names: {e}")
            for i, (supp_id, count) in enumerate(top_supplements, 1):
                print(f"{i}. Supplement ID {supp_id}: {count} studies ({count/len(studies)*100:.1f}%)")
    
    print("=" * 50)

def main():
    """Main function to run the script"""
    print("Starting supplement studies normalization script...")
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Extract and normalize supplement studies data.')
    parser.add_argument('--dry-run', action='store_true', help='Run without inserting data (for testing)')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for fetching records')
    parser.add_argument('--insert-batch-size', type=int, default=50, help='Batch size for inserting studies')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--limit', type=int, help='Limit number of research records to process')
    args = parser.parse_args()
    
    # Verify that the table exists instead of creating it
    if not check_if_table_exists('supplement_studies'):
        print("Error: 'supplement_studies' table does not exist. Please create it first using SQL.")
        print("Run the SQL script in the Supabase SQL Editor to create the table.")
        return
    
    # Get all supplement research records
    print(f"Fetching supplement research records (batch size: {args.batch_size})...")
    research_records = get_all_supplement_research(batch_size=args.batch_size)
    
    # Apply limit if specified
    if args.limit and args.limit > 0 and args.limit < len(research_records):
        print(f"Limiting to {args.limit} records as specified")
        research_records = research_records[:args.limit]
    
    print(f"Found {len(research_records)} research records to process.")
    
    if not research_records:
        print("No records to process. Exiting.")
        return
    
    # Extract and normalize studies
    print("Extracting and normalizing studies...")
    studies, supplements_processed = extract_and_normalize_studies(research_records)
    print(f"Extracted {len(studies)} unique studies across {len(supplements_processed)} supplements.")
    
    if not studies:
        print("No studies to insert. Exiting.")
        return
    
    # Print summary statistics before insertion
    print("\nPre-insertion summary:")
    print_summary(studies, supplements_processed)
    
    if args.dry_run:
        print("\nDRY RUN - No data will be inserted into the database.")
        return
    
    # First check if we have any existing studies
    try:
        existing_count_response = supabase.table('supplement_studies').select('id', count='exact').execute()
        existing_count = existing_count_response.count if hasattr(existing_count_response, 'count') else 0
        
        if existing_count > 0:
            print(f"Found {existing_count} existing studies in the table.")
            if not args.force:
                proceed = input("Do you want to proceed with insertion? This may create duplicates. (y/n): ")
                if proceed.lower() != 'y':
                    print("Exiting without inserting studies.")
                    return
    except Exception as e:
        print(f"Error checking existing studies: {e}")
        if not args.force:
            proceed = input("Unable to check for existing data. Proceed anyway? (y/n): ")
            if proceed.lower() != 'y':
                print("Exiting without inserting studies.")
                return
    
    # Insert studies in batches
    print(f"Inserting studies into the database (batch size: {args.insert_batch_size})...")
    total_inserted = insert_studies_batch(studies, batch_size=args.insert_batch_size)
    print(f"\nInsertion complete. Successfully inserted {total_inserted} out of {len(studies)} studies.")
    
    # Verify insertion
    try:
        verification_response = supabase.table('supplement_studies').select('id', count='exact').execute()
        final_count = verification_response.count if hasattr(verification_response, 'count') else 0
        print(f"Final count in supplement_studies table: {final_count}")
    except Exception as e:
        print(f"Error verifying final count: {e}")


if __name__ == "__main__":
    main()