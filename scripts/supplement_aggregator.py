import os
import time
import json
import logging
import argparse
import sys
from datetime import datetime, timezone
import dotenv
import requests
from supabase import create_client
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure console output to handle Unicode properly
if sys.platform == 'win32':
    # Force UTF-8 encoding for console output on Windows
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("supplement_aggregation.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("supplement_aggregator")

# Load environment variables from .env file
dotenv.load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
LLM_MODEL = "deepseek-chat"  # Model from user's example
LLM_BASE_URL = "https://api.deepseek.com"
AGGREGATION_VERSION = "1.0"  # Current aggregation version
API_RETRY_ATTEMPTS = 3
API_RETRY_WAIT_MULTIPLIER = 2
API_RETRY_WAIT_MIN = 1
API_RETRY_WAIT_MAX = 10
MIN_STUDIES_FOR_AGGREGATION = 2  # Minimum studies needed to perform aggregation

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def convert_safety_score(safety_score):
    """
    Convert safety_score from text field to numeric value
    """
    if not safety_score or "not assessed" in safety_score.lower():
        return None
    
    try:
        # Extract numeric portion if it exists
        for part in safety_score.split():
            if part.isdigit():
                return int(part)
        return None
    except (ValueError, AttributeError):
        return None

@retry(
    stop=stop_after_attempt(API_RETRY_ATTEMPTS),
    wait=wait_exponential(
        multiplier=API_RETRY_WAIT_MULTIPLIER,
        min=API_RETRY_WAIT_MIN,
        max=API_RETRY_WAIT_MAX
    ),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def analyze_with_deepseek(prompt):
    """
    Send prompt to DeepSeek API for analysis with retry logic
    """
    system_message = """
    You are a scientific research analysis expert. Follow these instructions carefully:
    
    1. When asked to rate on a scale of 1-10, ALWAYS respond with a single integer between 1 and 10.
    2. For consistency_score, provide a single integer (1-10).
    3. Do not include explanations within the score fields.
    4. Format your response exactly as requested in the prompt.
    5. Be concise but informative in your summaries.
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,  # Lower temperature for more deterministic responses
    }
    
    url = f"{LLM_BASE_URL}/v1/chat/completions"
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        data = response.json()
        result = data["choices"][0]["message"]["content"]
        
        # Log the raw response for debugging
        logger.debug(f"Raw DeepSeek response: {result}")
        
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling DeepSeek API: {str(e)}")
        raise  # Retry will handle this
    except KeyError as e:
        logger.error(f"Unexpected API response format: {str(e)}")
        logger.debug(f"API response: {response.text}")
        raise RuntimeError("Unexpected API response format")

def analyze_findings_consistency(supplement_id, supplement_name, studies):
    """
    Analyze consistency of findings across studies using LLM
    """
    # Extract results summaries
    results_summaries = [study.get('results_summary') for study in studies if study.get('results_summary')]
    
    if not results_summaries or len(results_summaries) < 2:
        return {
            'findings_consistency_score': None,
            'findings_summary': None
        }
    
    # Create prompt for analyzing consistency
    prompt = f"""Analyze the following research findings for {supplement_name} and evaluate their consistency.
    
Research Findings:
{json.dumps(results_summaries, indent=2)}

Based on these findings:

1. Rate the consistency of findings on a scale of 1-10:
   - 1-3: Highly inconsistent/contradictory findings
   - 4-6: Mixed findings with some disagreement
   - 7-10: Highly consistent findings across studies

2. Write a brief (2-3 sentences) summary of the overall findings consistency, noting major agreements or disagreements.

Format your response as follows:

CONSISTENCY_SCORE: [1-10]

FINDINGS_SUMMARY: [2-3 sentence summary]"""

    # Use DeepSeek API call
    response_text = analyze_with_deepseek(prompt)
    
    # Parse response
    consistency_score = None
    findings_summary = None
    
    lines = response_text.strip().split('\n')
    for line in lines:
        if line.startswith('CONSISTENCY_SCORE:'):
            score_text = line.replace('CONSISTENCY_SCORE:', '').strip()
            try:
                consistency_score = int(score_text)
            except ValueError:
                pass
        elif line.startswith('FINDINGS_SUMMARY:'):
            findings_summary = line.replace('FINDINGS_SUMMARY:', '').strip()
    
    return {
        'findings_consistency_score': consistency_score,
        'findings_summary': findings_summary
    }

def generate_research_summary(supplement_name, studies, metrics):
    """
    Generate a concise research summary using LLM
    """
    # Count study types
    study_types = {}
    for study in studies:
        if study.get('publication_types'):
            for study_type in study['publication_types']:
                study_types[study_type] = study_types.get(study_type, 0) + 1
    
    top_study_types = sorted(study_types.items(), key=lambda x: x[1], reverse=True)[:3]
    
    # Create prompt
    prompt = f"""Generate a concise 2-3 sentence research summary for {supplement_name} based on the following data:

Number of studies analyzed: {len(studies)}
Average safety score: {metrics.get('avg_safety_score')}
Average efficacy score: {metrics.get('avg_efficacy_score')}
Average quality score: {metrics.get('avg_quality_score')}
Consistency score: {metrics.get('findings_consistency_score')}
Consistency summary: {metrics.get('findings_summary')}
Top study types: {json.dumps(top_study_types)}

Your summary should:
1. Mention the quantity and quality of research
2. Highlight the general consensus on efficacy and safety
3. Be objective, accurate, and concise

Format your response as a single paragraph with no prefix or additional text."""

    # Use DeepSeek API
    research_summary = analyze_with_deepseek(prompt)
    
    return research_summary.strip()

def extract_common_metadata(studies):
    """
    Extract common metadata from studies like populations, dosages, etc.
    """
    # Initialize counters for different metadata
    populations = {}
    dosages = {}
    durations = {}
    interactions = {}
    study_designs = {}
    
    for study in studies:
        # Track populations
        population = study.get('population_specificity')
        if population and population.lower() not in ['none mentioned', 'not mentioned']:
            populations[population] = populations.get(population, 0) + 1
        
        # Track dosages
        dosage = study.get('effective_dosage')
        if dosage and dosage.lower() not in ['none mentioned', 'not mentioned']:
            dosages[dosage] = dosages.get(dosage, 0) + 1
        
        # Track durations
        duration = study.get('study_duration')
        if duration and duration.lower() not in ['none mentioned', 'not mentioned']:
            durations[duration] = durations.get(duration, 0) + 1
        
        # Track interactions
        interaction = study.get('interactions')
        if interaction and interaction.lower() not in ['none mentioned', 'not mentioned']:
            interactions[interaction] = interactions.get(interaction, 0) + 1
        
        # Track study designs
        if study.get('publication_types'):
            for study_type in study['publication_types']:
                study_designs[study_type] = study_designs.get(study_type, 0) + 1
    
    # Get top values for each category
    top_populations = [p[0] for p in sorted(populations.items(), key=lambda x: x[1], reverse=True)[:5]] if populations else []
    top_dosages = [d[0] for d in sorted(dosages.items(), key=lambda x: x[1], reverse=True)[:5]] if dosages else []
    top_interactions = [i[0] for i in sorted(interactions.items(), key=lambda x: x[1], reverse=True)[:5]] if interactions else []
    top_study_designs = [s[0] for s in sorted(study_designs.items(), key=lambda x: x[1], reverse=True)[:5]] if study_designs else []
    
    # Get most common duration
    typical_duration = None
    if durations:
        typical_duration = max(durations.items(), key=lambda x: x[1])[0]
    
    return {
        'populations_studied': top_populations,
        'common_dosages': top_dosages,
        'typical_duration': typical_duration,
        'common_interactions': top_interactions,
        'top_study_designs': top_study_designs
    }

def calculate_aggregate_metrics(supplement_id):
    """
    Calculate aggregate metrics for a supplement based on its analyzed studies
    """
    try:
        # Get supplement name
        supp_response = supabase.table("supplements").select("name").eq("id", supplement_id).execute()
        
        if not supp_response.data:
            logger.error(f"Supplement with ID {supplement_id} not found")
            return None
            
        supplement_name = supp_response.data[0]['name']
        
        # Get all analyzed studies for this supplement
        response = supabase.table("supplement_studies") \
            .select("*, publication_types") \
            .eq("supplement_id", supplement_id) \
            .not_.is_("last_analyzed_at", "null") \
            .execute()
        
        studies = response.data
        
        if not studies:
            logger.info(f"No analyzed studies found for supplement ID {supplement_id}")
            return None
        
        if len(studies) < MIN_STUDIES_FOR_AGGREGATION:
            logger.info(f"Not enough analyzed studies for supplement ID {supplement_id} (found {len(studies)}, need {MIN_STUDIES_FOR_AGGREGATION})")
            return None
        
        # Initialize metrics dictionary
        metrics = {
            'supplement_id': supplement_id,
            'avg_safety_score': None,
            'avg_efficacy_score': None,
            'avg_quality_score': None,
            'safety_score_count': 0,
            'efficacy_score_count': 0,
            'quality_score_count': 0,
            'findings_consistency_score': None,
            'findings_summary': None,
            'research_summary': None,
            'top_study_designs': [],
            'populations_studied': [],
            'common_dosages': [],
            'typical_duration': None,
            'common_interactions': [],
            'last_aggregated_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Calculate averages for numeric scores
        safety_scores = []
        efficacy_scores = []
        quality_scores = []
        
        for study in studies:
            # Process safety scores
            safety_score = convert_safety_score(study.get('safety_score'))
            if safety_score is not None:
                safety_scores.append(safety_score)
            
            # Process efficacy scores
            efficacy_score = study.get('efficacy_score')
            if efficacy_score is not None:
                efficacy_scores.append(efficacy_score)
            
            # Process quality scores
            quality_score = study.get('quality_score')
            if quality_score is not None:
                quality_scores.append(quality_score)
        
        # Calculate averages if we have data
        if safety_scores:
            metrics['avg_safety_score'] = round(sum(safety_scores) / len(safety_scores), 2)
            metrics['safety_score_count'] = len(safety_scores)
        
        if efficacy_scores:
            metrics['avg_efficacy_score'] = round(sum(efficacy_scores) / len(efficacy_scores), 2)
            metrics['efficacy_score_count'] = len(efficacy_scores)
        
        if quality_scores:
            metrics['avg_quality_score'] = round(sum(quality_scores) / len(quality_scores), 2)
            metrics['quality_score_count'] = len(quality_scores)
        
        # Generate findings consistency score and summary
        consistency_data = analyze_findings_consistency(supplement_id, supplement_name, studies)
        metrics.update(consistency_data)
        
        # Extract common metadata
        metadata = extract_common_metadata(studies)
        metrics.update(metadata)
        
        # Generate research summary
        if metrics['avg_safety_score'] is not None or metrics['avg_efficacy_score'] is not None:
            metrics['research_summary'] = generate_research_summary(supplement_name, studies, metrics)
        
        return metrics
    except Exception as e:
        logger.error(f"Error calculating aggregate metrics for supplement ID {supplement_id}: {str(e)}")
        return None

def update_supplement_aggregates(supplement_id, metrics):
    """
    Update or create aggregate records for a supplement
    """
    try:
        if not metrics:
            return False
        
        # Check if record exists
        response = supabase.table("supplement_research_aggregates") \
            .select("id") \
            .eq("supplement_id", supplement_id) \
            .execute()
        
        if response.data:
            # Update existing record
            logger.info(f"Updating existing aggregate record for supplement ID {supplement_id}")
            response = supabase.table("supplement_research_aggregates") \
                .update(metrics) \
                .eq("supplement_id", supplement_id) \
                .execute()
        else:
            # Create new record
            logger.info(f"Creating new aggregate record for supplement ID {supplement_id}")
            response = supabase.table("supplement_research_aggregates") \
                .insert(metrics) \
                .execute()
        
        return True
    except Exception as e:
        logger.error(f"Error updating supplement aggregates for ID {supplement_id}: {str(e)}")
        return False

def get_supplements_for_aggregation(specific_supplement_id=None, min_analyzed_studies=MIN_STUDIES_FOR_AGGREGATION):
    """
    Get a list of supplements that have enough analyzed studies for aggregation
    
    Parameters:
    - specific_supplement_id: If provided, only check this supplement
    - min_analyzed_studies: Minimum number of analyzed studies required
    """
    try:
        if specific_supplement_id:
            # If a specific supplement ID is provided, just get that one
            query = supabase.table("supplements").select("id, name").eq("id", specific_supplement_id)
            response = query.execute()
            supplements = response.data
        else:
            # Otherwise get all supplements
            query = supabase.table("supplements").select("id, name")
            response = query.execute()
            supplements = response.data
            
        # Filter to only include supplements with enough analyzed studies
        filtered_supplements = []
        
        for supplement in supplements:
            supp_id = supplement['id']
            
            # Check if this supplement has enough processed studies
            analyzed_response = supabase.table("supplement_studies")\
                .select("id", count="exact")\
                .eq("supplement_id", supp_id)\
                .not_.is_("last_analyzed_at", "null")\
                .execute()
            
            analyzed_count = analyzed_response.count
            
            # Only include supplements with enough analyzed studies
            if analyzed_count >= min_analyzed_studies:
                filtered_supplements.append(supplement)
        
        return filtered_supplements
            
    except Exception as e:
        logger.error(f"Error fetching supplements: {str(e)}")
        return []

def save_progress(supplement_id, success):
    """
    Save progress information to a local file
    """
    progress_data = {
        'last_supplement_id': supplement_id,
        'success': success,
        'timestamp': datetime.now().isoformat()
    }
    
    with open('aggregation_progress.json', 'w') as f:
        json.dump(progress_data, f)

def load_progress():
    """
    Load progress information from a local file
    """
    try:
        with open('aggregation_progress.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def parse_arguments():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(description='Aggregate supplement research metrics')
    parser.add_argument('--supplement', type=int, help='Specific supplement ID to process')
    parser.add_argument('--reset', action='store_true', help='Ignore previous progress and start from beginning')
    parser.add_argument('--min-studies', type=int, default=MIN_STUDIES_FOR_AGGREGATION, 
                        help=f'Minimum analyzed studies required (default: {MIN_STUDIES_FOR_AGGREGATION})')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--skip-errors', action='store_true', 
                        help='Continue processing even if a supplement fails')
    parser.add_argument('--force', action='store_true',
                        help='Force aggregation even if there are too few studies')
    return parser.parse_args()

def main():
    """
    Main function to process supplements and aggregate their research metrics
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Add debug logging flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
        debug_handler = logging.FileHandler("supplement_aggregation_debug.log", encoding='utf-8')
        debug_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        debug_handler.setFormatter(formatter)
        logger.addHandler(debug_handler)
        logger.debug("Debug logging enabled")
    
    logger.info(f"Starting aggregation script at {datetime.now().isoformat()}")
    logger.info(f"Using aggregation version: {AGGREGATION_VERSION}")
    logger.info(f"Min studies required: {args.min_studies}")
    
    # Load progress from previous run (unless reset flag is set)
    progress = None if args.reset else load_progress()
    last_supplement_id = progress.get('last_supplement_id') if progress else None
    
    if last_supplement_id and not args.reset:
        logger.info(f"Resuming from supplement ID: {last_supplement_id}")
    
    # Get supplements for aggregation
    min_studies = 1 if args.force else args.min_studies
    supplements = get_supplements_for_aggregation(args.supplement, min_studies)
    
    logger.info(f"Found {len(supplements)} supplements with at least {min_studies} analyzed studies")
    
    if not supplements:
        logger.info("No eligible supplements found. Exiting.")
        return
    
    # If we have a last_supplement_id, start from there
    start_processing = False if last_supplement_id and not args.reset else True
    
    total_processed = 0
    
    for supplement in supplements:
        supplement_id = supplement['id']
        supplement_name = supplement['name']
        
        # Skip supplements until we reach the last processed one
        if not start_processing and last_supplement_id:
            if supplement_id == last_supplement_id:
                start_processing = True
            else:
                continue
        
        logger.info(f"\nProcessing supplement: {supplement_name} (ID: {supplement_id})")
        
        try:
            # Calculate aggregate metrics
            metrics = calculate_aggregate_metrics(supplement_id)
            
            if not metrics:
                logger.warning(f"Not enough data to aggregate metrics for supplement {supplement_name}.")
                continue
            
            # Update supplement aggregates
            success = update_supplement_aggregates(supplement_id, metrics)
            
            if success:
                logger.info(f"Successfully updated aggregates for {supplement_name}")
                total_processed += 1
            else:
                logger.warning(f"Failed to update aggregates for {supplement_name}")
                if not args.skip_errors:
                    logger.error("Stopping due to update error. Use --skip-errors to continue despite errors.")
                    return
            
            # Save progress after each supplement
            save_progress(supplement_id, success)
            
        except Exception as e:
            logger.error(f"Error processing supplement {supplement_name}: {str(e)}")
            if not args.skip_errors:
                logger.error("Stopping due to processing error. Use --skip-errors to continue despite errors.")
                return
        
        # Sleep to avoid API rate limits
        time.sleep(1)
    
    logger.info(f"\nAggregation script completed at {datetime.now().isoformat()}")
    logger.info(f"Total supplements processed: {total_processed}")

if __name__ == "__main__":
    main()