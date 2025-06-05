#!/usr/bin/env python3
"""
Trigger AWS Lambda PubMed collector for all supplements in Supabase database
"""

import json
import boto3
from supabase import create_client, Client
from typing import List, Dict, Any
import os
import time
from datetime import datetime
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SupplementLambdaTrigger:
    def __init__(self, supabase_url: str, supabase_key: str, lambda_function_name: str):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.lambda_client = boto3.client('lambda')
        self.function_name = lambda_function_name
        
    def get_all_supplements(self) -> List[Dict[str, Any]]:
        """
        Get all supplements from Supabase database
        """
        try:
            response = self.supabase.table('supplements').select('id,name').execute()
            return response.data
        except Exception as e:
            logger.error(f"Error fetching supplements: {e}")
            return []
    
    def create_processing_batches(self, supplements: List[Dict[str, Any]], batch_size: int = 50) -> List[Dict[str, Any]]:
        """
        Create batches for parallel processing
        """
        batches = []
        
        for i in range(0, len(supplements), batch_size):
            batch_supplements = supplements[i:i + batch_size]
            
            batch = {
                'event_type': 'coordinator',
                'supplements': [supp['name'] for supp in batch_supplements],
                'job_id': f"supplementation_batch_{i//batch_size + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",  # Changed prefix
                'search_params': {
                    'start_year': 2010,  # Adjust these years as needed
                    'end_year': 2024
                },
                'batch_info': {
                    'batch_number': i//batch_size + 1,
                    'total_batches': (len(supplements) + batch_size - 1) // batch_size,
                    'supplements_in_batch': len(batch_supplements),
                    'supplement_ids': [supp['id'] for supp in batch_supplements]
                }
            }
            batches.append(batch)
        
        return batches
    
    def trigger_single_batch(self, batch: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger a single batch in AWS Lambda
        """
        try:
            logger.info(f"Triggering batch: {batch['job_id']} with {len(batch['supplements'])} supplements")
            
            response = self.lambda_client.invoke(
                FunctionName=self.function_name,
                InvocationType='Event',  # Async execution
                Payload=json.dumps(batch)
            )
            
            return {
                'job_id': batch['job_id'],
                'status': 'triggered',
                'supplements_count': len(batch['supplements']),
                'lambda_request_id': response.get('ResponseMetadata', {}).get('RequestId'),
                'supplements': batch['supplements']
            }
            
        except Exception as e:
            logger.error(f"Error triggering batch {batch['job_id']}: {e}")
            return {
                'job_id': batch['job_id'],
                'status': 'failed',
                'error': str(e),
                'supplements': batch['supplements']
            }
    
    def trigger_all_batches(self, batches: List[Dict[str, Any]], delay_seconds: int = 2) -> List[Dict[str, Any]]:
        """
        Trigger all batches with a delay between each
        """
        results = []
        
        for i, batch in enumerate(batches):
            result = self.trigger_single_batch(batch)
            results.append(result)
            
            # Progress update
            print(f"✅ Triggered batch {i+1}/{len(batches)}: {result['job_id']}")
            if result['status'] == 'failed':
                print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
            else:
                print(f"   📊 Processing {result['supplements_count']} supplements")
            
            # Delay between batch triggers to avoid overwhelming Lambda
            if i < len(batches) - 1:  # Don't delay after the last batch
                time.sleep(delay_seconds)
        
        return results
    
    def save_trigger_log(self, results: List[Dict[str, Any]], supplements_count: int):
        """
        Save trigger results to a log file for monitoring
        """
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'total_supplements': supplements_count,
            'total_batches': len(results),
            'successful_triggers': len([r for r in results if r['status'] == 'triggered']),
            'failed_triggers': len([r for r in results if r['status'] == 'failed']),
            'batches': results
        }
        
        filename = f"lambda_trigger_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w') as f:
            json.dumps(log_data, f, indent=2)
        
        print(f"\n📝 Trigger log saved to: {filename}")
        return filename
    
    def print_summary(self, results: List[Dict[str, Any]], supplements_count: int):
        """
        Print a summary of the triggering process
        """
        successful = len([r for r in results if r['status'] == 'triggered'])
        failed = len([r for r in results if r['status'] == 'failed'])
        
        print(f"\n{'='*50}")
        print(f"🚀 LAMBDA TRIGGER SUMMARY")
        print(f"{'='*50}")
        print(f"Total supplements: {supplements_count}")
        print(f"Total batches: {len(results)}")
        print(f"Successfully triggered: {successful}")
        print(f"Failed to trigger: {failed}")
        print(f"Success rate: {(successful/len(results)*100):.1f}%")
        
        if failed > 0:
            print(f"\n❌ Failed batches:")
            for result in results:
                if result['status'] == 'failed':
                    print(f"  - {result['job_id']}: {result.get('error', 'Unknown error')}")
        
        print(f"\n⏰ Estimated processing time: 15-30 minutes")
        print(f"💰 Estimated cost: $5-15 total")
        print(f"\n📊 Monitor progress in AWS CloudWatch logs")
        print(f"📁 Results will be saved to your S3 bucket")

def main():
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Configuration - using your .env variable names
    SUPABASE_URL = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')  # Use service role key for admin access
    LAMBDA_FUNCTION_NAME = os.getenv('LAMBDA_FUNCTION_NAME', 'pubmed-collector')
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '25'))  # Supplements per batch
    DELAY_SECONDS = int(os.getenv('DELAY_SECONDS', '3'))  # Delay between batch triggers
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: Please check your .env file has NEXT_PUBLIC_SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return
    
    print(f"🔧 Configuration:")
    print(f"  Lambda function: {LAMBDA_FUNCTION_NAME}")
    print(f"  Batch size: {BATCH_SIZE} supplements per batch")
    print(f"  Delay between batches: {DELAY_SECONDS} seconds")
    print()
    
    # Initialize trigger
    trigger = SupplementLambdaTrigger(SUPABASE_URL, SUPABASE_KEY, LAMBDA_FUNCTION_NAME)
    
    # Step 1: Get all supplements
    print("📥 Fetching supplements from Supabase...")
    supplements = trigger.get_all_supplements()
    
    if not supplements:
        print("❌ No supplements found in database")
        return
    
    print(f"✅ Found {len(supplements)} supplements")
    
    # Step 2: Create batches
    print(f"📦 Creating batches of {BATCH_SIZE} supplements...")
    batches = trigger.create_processing_batches(supplements, BATCH_SIZE)
    print(f"✅ Created {len(batches)} batches")
    
    # Step 3: Confirm before triggering
    print(f"\n⚠️  About to trigger {len(batches)} Lambda functions")
    print(f"   This will process {len(supplements)} supplements")
    print(f"   Estimated cost: $5-15")
    
    confirm = input("\nProceed? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled")
        return
    
    # Step 4: Trigger all batches
    print(f"\n🚀 Triggering Lambda functions...")
    results = trigger.trigger_all_batches(batches, DELAY_SECONDS)
    
    # Step 5: Save results and show summary
    trigger.save_trigger_log(results, len(supplements))
    trigger.print_summary(results, len(supplements))

if __name__ == "__main__":
    main()