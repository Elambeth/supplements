import pandas as pd
import numpy as np
from supabase import create_client, Client
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from typing import List, Dict, Any, Optional
import math

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = ""
SUPABASE_KEY = ""

# Batch configuration  
BATCH_SIZE = 2000  # Larger batches for scoring operations
MAX_WORKERS = 4    # Conservative to avoid overwhelming Supabase

def init_supabase() -> Client:
    """Initialize Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

class SupplementScoring:
    def __init__(self, batch_size: int = BATCH_SIZE, max_workers: int = MAX_WORKERS):
        self.supabase = init_supabase()
        self.batch_size = batch_size
        self.max_workers = max_workers
        
    def calculate_paper_weights_vectorized(self, df: pd.DataFrame) -> pd.Series:
        """Vectorized version of calculate_paper_weight function"""
        logger.debug(f"Calculating weights for {len(df)} papers")
        
        # Base weight with quality bonus
        base_weight = 1.0 + np.maximum(0, df['quality_score'].fillna(50) - 50) / 100.0
        
        # Citation weight (logarithmic scale to avoid extreme outliers)
        citation_weight = 1 + np.log(df['citation_count'].fillna(0) + 1) / 10.0
        
        # Study type weighting
        study_type_weight = np.where(
            (df['is_clinical'] == True) | (df['is_human_study'] == True), 2.0,
            np.where(df['is_animal_study'] == True, 1.5,
                    np.where(df['is_molecular_study'] == True, 1.2, 1.0))
        )
        
        # Recency weighting (exponential decay)
        current_year = datetime.now().year
        publication_years = pd.to_datetime(df['publication_date'], errors='coerce').dt.year
        years_old = current_year - publication_years.fillna(current_year - 10)  # Default to 10 years old
        recency_weight = np.exp(-years_old / 15.0)  # Half-life of ~10 years
        
        # Combine all weights
        final_weight = base_weight * citation_weight * study_type_weight * recency_weight
        
        return final_weight.round(6)  # Round to 6 decimal places for database storage
    
    def normalize_safety_score(self, safety_series: pd.Series) -> pd.Series:
        """Vectorized safety score normalization"""
        def normalize_single_safety(safety_str):
            if pd.isna(safety_str):
                return 0.5
            
            safety_str = str(safety_str).lower().strip()
            
            # Check if it's a numeric string (1-100 scale)
            if safety_str.isdigit():
                return float(safety_str) / 100.0
            
            # Check if it's a fraction format
            if '/' in safety_str:
                parts = safety_str.split('/')
                if len(parts) == 2:
                    try:
                        numerator = float(parts[0].strip())
                        denominator = float(parts[1].strip())
                        if denominator > 0:
                            return numerator / denominator
                    except (ValueError, ZeroDivisionError):
                        pass
            
            # Text-based scoring
            if 'safe' in safety_str:
                return 0.8
            elif any(word in safety_str for word in ['concern', 'warning', 'risk']):
                return 0.3
            else:
                return 0.5
        
        return safety_series.apply(normalize_single_safety)
    
    def calculate_paper_scores_vectorized(self, df: pd.DataFrame) -> pd.Series:
        """Vectorized version of calculate_paper_score function"""
        logger.debug(f"Calculating scores for {len(df)} papers")
        
        # Safety score normalization (40% weight)
        safety_norm = self.normalize_safety_score(df['safety_score']) * 0.4
        
        # Efficacy normalization (40% weight) - scores are 1-100
        efficacy_norm = (df['efficacy_score'].fillna(50) / 100.0) * 0.4
        
        # Quality normalization (20% weight) - scores are 1-100  
        quality_norm = (df['quality_score'].fillna(50) / 100.0) * 0.2
        
        # Combined weighted score
        combined_score = safety_norm + efficacy_norm + quality_norm
        
        return combined_score.round(6)  # Round for database storage
    
    def get_papers_to_process(self, supplement_id: Optional[int] = None) -> pd.DataFrame:
        """Get papers that need weight/score calculation"""
        logger.info("Fetching papers that need processing...")
        
        # Build query - only get papers that:
        # 1. Have quality scores (required for calculation)
        # 2. Don't have weight scores yet (need processing)
        query = (
            self.supabase.table('supplement_studies').select(
                'id, supplement_id, citation_count, is_clinical, is_human_study, '
                'is_animal_study, is_molecular_study, publication_date, '
                'quality_score, safety_score, efficacy_score'
            )
            .not_.is_('quality_score', 'null')  # Must have quality score
            .is_('weight_score', 'null')        # Must NOT have weight score (needs processing)
        )
        
        if supplement_id:
            query = query.eq('supplement_id', supplement_id)
        
        # Execute query in chunks to handle large datasets
        all_data = []
        offset = 0
        chunk_size = 1000  # Smaller chunks to avoid issues
        
        while True:
            try:
                # Use limit and offset instead of range
                result = query.limit(chunk_size).offset(offset).execute()
                
                if not result.data:
                    break
                    
                all_data.extend(result.data)
                offset += chunk_size
                
                logger.info(f"Fetched {len(all_data)} papers so far...")
                
                # Break if we got less than chunk_size (end of data)
                if len(result.data) < chunk_size:
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching data at offset {offset}: {str(e)}")
                break
        
        df = pd.DataFrame(all_data)
        logger.info(f"Total papers to process: {len(df)}")
        
        return df
    

    def check_unprocessed_papers_count(self, supplement_id: Optional[int] = None) -> Dict[str, int]:
        """Check how many papers still need weight score calculation"""
        try:
            # Papers that need processing (have quality score but no weight score)
            query_need_processing = self.supabase.table('supplement_studies').select(
                'id', count='exact'
            ).not_.is_('quality_score', 'null').is_('weight_score', 'null')
            
            if supplement_id:
                query_need_processing = query_need_processing.eq('supplement_id', supplement_id)
            
            result_need_processing = query_need_processing.execute()
            
            # Papers that can't be processed (no quality score)
            query_no_quality = self.supabase.table('supplement_studies').select(
                'id', count='exact'
            ).is_('quality_score', 'null')
            
            if supplement_id:
                query_no_quality = query_no_quality.eq('supplement_id', supplement_id)
                
            result_no_quality = query_no_quality.execute()
            
            # Papers already processed
            query_already_processed = self.supabase.table('supplement_studies').select(
                'id', count='exact'
            ).not_.is_('weight_score', 'null')
            
            if supplement_id:
                query_already_processed = query_already_processed.eq('supplement_id', supplement_id)
                
            result_already_processed = query_already_processed.execute()
            
            counts = {
                'need_processing': result_need_processing.count,
                'missing_quality_score': result_no_quality.count,
                'already_processed': result_already_processed.count,
                'total': result_need_processing.count + result_no_quality.count + result_already_processed.count
            }
            
            logger.info("\n" + "=" * 50)
            logger.info("PAPER PROCESSING STATUS")
            logger.info("=" * 50)
            logger.info(f"Papers needing processing: {counts['need_processing']:,}")
            logger.info(f"Papers already processed: {counts['already_processed']:,}")
            logger.info(f"Papers missing quality score: {counts['missing_quality_score']:,}")
            logger.info(f"Total papers: {counts['total']:,}")
            logger.info("=" * 50)
            
            return counts
            
        except Exception as e:
            logger.error(f"Error checking unprocessed papers: {str(e)}")
            return {'error': str(e)}


    def update_paper_weights_batch(self, batch_data: List[Dict]) -> Dict[str, int]:
        """Update a batch of paper weights and scores"""
        results = {'successful': 0, 'failed': 0}
        
        try:
            # Convert to DataFrame for vectorized operations
            df_batch = pd.DataFrame(batch_data)
            
            # Calculate weights and scores
            df_batch['weight_score'] = self.calculate_paper_weights_vectorized(df_batch)
            df_batch['normalized_score'] = self.calculate_paper_scores_vectorized(df_batch)
            df_batch['weight_calculated_at'] = datetime.now().isoformat()
            
            # Update each record (Supabase doesn't have bulk update, so we batch the calls)
            update_records = []
            for _, row in df_batch.iterrows():
                update_data = {
                    'weight_score': float(row['weight_score']),
                    'normalized_score': float(row['normalized_score']),
                    'weight_calculated_at': row['weight_calculated_at']
                }
                update_records.append({'id': row['id'], 'data': update_data})
            
            # Batch update using multiple calls (more efficient than one-by-one)
            for record in update_records:
                try:
                    self.supabase.table('supplement_studies').update(
                        record['data']
                    ).eq('id', record['id']).execute()
                    results['successful'] += 1
                except Exception as e:
                    logger.error(f"Failed to update paper ID {record['id']}: {str(e)}")
                    results['failed'] += 1
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            results['failed'] = len(batch_data)
        
        return results
    
    def update_paper_weights_parallel(self, supplement_id: Optional[int] = None) -> int:
        """Update paper weights using parallel batch processing"""
        # Get all papers to process
        df_papers = self.get_papers_to_process(supplement_id)
        
        if df_papers.empty:
            logger.info("No papers to process")
            return 0
        
        # Convert to list of dicts for batch processing
        papers_data = df_papers.to_dict('records')
        
        # Split into batches
        batches = [papers_data[i:i + self.batch_size] for i in range(0, len(papers_data), self.batch_size)]
        total_batches = len(batches)
        
        logger.info(f"Processing {len(papers_data)} papers in {total_batches} batches using {self.max_workers} workers")
        
        total_results = {'successful': 0, 'failed': 0}
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batch jobs
            future_to_batch = {
                executor.submit(self.update_paper_weights_batch, batch): i + 1 
                for i, batch in enumerate(batches)
            }
            
            # Collect results as they complete
            completed_batches = 0
            for future in as_completed(future_to_batch):
                batch_num = future_to_batch[future]
                try:
                    batch_results = future.result()
                    
                    # Aggregate results
                    for key in total_results:
                        total_results[key] += batch_results[key]
                    
                    completed_batches += 1
                    elapsed_time = time.time() - start_time
                    avg_time_per_batch = elapsed_time / completed_batches
                    estimated_remaining = (total_batches - completed_batches) * avg_time_per_batch
                    
                    logger.info(f"Completed batch {batch_num} ({completed_batches}/{total_batches}). "
                              f"Success: {batch_results['successful']}, Failed: {batch_results['failed']}. "
                              f"ETA: {estimated_remaining:.1f}s")
                    
                except Exception as e:
                    logger.error(f"Batch {batch_num} failed with exception: {str(e)}")
                    total_results['failed'] += len(batches[batch_num - 1])
        
        elapsed_time = time.time() - start_time
        logger.info(f"Weight calculation complete in {elapsed_time:.1f} seconds!")
        logger.info(f"Successfully updated: {total_results['successful']}")
        logger.info(f"Failed updates: {total_results['failed']}")
        logger.info(f"Processing rate: {total_results['successful'] / elapsed_time:.1f} papers/second")
        
        return total_results['successful']
    
    def get_supplements_for_aggregation(self, supplement_id: Optional[int] = None) -> List[int]:
        """Get supplement IDs that need aggregation"""
        query = self.supabase.table('supplement_studies').select('supplement_id').not_.is_('supplement_id', 'null').not_.is_('weight_score', 'null')
        
        if supplement_id:
            query = query.eq('supplement_id', supplement_id)
        
        # Get all supplement IDs with calculated weights
        result = query.execute()
        supplement_ids = list(set([row['supplement_id'] for row in result.data]))
        
        logger.info(f"Found {len(supplement_ids)} supplements needing aggregation")
        return supplement_ids
    
    def calculate_supplement_aggregates(self, supplement_ids: List[int]) -> List[Dict]:
        """Calculate aggregates for a batch of supplements"""
        aggregates = []
        
        for supp_id in supplement_ids:
            try:
                # Get all studies for this supplement with calculated weights
                studies_result = self.supabase.table('supplement_studies').select(
                    'id, safety_score, efficacy_score, quality_score, weight_score, normalized_score'
                ).eq('supplement_id', supp_id).not_.is_('weight_score', 'null').execute()
                
                if not studies_result.data:
                    continue
                
                df_studies = pd.DataFrame(studies_result.data)
                
                # Calculate weighted averages
                weights = df_studies['weight_score']
                total_weight = weights.sum()
                
                if total_weight == 0:
                    continue
                
                # Safety score (handle text format)
                safety_normalized = self.normalize_safety_score(df_studies['safety_score'])
                avg_safety = np.average(safety_normalized, weights=weights)
                
                # Efficacy and quality (1-100 scale)
                avg_efficacy = np.average(df_studies['efficacy_score'].fillna(50) / 100.0, weights=weights)
                avg_quality = np.average(df_studies['quality_score'].fillna(50) / 100.0, weights=weights)
                
                # Overall score
                overall_score = avg_safety * 0.4 + avg_efficacy * 0.4 + avg_quality * 0.2
                
                # Consistency score (coefficient of variation)
                scores = df_studies['normalized_score'].dropna()
                if len(scores) > 1:
                    consistency_score = max(0, 1.0 - (scores.std() / scores.mean())) if scores.mean() > 0 else 1.0
                else:
                    consistency_score = 1.0
                
                # Confidence level
                study_count = len(df_studies)
                if study_count >= 20 and total_weight >= 30:
                    confidence_level = 'high'
                elif study_count >= 10 and total_weight >= 15:
                    confidence_level = 'medium'
                elif study_count >= 5 and total_weight >= 5:
                    confidence_level = 'low'
                else:
                    confidence_level = 'very_low'
                
                # Research summary
                research_summary = (
                    f"Overall: {overall_score*10:.1f}/10 | "
                    f"Safety: {avg_safety*10:.1f}/10 | "
                    f"Efficacy: {avg_efficacy*10:.1f}/10 | "
                    f"Quality: {avg_quality*10:.1f}/10 | "
                    f"Confidence: {confidence_level} ({study_count} studies)"
                )
                
                aggregate_data = {
                    'supplement_id': supp_id,
                    'avg_safety_score': round(avg_safety, 6),
                    'avg_efficacy_score': round(avg_efficacy, 6),
                    'avg_quality_score': round(avg_quality, 6),
                    'safety_score_count': study_count,
                    'efficacy_score_count': study_count,
                    'quality_score_count': study_count,
                    'findings_consistency_score': round(consistency_score, 6),
                    'overall_score': round(overall_score, 6),
                    'confidence_level': confidence_level,
                    'weighted_study_count': round(total_weight, 6),
                    'research_summary': research_summary,
                    'last_aggregated_at': datetime.now().isoformat()
                }
                
                aggregates.append(aggregate_data)
                
            except Exception as e:
                logger.error(f"Error calculating aggregate for supplement {supp_id}: {str(e)}")
        
        return aggregates
    
    def update_supplement_aggregates(self, supplement_id: Optional[int] = None) -> int:
        """Update supplement aggregates using batch processing"""
        # Get supplements to process
        supplement_ids = self.get_supplements_for_aggregation(supplement_id)
        
        if not supplement_ids:
            logger.info("No supplements to aggregate")
            return 0
        
        # Process in batches
        batch_size = 50  # Smaller batches for aggregate calculations
        batches = [supplement_ids[i:i + batch_size] for i in range(0, len(supplement_ids), batch_size)]
        
        logger.info(f"Processing {len(supplement_ids)} supplements in {len(batches)} batches")
        
        total_updated = 0
        start_time = time.time()
        
        for i, batch in enumerate(batches):
            try:
                # Calculate aggregates for this batch
                aggregates = self.calculate_supplement_aggregates(batch)
                
                # Update/insert aggregates
                for aggregate in aggregates:
                    try:
                        # Try update first
                        existing = self.supabase.table('supplement_research_aggregates').select('id').eq('supplement_id', aggregate['supplement_id']).execute()
                        
                        if existing.data:
                            # Update existing record
                            self.supabase.table('supplement_research_aggregates').update(
                                aggregate
                            ).eq('supplement_id', aggregate['supplement_id']).execute()
                        else:
                            # Insert new record
                            self.supabase.table('supplement_research_aggregates').insert(
                                aggregate
                            ).execute()
                        
                        total_updated += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to upsert aggregate for supplement {aggregate['supplement_id']}: {str(e)}")
                
                logger.info(f"Completed batch {i+1}/{len(batches)}. Updated {len(aggregates)} aggregates.")
                
            except Exception as e:
                logger.error(f"Error processing aggregate batch {i+1}: {str(e)}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Aggregate calculation complete in {elapsed_time:.1f} seconds!")
        logger.info(f"Successfully updated: {total_updated} supplements")
        
        return total_updated
    
    def run_complete_scoring_update(self, supplement_id: Optional[int] = None, skip_weights: bool = False) -> Dict:
        """Run the complete scoring update process"""
        start_time = time.time()
        
        logger.info("=" * 60)
        logger.info("STARTING COMPLETE SCORING UPDATE")
        logger.info("=" * 60)
        logger.info(f"Target supplement: {supplement_id or 'ALL'}")
        logger.info(f"Batch size: {self.batch_size}")
        logger.info(f"Max workers: {self.max_workers}")
        logger.info(f"Skip weights: {skip_weights}")
        
        results = {}
        
        # Phase 1: Update paper weights and scores
        if not skip_weights:
            logger.info("\n--- PHASE 1: CALCULATING PAPER WEIGHTS AND SCORES ---")
            weight_start = time.time()
            papers_processed = self.update_paper_weights_parallel(supplement_id)
            weight_duration = time.time() - weight_start
            
            results['weight_phase'] = {
                'duration': weight_duration,
                'papers_processed': papers_processed,
                'papers_per_second': papers_processed / weight_duration if weight_duration > 0 else 0
            }
            
            logger.info(f"Phase 1 complete: {papers_processed} papers in {weight_duration:.1f}s "
                       f"({results['weight_phase']['papers_per_second']:.1f} papers/sec)")
        else:
            logger.info("\n--- SKIPPING PHASE 1: WEIGHT CALCULATION ---")
            results['weight_phase'] = {'duration': 0, 'papers_processed': 0, 'papers_per_second': 0}
        
        # Phase 2: Update supplement aggregates
        logger.info("\n--- PHASE 2: CALCULATING SUPPLEMENT AGGREGATES ---")
        agg_start = time.time()
        supplements_processed = self.update_supplement_aggregates(supplement_id)
        agg_duration = time.time() - agg_start
        
        results['aggregate_phase'] = {
            'duration': agg_duration,
            'supplements_processed': supplements_processed,
            'supplements_per_second': supplements_processed / agg_duration if agg_duration > 0 else 0
        }
        
        total_duration = time.time() - start_time
        
        logger.info(f"Phase 2 complete: {supplements_processed} supplements in {agg_duration:.1f}s "
                   f"({results['aggregate_phase']['supplements_per_second']:.1f} supplements/sec)")
        
        results['total_duration'] = total_duration
        results['total_records_processed'] = results['weight_phase']['papers_processed'] + supplements_processed
        
        logger.info("\n" + "=" * 60)
        logger.info("SCORING UPDATE COMPLETE!")
        logger.info("=" * 60)
        logger.info(f"Total time: {total_duration:.1f} seconds")
        logger.info(f"Papers processed: {results['weight_phase']['papers_processed']}")
        logger.info(f"Supplements processed: {supplements_processed}")
        logger.info(f"Total records: {results['total_records_processed']}")
        logger.info("=" * 60)
        
        return results
    
    def check_scoring_status(self) -> Dict[str, Any]:
        """Check the current status of scoring progress"""
        status = {}
        
        try:
            # Total papers
            total_papers = self.supabase.table('supplement_studies').select('id', count='exact').execute()
            status['total_papers'] = total_papers.count
            
            # Papers with weights
            papers_with_weights = self.supabase.table('supplement_studies').select('id', count='exact').not_.is_('weight_score', 'null').execute()
            status['papers_with_weights'] = papers_with_weights.count
            
            # Papers with scores
            papers_with_scores = self.supabase.table('supplement_studies').select('id', count='exact').not_.is_('normalized_score', 'null').execute()
            status['papers_with_scores'] = papers_with_scores.count
            
            # Total supplements
            total_supplements = self.supabase.table('supplement_studies').select('supplement_id', count='exact').not_.is_('supplement_id', 'null').execute()
            # Note: This gives us total rows, not unique supplements
            # For unique count, we'd need to fetch and process
            
            # Supplements with aggregates
            supplements_with_aggregates = self.supabase.table('supplement_research_aggregates').select('id', count='exact').execute()
            status['supplements_with_aggregates'] = supplements_with_aggregates.count
            
            # Calculate percentages
            if status['total_papers'] > 0:
                status['weight_completion_percent'] = (status['papers_with_weights'] / status['total_papers']) * 100
                status['score_completion_percent'] = (status['papers_with_scores'] / status['total_papers']) * 100
            
            # Get latest update timestamps
            latest_weight_update = self.supabase.table('supplement_studies').select('weight_calculated_at').not_.is_('weight_calculated_at', 'null').order('weight_calculated_at', desc=True).limit(1).execute()
            if latest_weight_update.data:
                status['last_weight_update'] = latest_weight_update.data[0]['weight_calculated_at']
            
            latest_aggregate_update = self.supabase.table('supplement_research_aggregates').select('last_aggregated_at').order('last_aggregated_at', desc=True).limit(1).execute()
            if latest_aggregate_update.data:
                status['last_aggregate_update'] = latest_aggregate_update.data[0]['last_aggregated_at']
            
        except Exception as e:
            logger.error(f"Error checking status: {str(e)}")
            status['error'] = str(e)
        
        return status
    
    def print_status(self):
        """Print a formatted status report"""
        status = self.check_scoring_status()
        
        logger.info("\n" + "=" * 50)
        logger.info("SCORING STATUS REPORT")
        logger.info("=" * 50)
        
        for key, value in status.items():
            if 'percent' in key:
                logger.info(f"{key.replace('_', ' ').title()}: {value:.1f}%")
            else:
                logger.info(f"{key.replace('_', ' ').title()}: {value}")
        
        logger.info("=" * 50)

def main():
    """Main function to run the scoring update process."""
    
    # Initialize scorer
    logger.info("Initializing scoring system...")
    scorer = SupplementScoring(batch_size=BATCH_SIZE, max_workers=MAX_WORKERS)
    
    # Check current status
    scorer.print_status()
    
    # Ask user what they want to do
    print("\nScoring Update Options:")
    print("1. Run complete update for all supplements")
    print("2. Run update for specific supplement")
    print("3. Run update skipping weight calculation (aggregates only)")
    print("4. Check status only")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == '1':
        logger.info("Starting complete update for all supplements...")
        results = scorer.run_complete_scoring_update()
        
    elif choice == '2':
        supplement_id = input("Enter supplement ID: ").strip()
        try:
            supplement_id = int(supplement_id)
            logger.info(f"Starting update for supplement {supplement_id}...")
            results = scorer.run_complete_scoring_update(supplement_id=supplement_id)
        except ValueError:
            logger.error("Invalid supplement ID")
            return
            
    elif choice == '3':
        logger.info("Starting aggregates-only update...")
        results = scorer.run_complete_scoring_update(skip_weights=True)
        
    elif choice == '4':
        logger.info("Status check complete.")
        return
        
    else:
        logger.error("Invalid choice")
        return
    
    # Print final results
    if 'results' in locals():
        logger.info(f"\n{'='*50}")
        logger.info(f"FINAL SUMMARY:")
        logger.info(f"Total duration: {results['total_duration']:.1f} seconds")
        logger.info(f"Papers processed: {results['weight_phase']['papers_processed']}")
        logger.info(f"Supplements processed: {results['aggregate_phase']['supplements_processed']}")
        logger.info(f"Overall processing rate: {results['total_records_processed'] / results['total_duration']:.1f} records/second")
        logger.info(f"{'='*50}")

if __name__ == "__main__":
    main()
