#!/usr/bin/env python3
"""
AWS Lambda PubMed Data Collection Pipeline

This Lambda function collects supplement research papers from PubMed API
with parallel processing capabilities and unlimited result collection.

Environment Variables Required:
- S3_BUCKET: S3 bucket name for storing results
- SQS_QUEUE_URL: SQS queue URL for coordination
- NCBI_EMAIL: Email for PubMed API identification
- NCBI_API_KEY: Optional NCBI API key for higher rate limits
"""

import json
import os
import time
import boto3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import requests
from urllib.parse import quote
import uuid

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
lambda_client = boto3.client('lambda')

# Constants
BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
RATE_LIMIT_DELAY = 0.34  # 3 requests per second
MAX_RETMAX = 100  # PubMed API batch size limit
LAMBDA_TIMEOUT_BUFFER = 30  # Reserve 30 seconds before Lambda timeout
MAX_EXECUTION_TIME = 15 * 60 - LAMBDA_TIMEOUT_BUFFER  # 14.5 minutes

# High-quality study type filters
HIGH_QUALITY_PUBLICATION_TYPES = [
    "Randomized Controlled Trial",
    "Systematic Review", 
    "Meta-Analysis",
    "Network Meta-Analysis",
    "Clinical Trial, Phase II",
    "Clinical Trial, Phase III", 
    "Controlled Clinical Trial",
    "Pragmatic Clinical Trial",
    "Adaptive Clinical Trial",
    "Observational Study",
    "Clinical Study",
    "Comparative Study",
    "Multicenter Study",
    "Review",
    "Scoping Review",
    "Practice Guideline",
    "Guideline"
]

class LambdaPubMedCollector:
    """
    AWS Lambda-optimized PubMed data collector with parallel processing capabilities.
    """
    
    def __init__(self):
        self.email = os.environ.get('NCBI_EMAIL', 'researcher@example.com')
        self.api_key = os.environ.get('NCBI_API_KEY')
        self.s3_bucket = os.environ['S3_BUCKET']
        self.sqs_queue_url = os.environ.get('SQS_QUEUE_URL')
        self.start_time = time.time()
        
    def lambda_handler(self, event: Dict[str, Any], context) -> Dict[str, Any]:
        """
        Main Lambda handler function.
        
        Event types supported:
        1. coordinator: Initiates parallel processing for multiple supplements
        2. worker: Processes a single supplement or batch of PMIDs
        3. batch_processor: Processes a specific batch of PMIDs for detailed extraction
        """
        try:
            event_type = event.get('event_type', 'worker')
            
            if event_type == 'coordinator':
                return self._handle_coordinator(event)
            elif event_type == 'worker':
                return self._handle_worker(event)
            elif event_type == 'batch_processor':
                return self._handle_batch_processor(event)
            else:
                raise ValueError(f"Unknown event type: {event_type}")
                
        except Exception as e:
            logger.error(f"Lambda execution failed: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': str(e)})
            }
    
    def _handle_coordinator(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinator function that initiates parallel processing for multiple supplements.
        """
        supplements = event.get('supplements', [])
        search_params = event.get('search_params', {})
        job_id = event.get('job_id', str(uuid.uuid4()))
        
        logger.info(f"Starting coordinator for job {job_id} with {len(supplements)} supplements")
        
        # Create worker tasks for each supplement
        worker_tasks = []
        for supplement in supplements:
            worker_event = {
                'event_type': 'worker',
                'supplement': supplement,
                'job_id': job_id,
                'search_params': search_params
            }
            worker_tasks.append(worker_event)
        
        # Send tasks to SQS for parallel processing
        if self.sqs_queue_url:
            self._send_tasks_to_sqs(worker_tasks)
        else:
            # Direct Lambda invocation for smaller workloads
            self._invoke_workers_directly(worker_tasks)
        
        # Save job metadata
        job_metadata = {
            'job_id': job_id,
            'supplements': supplements,
            'search_params': search_params,
            'start_time': datetime.utcnow().isoformat(),
            'status': 'initiated',
            'worker_count': len(supplements)
        }
        
        self._save_to_s3(f"jobs/{job_id}/metadata.json", job_metadata)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'job_id': job_id,
                'workers_initiated': len(worker_tasks),
                'message': 'Parallel processing initiated'
            })
        }
    
    def _handle_worker(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Worker function that processes a single supplement.
        """
        supplement = event['supplement']
        job_id = event.get('job_id', str(uuid.uuid4()))
        search_params = event.get('search_params', {})
        
        logger.info(f"Processing supplement: {supplement} for job: {job_id}")
        
        # Search for PMIDs
        total_count, pmids = self._search_and_get_all_pmids(supplement, search_params)
        
        if not pmids:
            result = {
                'supplement': supplement,
                'job_id': job_id,
                'total_count': total_count,
                'retrieved_count': 0,
                'articles': [],
                'status': 'completed'
            }
        else:
            # Process PMIDs in batches
            result = self._process_pmids_in_batches(supplement, job_id, pmids, total_count)
        
        # Save result to S3
        output_key = f"jobs/{job_id}/supplements/{supplement.replace(' ', '_')}.json"
        self._save_to_s3(output_key, result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'supplement': supplement,
                'job_id': job_id,
                'total_count': total_count,
                'processed_count': result.get('retrieved_count', 0),
                's3_key': output_key
            })
        }
    
    def _handle_batch_processor(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Batch processor function that handles detailed extraction for a batch of PMIDs.
        """
        supplement = event['supplement']
        job_id = event['job_id']
        pmids = event['pmids']
        batch_id = event['batch_id']
        
        logger.info(f"Processing batch {batch_id} with {len(pmids)} PMIDs for {supplement}")
        
        # Extract detailed article information
        articles = self._fetch_article_details_optimized(pmids)
        
        # Save batch result
        batch_result = {
            'supplement': supplement,
            'job_id': job_id,
            'batch_id': batch_id,
            'pmids': pmids,
            'articles': articles,
            'processed_count': len(articles),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        batch_key = f"jobs/{job_id}/batches/{supplement.replace(' ', '_')}_batch_{batch_id}.json"
        self._save_to_s3(batch_key, batch_result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'batch_id': batch_id,
                'processed_count': len(articles),
                's3_key': batch_key
            })
        }
    
    def _search_and_get_all_pmids(self, supplement: str, search_params: Dict[str, Any]) -> Tuple[int, List[str]]:
        """
        Search PubMed and retrieve ALL PMIDs matching the criteria (no limits).
        """
        # Build comprehensive search query
        query = self._build_search_query(supplement, search_params)
        
        logger.info(f"Searching for all results matching: {query}")
        
        # Get initial search results with WebEnv
        search_url = f"{BASE_URL}esearch.fcgi"
        search_params_api = {
            "db": "pubmed",
            "term": query,
            "usehistory": "y",
            "retmode": "json",
            "retmax": 0,  # Just get count initially
            "tool": "LambdaSupplementCollector",
            "email": self.email
        }
        
        if self.api_key:
            search_params_api["api_key"] = self.api_key
        
        try:
            response = requests.get(search_url, params=search_params_api)
            response.raise_for_status()
            search_result = response.json()
            
            total_count = int(search_result["esearchresult"]["count"])
            webenv = search_result["esearchresult"]["webenv"]
            query_key = search_result["esearchresult"]["querykey"]
            
            logger.info(f"Total results found: {total_count}")
            
            if total_count == 0:
                return 0, []
            
            # Fetch ALL PMIDs in batches
            pmids = []
            batch_size = MAX_RETMAX
            
            for start in range(0, total_count, batch_size):
                # Check if we're approaching Lambda timeout
                if time.time() - self.start_time > MAX_EXECUTION_TIME:
                    logger.warning("Approaching Lambda timeout, stopping PMID collection")
                    break
                
                retmax = min(batch_size, total_count - start)
                
                fetch_params = {
                    "db": "pubmed",
                    "query_key": query_key,
                    "WebEnv": webenv,
                    "retstart": start,
                    "retmax": retmax,
                    "retmode": "json",
                    "tool": "LambdaSupplementCollector",
                    "email": self.email
                }
                
                if self.api_key:
                    fetch_params["api_key"] = self.api_key
                
                logger.info(f"Fetching PMIDs {start} to {start + retmax}")
                batch_response = requests.get(search_url, params=fetch_params)
                batch_response.raise_for_status()
                
                batch_result = batch_response.json()
                batch_pmids = batch_result["esearchresult"].get("idlist", [])
                pmids.extend(batch_pmids)
                
                time.sleep(RATE_LIMIT_DELAY)
            
            logger.info(f"Retrieved {len(pmids)} PMIDs out of {total_count} total")
            return total_count, pmids
            
        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            return 0, []
    
    def _build_search_query(self, supplement: str, search_params: Dict[str, Any]) -> str:
        """
        Build a comprehensive PubMed search query with high-quality filters.
        """
        # Base search for supplement
        query = f'"{supplement}"[Title/Abstract]'
        
        # Add therapeutic context
        query += ' AND (therapy[Title/Abstract] OR treatment[Title/Abstract] OR intervention[Title/Abstract] OR therapeutic[Title/Abstract] OR clinical[Title/Abstract])'
        
        # Add high-quality publication type filters
        pub_type_filters = []
        for pub_type in HIGH_QUALITY_PUBLICATION_TYPES:
            pub_type_filters.append(f'"{pub_type}"[Publication Type]')
        
        if pub_type_filters:
            query += f" AND ({' OR '.join(pub_type_filters)})"
        
        # Add date range if specified
        start_year = search_params.get('start_year')
        end_year = search_params.get('end_year', datetime.now().year)
        
        if start_year:
            query += f" AND {start_year}:{end_year}[pdat]"
        
        # Add language filter (English only for consistency)
        query += ' AND English[Language]'
        
        # Add human studies filter
        query += ' AND humans[MeSH Terms]'
        
        return query
    
    def _process_pmids_in_batches(self, supplement: str, job_id: str, pmids: List[str], total_count: int) -> Dict[str, Any]:
        """
        Process PMIDs in batches, using separate Lambda functions for large batches.
        """
        batch_size = 50  # Smaller batches for Lambda processing
        all_articles = []
        batch_count = 0
        
        for i in range(0, len(pmids), batch_size):
            # Check Lambda timeout
            if time.time() - self.start_time > MAX_EXECUTION_TIME:
                logger.warning("Approaching Lambda timeout, delegating remaining batches")
                # Delegate remaining batches to separate Lambda functions
                self._delegate_remaining_batches(supplement, job_id, pmids[i:], batch_count)
                break
            
            batch_pmids = pmids[i:i + batch_size]
            batch_count += 1
            
            logger.info(f"Processing batch {batch_count} with {len(batch_pmids)} PMIDs")
            
            # Process this batch
            batch_articles = self._fetch_article_details_optimized(batch_pmids)
            all_articles.extend(batch_articles)
            
            # Small delay between batches
            time.sleep(0.1)
        
        return {
            'supplement': supplement,
            'job_id': job_id,
            'search_date': datetime.utcnow().isoformat(),
            'total_count': total_count,
            'retrieved_count': len(all_articles),
            'articles': all_articles,
            'status': 'completed' if len(pmids) <= len(all_articles) * batch_size else 'partial'
        }
    
    def _delegate_remaining_batches(self, supplement: str, job_id: str, remaining_pmids: List[str], start_batch_id: int):
        """
        Delegate remaining PMID batches to separate Lambda functions.
        """
        batch_size = 50
        
        for i in range(0, len(remaining_pmids), batch_size):
            batch_pmids = remaining_pmids[i:i + batch_size]
            batch_id = start_batch_id + (i // batch_size) + 1
            
            batch_event = {
                'event_type': 'batch_processor',
                'supplement': supplement,
                'job_id': job_id,
                'pmids': batch_pmids,
                'batch_id': batch_id
            }
            
            # Send to SQS or invoke directly
            if self.sqs_queue_url:
                self._send_message_to_sqs(batch_event)
            else:
                self._invoke_lambda_async(batch_event)
    
    def _fetch_article_details_optimized(self, pmids: List[str]) -> List[Dict[str, Any]]:
        """
        Optimized article detail fetching for Lambda environment.
        """
        if not pmids:
            return []
        
        articles = []
        
        # Process in smaller batches to respect rate limits and memory
        batch_size = 20
        
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i:i + batch_size]
            
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(batch_pmids),
                "retmode": "xml",
                "tool": "LambdaSupplementCollector",
                "email": self.email
            }
            
            if self.api_key:
                fetch_params["api_key"] = self.api_key
            
            fetch_url = f"{BASE_URL}efetch.fcgi"
            
            try:
                response = requests.get(fetch_url, params=fetch_params)
                response.raise_for_status()
                
                batch_articles = self._parse_pubmed_xml_optimized(response.text)
                articles.extend(batch_articles)
                
                time.sleep(RATE_LIMIT_DELAY)
                
            except Exception as e:
                logger.error(f"Error fetching batch details: {e}")
                continue
        
        return articles
    
    def _parse_pubmed_xml_optimized(self, xml_content: str) -> List[Dict[str, Any]]:
        """
        Optimized XML parsing for Lambda environment.
        """
        try:
            # Use xml.etree.ElementTree for better performance in Lambda
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_content)
            articles = []
            
            for article_elem in root.findall('.//PubmedArticle'):
                try:
                    article_data = {}
                    
                    # Extract PMID
                    pmid_elem = article_elem.find('.//PMID')
                    article_data['pmid'] = pmid_elem.text if pmid_elem is not None else None
                    
                    # Extract title
                    title_elem = article_elem.find('.//ArticleTitle')
                    article_data['title'] = title_elem.text if title_elem is not None else None
                    
                    # Extract authors
                    authors = []
                    for author_elem in article_elem.findall('.//Author'):
                        last_name = author_elem.find('LastName')
                        fore_name = author_elem.find('ForeName')
                        if last_name is not None and fore_name is not None:
                            authors.append(f"{fore_name.text} {last_name.text}")
                        elif last_name is not None:
                            authors.append(last_name.text)
                    article_data['authors'] = authors
                    
                    # Extract journal
                    journal_elem = article_elem.find('.//Journal/Title')
                    article_data['journal'] = journal_elem.text if journal_elem is not None else None
                    
                    # Extract publication date
                    year_elem = article_elem.find('.//PubDate/Year')
                    month_elem = article_elem.find('.//PubDate/Month')
                    day_elem = article_elem.find('.//PubDate/Day')
                    
                    pub_date = ""
                    if year_elem is not None:
                        pub_date = year_elem.text
                        if month_elem is not None:
                            pub_date += f"-{month_elem.text}"
                            if day_elem is not None:
                                pub_date += f"-{day_elem.text}"
                    article_data['publication_date'] = pub_date if pub_date else None
                    
                    # Extract abstract
                    abstract_parts = []
                    for abstract_elem in article_elem.findall('.//AbstractText'):
                        label = abstract_elem.get('Label', '')
                        text = abstract_elem.text or ''
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)
                    article_data['abstract'] = " ".join(abstract_parts) if abstract_parts else None
                    
                    # Extract MeSH terms
                    mesh_terms = []
                    for mesh_elem in article_elem.findall('.//MeshHeading/DescriptorName'):
                        if mesh_elem.text:
                            mesh_terms.append(mesh_elem.text)
                    article_data['mesh_terms'] = mesh_terms
                    
                    # Extract publication types
                    pub_types = []
                    for pub_type_elem in article_elem.findall('.//PublicationType'):
                        if pub_type_elem.text:
                            pub_types.append(pub_type_elem.text)
                    article_data['publication_types'] = pub_types
                    
                    articles.append(article_data)
                    
                except Exception as e:
                    logger.error(f"Error parsing article: {e}")
                    continue
            
            return articles
            
        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
            return []
    
    def _save_to_s3(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Save data to S3 bucket.
        """
        try:
            json_data = json.dumps(data, indent=2, ensure_ascii=False)
            
            s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=key,
                Body=json_data,
                ContentType='application/json'
            )
            
            logger.info(f"Saved data to s3://{self.s3_bucket}/{key}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to S3: {e}")
            return False
    
    def _send_tasks_to_sqs(self, tasks: List[Dict[str, Any]]):
        """
        Send tasks to SQS for parallel processing.
        """
        for task in tasks:
            try:
                sqs_client.send_message(
                    QueueUrl=self.sqs_queue_url,
                    MessageBody=json.dumps(task)
                )
            except Exception as e:
                logger.error(f"Error sending task to SQS: {e}")
    
    def _send_message_to_sqs(self, message: Dict[str, Any]):
        """
        Send a single message to SQS.
        """
        try:
            sqs_client.send_message(
                QueueUrl=self.sqs_queue_url,
                MessageBody=json.dumps(message)
            )
        except Exception as e:
            logger.error(f"Error sending message to SQS: {e}")
    
    def _invoke_workers_directly(self, tasks: List[Dict[str, Any]]):
        """
        Invoke worker Lambda functions directly (for smaller workloads).
        """
        function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
        
        for task in tasks:
            try:
                lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='Event',  # Async invocation
                    Payload=json.dumps(task)
                )
            except Exception as e:
                logger.error(f"Error invoking worker Lambda: {e}")
    
    def _invoke_lambda_async(self, event: Dict[str, Any]):
        """
        Invoke Lambda function asynchronously.
        """
        function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME')
        
        try:
            lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='Event',
                Payload=json.dumps(event)
            )
        except Exception as e:
            logger.error(f"Error invoking Lambda: {e}")

# Global instance
collector = LambdaPubMedCollector()

def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    """
    return collector.lambda_handler(event, context)