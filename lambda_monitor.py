#!/usr/bin/env python3
"""
Monitor AWS Lambda PubMed collection progress
"""

import json
import boto3
import os
from datetime import datetime
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LambdaProgressMonitor:
    def __init__(self, s3_bucket: str):
        self.s3_client = boto3.client('s3')
        self.s3_bucket = s3_bucket
        
    def check_job_progress(self, job_ids: list = None) -> dict:
        """
        Check progress of specific jobs or all jobs
        """
        try:
            # If no specific job IDs provided, find all jobs
            if not job_ids:
                job_ids = self.find_all_job_ids()
            
            progress_report = {
                'total_jobs': len(job_ids),
                'completed_jobs': 0,
                'in_progress_jobs': 0,
                'failed_jobs': 0,
                'job_details': {},
                'overall_stats': {
                    'total_supplements': 0,
                    'completed_supplements': 0,
                    'total_papers': 0
                }
            }
            
            for job_id in job_ids:
                job_status = self.check_single_job(job_id)
                progress_report['job_details'][job_id] = job_status
                
                # Update overall stats
                if job_status['status'] == 'completed':
                    progress_report['completed_jobs'] += 1
                elif job_status['status'] == 'in_progress':
                    progress_report['in_progress_jobs'] += 1
                else:
                    progress_report['failed_jobs'] += 1
                
                progress_report['overall_stats']['total_supplements'] += job_status['total_supplements']
                progress_report['overall_stats']['completed_supplements'] += job_status['completed_supplements']
                progress_report['overall_stats']['total_papers'] += job_status['total_papers']
            
            return progress_report
            
        except Exception as e:
            print(f"Error checking progress: {e}")
            return {}
    
    def find_all_job_ids(self) -> list:
        """
        Find all job IDs in the S3 bucket
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix='jobs/',
                Delimiter='/'
            )
            
            job_ids = []
            if 'CommonPrefixes' in response:
                for prefix_info in response['CommonPrefixes']:
                    job_id = prefix_info['Prefix'].replace('jobs/', '').rstrip('/')
                    if job_id:  # Skip empty job IDs
                        job_ids.append(job_id)
            
            return job_ids
            
        except Exception as e:
            print(f"Error finding job IDs: {e}")
            return []
    
    def check_single_job(self, job_id: str) -> dict:
        """
        Check progress of a single job
        """
        job_status = {
            'job_id': job_id,
            'status': 'not_found',
            'total_supplements': 0,
            'completed_supplements': 0,
            'total_papers': 0,
            'completed_supplement_names': [],
            'error_count': 0
        }
        
        try:
            # Check if job metadata exists
            try:
                metadata_response = self.s3_client.get_object(
                    Bucket=self.s3_bucket,
                    Key=f"jobs/{job_id}/metadata.json"
                )
                metadata = json.loads(metadata_response['Body'].read().decode('utf-8'))
                job_status['total_supplements'] = len(metadata.get('supplements', []))
                job_status['status'] = 'in_progress'
            except:
                # No metadata found, check if any results exist
                pass
            
            # Check completed supplements
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.s3_bucket,
                    Prefix=f"jobs/{job_id}/supplements/"
                )
                
                if 'Contents' in response:
                    completed_supplements = []
                    total_papers = 0
                    
                    for obj in response['Contents']:
                        supplement_name = obj['Key'].split('/')[-1].replace('.json', '').replace('_', ' ')
                        completed_supplements.append(supplement_name)
                        
                        # Get paper count for this supplement
                        try:
                            file_response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=obj['Key'])
                            supplement_data = json.loads(file_response['Body'].read().decode('utf-8'))
                            total_papers += supplement_data.get('retrieved_count', 0)
                        except:
                            pass
                    
                    job_status['completed_supplements'] = len(completed_supplements)
                    job_status['completed_supplement_names'] = completed_supplements
                    job_status['total_papers'] = total_papers
                    
                    if job_status['total_supplements'] > 0:
                        if job_status['completed_supplements'] >= job_status['total_supplements']:
                            job_status['status'] = 'completed'
                        else:
                            job_status['status'] = 'in_progress'
                    else:
                        job_status['status'] = 'completed' if completed_supplements else 'in_progress'
            except:
                pass
            
            return job_status
            
        except Exception as e:
            job_status['status'] = 'error'
            job_status['error'] = str(e)
            return job_status
    
    def print_progress_report(self, progress_report: dict):
        """
        Print a nice progress report
        """
        print(f"\n{'='*60}")
        print(f"📊 LAMBDA PROGRESS REPORT")
        print(f"{'='*60}")
        print(f"⏰ Report time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Overall statistics
        stats = progress_report['overall_stats']
        print(f"📈 Overall Progress:")
        print(f"  Total jobs: {progress_report['total_jobs']}")
        print(f"  Completed jobs: {progress_report['completed_jobs']}")
        print(f"  In progress: {progress_report['in_progress_jobs']}")
        print(f"  Failed/Error: {progress_report['failed_jobs']}")
        print()
        
        print(f"📚 Supplement Progress:")
        if stats['total_supplements'] > 0:
            completion_rate = (stats['completed_supplements'] / stats['total_supplements']) * 100
            print(f"  Supplements: {stats['completed_supplements']}/{stats['total_supplements']} ({completion_rate:.1f}%)")
        else:
            print(f"  Supplements: {stats['completed_supplements']} completed")
        print(f"  Papers collected: {stats['total_papers']:,}")
        print()
        
        # Job details
        if progress_report['job_details']:
            print(f"📋 Job Details:")
            for job_id, details in progress_report['job_details'].items():
                status_emoji = {
                    'completed': '✅',
                    'in_progress': '🔄',
                    'error': '❌',
                    'not_found': '❓'
                }.get(details['status'], '❓')
                
                print(f"  {status_emoji} {job_id}")
                print(f"    Status: {details['status']}")
                if details['total_supplements'] > 0:
                    print(f"    Progress: {details['completed_supplements']}/{details['total_supplements']} supplements")
                else:
                    print(f"    Completed: {details['completed_supplements']} supplements")
                print(f"    Papers: {details['total_papers']:,}")
                
                if details['status'] == 'error':
                    print(f"    Error: {details.get('error', 'Unknown error')}")
                print()
    
    def monitor_continuously(self, job_ids: list = None, interval_seconds: int = 30):
        """
        Monitor progress continuously with updates
        """
        print(f"🔍 Starting continuous monitoring (updating every {interval_seconds} seconds)")
        print("Press Ctrl+C to stop monitoring")
        
        try:
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')  # Clear screen
                
                progress_report = self.check_job_progress(job_ids)
                self.print_progress_report(progress_report)
                
                # Check if all jobs are completed
                if (progress_report['completed_jobs'] == progress_report['total_jobs'] and 
                    progress_report['total_jobs'] > 0):
                    print("🎉 All jobs completed!")
                    break
                
                print(f"⏳ Next update in {interval_seconds} seconds...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\n👋 Monitoring stopped by user")

def main():
    S3_BUCKET = os.getenv('S3_BUCKET')
    
    if not S3_BUCKET:
        print("❌ Error: Please add S3_BUCKET to your .env file")
        print("Example: S3_BUCKET=pubmed-results-your-bucket-name")
        return
    
    monitor = LambdaProgressMonitor(S3_BUCKET)
    
    # Check command line arguments
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'continuous':
            # Continuous monitoring
            monitor.monitor_continuously()
        elif sys.argv[1] == 'job':
            # Monitor specific job
            if len(sys.argv) > 2:
                job_id = sys.argv[2]
                progress = monitor.check_job_progress([job_id])
                monitor.print_progress_report(progress)
            else:
                print("Usage: python monitor.py job <job_id>")
        else:
            print("Usage: python monitor.py [continuous|job <job_id>]")
    else:
        # Single progress check
        progress = monitor.check_job_progress()
        monitor.print_progress_report(progress)

if __name__ == "__main__":
    main()