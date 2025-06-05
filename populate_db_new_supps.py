#!/usr/bin/env python3
"""
Supabase PubMed Data Consolidator - Clean Version

Downloads research data from S3 and adds it to existing supplement_studies table
with duplicate prevention.
"""

import boto3
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Set
import logging
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client
import re

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CleanSupabaseConsolidator:
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.environ['S3_BUCKET']
        
        # Initialize Supabase
        supabase_url = os.environ['NEXT_PUBLIC_SUPABASE_URL']
        supabase_key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # Cache for supplement name -> ID mapping
        self.supplement_cache = {}
        self.existing_papers: Set[str] = set()
        
    def load_supplement_cache(self):
        """Load all supplements and create name -> ID mapping."""
        logger.info("Loading supplement cache...")
        
        response = self.supabase.table('supplements').select('id, name').execute()
        
        for supplement in response.data:
            # Normalize supplement names for matching
            normalized_name = self.normalize_supplement_name(supplement['name'])
            self.supplement_cache[normalized_name] = supplement['id']
        
        logger.info(f"Loaded {len(self.supplement_cache)} supplements into cache")
    
    def normalize_supplement_name(self, name: str) -> str:
        """Normalize supplement names for consistent matching."""
        if not name:
            return ""
        
        # Convert to lowercase, remove extra spaces, special chars
        normalized = re.sub(r'[^\w\s-]', '', name.lower().strip())
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Common variations mapping
        variations = {
            'vitamin c': 'ascorbic acid',
            'vitamin e': 'tocopherol',
            'vitamin d': 'cholecalciferol',
            'vitamin b12': 'cobalamin',
            'omega 3': 'omega-3',
            'fish oil': 'omega-3',
            'coq10': 'coenzyme q10',
        }
        
        return variations.get(normalized, normalized)
    
    def find_supplement_id(self, supplement_name: str) -> int:
        """Find supplement ID by name with fuzzy matching."""
        normalized = self.normalize_supplement_name(supplement_name)
        
        # Direct match
        if normalized in self.supplement_cache:
            return self.supplement_cache[normalized]
        
        # Fuzzy matching - check if normalized name contains any cached supplement
        for cached_name, supplement_id in self.supplement_cache.items():
            if cached_name in normalized or normalized in cached_name:
                logger.info(f"Fuzzy matched '{supplement_name}' -> '{cached_name}'")
                return supplement_id
        
        logger.warning(f"No match found for supplement: {supplement_name}")
        return None
    
    def load_existing_papers(self):
        """Load existing PubMed IDs from supplement_studies table."""
        logger.info("Loading existing papers from supplement_studies...")
        
        response = self.supabase.table('supplement_studies').select('pmid').execute()
        
        self.existing_papers = {study['pmid'] for study in response.data if study['pmid']}
        logger.info(f"Found {len(self.existing_papers)} existing papers in database")
    
    def list_s3_results(self) -> List[str]:
        """List all supplement result files in S3."""
        logger.info(f"Scanning S3 bucket: {self.bucket_name}")
        
        paginator = self.s3_client.get_paginator('list_objects_v2')
        job_files = []
        
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix='jobs/'):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.endswith('.json') and '/supplements/' in key:
                        job_files.append(key)
        
        logger.info(f"Found {len(job_files)} supplement result files")
        return job_files
    
    def download_s3_file(self, s3_key: str) -> Dict[str, Any]:
        """Download and parse a single JSON file from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            content = response['Body'].read().decode('utf-8')
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error downloading {s3_key}: {e}")
            return None
    
    def process_paper(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Process and clean a single paper's data for supplement_studies table."""
        # Extract PubMed ID (handle both pmid and pubmed_id)
        pubmed_id = article.get('pmid') or article.get('pubmed_id')
        if not pubmed_id:
            return None
        
        # Clean and process fields - handle None values
        title = (article.get('title') or '').strip() or 'No title available'
        abstract = (article.get('abstract') or '').strip() or 'No abstract available'
        
        # Handle authors - ensure it's a proper array
        authors = article.get('authors', [])
        if not isinstance(authors, list):
            authors = []
        
        # Handle MeSH terms - ensure it's a proper array
        mesh_terms = article.get('mesh_terms', [])
        if not isinstance(mesh_terms, list):
            mesh_terms = []
        
        # Handle publication types - ensure it's a proper array
        pub_types = article.get('publication_types', [])
        if not isinstance(pub_types, list):
            pub_types = []
        
        # Parse publication date to timestamp
        pub_date = article.get('publication_date') or ''
        publication_date = None
        if pub_date:
            try:
                # Try to parse various date formats
                if re.match(r'\d{4}-\w+', pub_date):  # "2025-Jun"
                    year_month = pub_date.replace('-', ' ')
                    publication_date = datetime.strptime(year_month, '%Y %b').isoformat()
                elif re.match(r'\d{4}', pub_date):  # Just year
                    publication_date = f"{pub_date}-01-01T00:00:00"
                else:
                    # Try as-is
                    publication_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00')).isoformat()
            except Exception as e:
                # If parsing fails, store as None
                logger.debug(f"Date parsing failed for '{pub_date}': {e}")
                publication_date = None
        
        return {
            'pmid': str(pubmed_id),
            'title': title,
            'abstract': abstract,
            'authors': authors,
            'journal': (article.get('journal') or '').strip() or 'Unknown journal',
            'publication_date': publication_date,
            'publication_types': pub_types,
            'mesh_terms': mesh_terms
        }
    
    def batch_insert_studies(self, studies: List[Dict[str, Any]]) -> int:
        """Insert studies in batches, skipping duplicates."""
        if not studies:
            return 0
        
        # Filter out existing papers
        new_studies = [s for s in studies if s['pmid'] not in self.existing_papers]
        
        if not new_studies:
            logger.info("No new studies to insert")
            return 0
        
        try:
            # Insert in batches of 50 (smaller batches for stability)
            batch_size = 50
            inserted = 0
            
            for i in range(0, len(new_studies), batch_size):
                batch = new_studies[i:i + batch_size]
                
                response = self.supabase.table('supplement_studies').insert(batch).execute()
                
                if response.data:
                    inserted += len(response.data)
                    # Add to existing papers cache
                    for study in batch:
                        self.existing_papers.add(study['pmid'])
                
                logger.info(f"Inserted batch {i//batch_size + 1}: {len(batch)} studies")
            
            logger.info(f"Successfully inserted {inserted} new studies")
            return inserted
            
        except Exception as e:
            logger.error(f"Error inserting studies: {e}")
            if new_studies:
                logger.error(f"Sample record: {new_studies[0]}")
            return 0
    
    def consolidate_all_data(self):
        """Main consolidation process."""
        logger.info("Starting data consolidation...")
        
        # Setup
        self.load_supplement_cache()
        self.load_existing_papers()
        
        # Get all S3 files
        s3_files = self.list_s3_results()
        
        studies_to_insert = []
        stats = {
            'files_processed': 0,
            'total_articles_found': 0,
            'new_studies': 0,
            'skipped_no_supplement': 0,
            'skipped_no_pubmed_id': 0
        }
        
        # Process each file
        for i, s3_key in enumerate(s3_files, 1):
            logger.info(f"Processing file {i}/{len(s3_files)}: {s3_key}")
            
            data = self.download_s3_file(s3_key)
            if not data:
                continue
            
            supplement_name = data.get('supplement', '')
            supplement_id = self.find_supplement_id(supplement_name)
            
            if not supplement_id:
                logger.warning(f"Skipping file - no supplement match: {supplement_name}")
                stats['skipped_no_supplement'] += 1
                continue

            # START MODIFICATION
            s3_key_parts = s3_key.split('/') 
            # Example s3_key: 'jobs/supplementation_batch_1_20240603_120000/supplements/Vitamin_D.json'
            # s3_key_parts will be ['jobs', 'supplementation_batch_1_20240603_120000', 'supplements', 'Vitamin_D.json']
            
            collection_job_id = None
            if len(s3_key_parts) > 1:
                collection_job_id = s3_key_parts[1] # This is the job_id

            collection_type = 'unknown' # Default collection type
            if collection_job_id:
                if collection_job_id.startswith('supplementation_'):
                    collection_type = 'supplementation'
                elif collection_job_id.startswith('supabase_batch_'): # Adjust if your old intervention batches had a different prefix
                    collection_type = 'intervention'
                # Add other conditions if you have more specific job_id patterns for other types
            # END MODIFICATION
            
            articles = data.get('articles', [])
            stats['total_articles_found'] += len(articles)
            
            # Process each article
            for article in articles:
                processed_study = self.process_paper(article)
                if not processed_study:
                    stats['skipped_no_pubmed_id'] += 1
                    continue
                
                pmid = processed_study['pmid']
                
                # Add supplement_id to the study
                processed_study['supplement_id'] = supplement_id
                # START MODIFICATION - Add new fields
                processed_study['collection_type'] = collection_type
                processed_study['collection_job_id'] = collection_job_id
                # END MODIFICATION
                
                # Add to studies list if new
                if pmid not in self.existing_papers:
                    studies_to_insert.append(processed_study)
            
            stats['files_processed'] += 1
            
            # Insert in batches every 20 files to avoid memory issues
            # Consider adjusting this threshold based on typical file sizes and memory constraints
            if len(studies_to_insert) >= 1000: # Increased batch size for potential efficiency, monitor memory
                logger.info(f"Preparing to insert batch of {len(studies_to_insert)} studies...")
                stats['new_studies'] += self.batch_insert_studies(studies_to_insert)
                studies_to_insert = []
        
        # Insert remaining studies
        if studies_to_insert:
            logger.info(f"Preparing to insert final batch of {len(studies_to_insert)} studies...")
            stats['new_studies'] += self.batch_insert_studies(studies_to_insert)
        
        return stats

def main():
    """Main execution function."""
    print("🔄 Clean Supabase PubMed Data Consolidator")
    print("=" * 50)
    
    consolidator = CleanSupabaseConsolidator()
    
    try:
        # Test database connection
        print("\n🗄️  Testing database connection...")
        test_response = consolidator.supabase.table('supplement_studies').select('*').limit(1).execute()
        print("✅ Database connection successful")
        
        # Consolidate data
        print("\n📥 Consolidating S3 data into Supabase...")
        stats = consolidator.consolidate_all_data()
        
        # Print summary
        print("\n✅ Data consolidation complete!")
        print(f"📁 Files processed: {stats['files_processed']}")
        print(f"📄 Total articles found: {stats['total_articles_found']:,}")
        print(f"🆕 New studies added: {stats['new_studies']:,}")
        print(f"⚠️  Skipped (no supplement match): {stats['skipped_no_supplement']}")
        print(f"⚠️  Skipped (no PubMed ID): {stats['skipped_no_pubmed_id']}")
        
        print(f"\n🎉 Your Supabase database now contains comprehensive research data!")
        print(f"   Use the 'supplement_studies' table for analysis")
        
    except Exception as e:
        logger.error(f"Error during consolidation: {e}")
        raise

if __name__ == "__main__":
    main()