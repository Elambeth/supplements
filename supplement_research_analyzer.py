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
        logging.FileHandler("supplement_analysis.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("supplement_analyzer")

# Load environment variables from .env file
dotenv.load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
LLM_MODEL = "deepseek-chat"  # Model from user's example
LLM_BASE_URL = "https://api.deepseek.com"
PROMPT_VERSION = "1.1"  # Current prompt version
MAX_PAPERS_PER_SUPPLEMENT = 20
API_RETRY_ATTEMPTS = 3
API_RETRY_WAIT_MULTIPLIER = 2
API_RETRY_WAIT_MIN = 1
API_RETRY_WAIT_MAX = 10

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_analysis_prompt_template():
    """Return the analysis prompt template"""
    return """You are to perform an analysis of the research paper abstract provided below, which relates to {supplement_name}. Output only the specified information and nothing else. Format your response exactly as requested.

Abstract to analyze:
---
{abstract_text}
---

Based on the abstract above, provide the following information:

- Safety Score (1-10): Evaluate whether the study demonstrates that {supplement_name} is safe for human consumption. Consider reported adverse events, side effects, toxicity information, contraindications, and safety profiles across different dosages. A score of 1 indicates significant safety concerns, while 10 indicates excellent safety with no reported adverse effects. If safety is not addressed in the study, mark as "Not Assessed."

- Efficacy Score (1-10): Rate how effectively the supplement achieved its intended outcomes based on the study results. Consider statistical significance, effect size, clinical relevance, and consistency of results. A score of 1 indicates no demonstrable effect, 5 indicates modest effects, and 10 indicates strong, clinically meaningful outcomes. If the study shows mixed results, explain the context.

- Study Quality Score (1-10): Evaluate the methodological rigor of the study based on:

  * Study design (RCT > cohort > case-control > case series)

  * Sample size (larger samples receive higher scores)

  * Appropriate controls and blinding procedures

  * Statistical analysis methods

  * Duration of follow-up

  * Funding source independence

  * Peer-review status and journal reputation

Scoring Guidelines:

When assigning scores from 1-10, please use the full range of the scale. Avoid clustering scores in the middle range (4-7) simply to appear moderate. Each score should accurately reflect the paper's merits on that dimension, even if that means giving very high (9-10) or very low (1-2) scores when warranted. The goal is precision and accuracy, not moderation. For example:

- A score of 1-2 indicates significant deficiencies or concerns

- A score of 3-4 indicates below average performance

- A score of 5-6 indicates average performance

- A score of 7-8 indicates above average, strong performance

- A score of 9-10 indicates exceptional, outstanding performance

Remember that differentiation between studies is valuable, and don't hesitate to use the extremes of the scale when the evidence supports such a rating.

- Study Goal: In 1-2 sentences, describe what the researchers were attempting to determine about {supplement_name}. Frame this in relation to a specific health outcome or physiological effect.

- Results Summary: In 2-3 sentences, concisely describe what the study found regarding {supplement_name}'s effects, including any notable limitations or qualifications to these findings.

- Population Specificity: Note the specific population studied (e.g., healthy adults, elderly with specific conditions, athletes), including relevant demographic information.

- Effective Dosage: If provided, note the dosage(s) used in the study and which showed efficacy.

- Study Duration: How long was the intervention administered? Note if effects were acute (single dose) or required ongoing supplementation.

- Interactions: Note any mentioned interactions with medications, foods, or other supplements.

Format your response as follows:

SAFETY SCORE: [1-10 or "Not Assessed"]

EFFICACY SCORE: [1-10]

QUALITY SCORE: [1-10]

GOAL: [1-2 sentences]

RESULTS: [2-3 sentences]

POPULATION: [Brief description]

DOSAGE: [Amount and frequency, if available]

DURATION: [Length of intervention]

INTERACTIONS: [Any noted interactions or "None mentioned"]
"""

@retry(
    stop=stop_after_attempt(API_RETRY_ATTEMPTS),
    wait=wait_exponential(
        multiplier=API_RETRY_WAIT_MULTIPLIER,
        min=API_RETRY_WAIT_MIN,
        max=API_RETRY_WAIT_MAX
    ),
    retry=retry_if_exception_type(requests.exceptions.RequestException)
)
def analyze_abstract_with_deepseek(supplement_name, abstract_text):
    """
    Send abstract to DeepSeek API for analysis with retry logic
    """
    # Add clear instructions about expected format for numeric fields
    system_message = """
    You are a scientific research analysis expert. Follow these instructions carefully:
    
    1. When asked to rate on a scale of 1-10, ALWAYS respond with a single integer between 1 and 10.
    2. If information is not available to assess a category, respond ONLY with "Not Assessed" (no other explanation).
    3. For safety, efficacy, and quality scores, you must provide either a single integer (1-10) or "Not Assessed".
    4. Do not include explanations within the score fields.
    5. Format your response exactly as requested in the prompt.
    """
    
    prompt = get_analysis_prompt_template().format(
        supplement_name=supplement_name,
        abstract_text=abstract_text
    )
    
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

def parse_analysis_response(response_text):
    """
    Parse the LLM response to extract structured data
    """
    if not response_text:
        return None
    
    results = {}
    
    # Extract data using simple line parsing
    lines = response_text.strip().split('\n')
    
    # Initialize fields to None in case they're missing in the response
    fields_map = {
        'SAFETY SCORE:': 'safety_score',
        'EFFICACY SCORE:': 'efficacy_score',
        'QUALITY SCORE:': 'quality_score',
        'GOAL:': 'study_goal',
        'RESULTS:': 'results_summary',
        'POPULATION:': 'population_specificity',
        'DOSAGE:': 'effective_dosage',
        'DURATION:': 'study_duration',
        'INTERACTIONS:': 'interactions'
    }
    
    # Initialize all fields to None
    for field in fields_map.values():
        results[field] = None
    
    for line in lines:
        for prefix, field in fields_map.items():
            if line.startswith(prefix):
                value = line.replace(prefix, '').strip()
                
                # Handle numeric fields properly
                if field in ['efficacy_score', 'quality_score']:
                    # Only convert to int if it's a valid integer
                    if value and value.isdigit():
                        value = int(value)
                    elif value and "not assessed" in value.lower():
                        # Set to None if "Not Assessed"
                        value = None
                    elif value and any(char.isdigit() for char in value):
                        # If there's a number somewhere in the string, try to extract it
                        try:
                            # Extract the first number found
                            for part in value.split():
                                if part.isdigit():
                                    value = int(part)
                                    break
                            else:
                                # If we didn't break, no valid integer was found
                                value = None
                        except (ValueError, AttributeError):
                            value = None
                    else:
                        # Default to None for any other non-numeric value
                        value = None
                
                results[field] = value
                break
    
    # Add metadata
    results['analysis_prompt_version'] = PROMPT_VERSION
    results['last_analyzed_at'] = datetime.now(timezone.utc).isoformat()
    
    logger.debug(f"Parsed analysis results: {results}")
    
    return results

def get_supplements_needing_analysis(specific_supplement_id=None):
    """
    Get a list of supplements that have research papers needing analysis
    """
    try:
        query = supabase.table("supplements").select("id, name")
        
        if specific_supplement_id:
            query = query.eq("id", specific_supplement_id)
            
        response = query.execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching supplements: {str(e)}")
        return []

def get_unanalyzed_studies_for_supplement(supplement_id, limit=MAX_PAPERS_PER_SUPPLEMENT):
    """
    Get research studies for a supplement that haven't been analyzed yet
    """
    try:
        response = supabase.table("supplement_studies") \
            .select("id, supplement_id, pmid, title, abstract") \
            .eq("supplement_id", supplement_id) \
            .is_("last_analyzed_at", "null") \
            .order("id") \
            .limit(limit) \
            .execute()
        
        return response.data
    except Exception as e:
        logger.error(f"Error fetching studies for supplement ID {supplement_id}: {str(e)}")
        return []

def update_study_with_analysis(study_id, analysis_data):
    """
    Update a study record with analysis results
    """
    try:
        # Validate data types before updating
        update_data = {}
        
        # Ensure numeric fields have proper type
        int_fields = ['efficacy_score', 'quality_score']
        for field, value in analysis_data.items():
            if field in int_fields:
                # Ensure integer fields are either valid integers or NULL
                if value is not None and not isinstance(value, int):
                    logger.warning(f"Field {field} has invalid value type: {type(value)}. Value: '{value}'. Setting to NULL.")
                    update_data[field] = None
                else:
                    update_data[field] = value
            else:
                update_data[field] = value
        
        # Log the cleaned data before updating
        logger.debug(f"Updating study ID {study_id} with data: {update_data}")
        
        response = supabase.table("supplement_studies") \
            .update(update_data) \
            .eq("id", study_id) \
            .execute()
        
        return True
    except Exception as e:
        logger.error(f"Error updating study ID {study_id}: {str(e)}")
        return False

def save_progress(supplement_id, processed_count, total_count):
    """
    Save progress information to a local file
    """
    progress_data = {
        'last_supplement_id': supplement_id,
        'processed_count': processed_count,
        'total_count': total_count,
        'timestamp': datetime.now().isoformat()
    }
    
    with open('analysis_progress.json', 'w') as f:
        json.dump(progress_data, f)

def load_progress():
    """
    Load progress information from a local file
    """
    try:
        with open('analysis_progress.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def parse_arguments():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(description='Analyze supplement research papers')
    parser.add_argument('--supplement', type=int, help='Specific supplement ID to process')
    parser.add_argument('--reset', action='store_true', help='Ignore previous progress and start from beginning')
    parser.add_argument('--limit', type=int, default=MAX_PAPERS_PER_SUPPLEMENT, 
                        help=f'Maximum papers to process per supplement (default: {MAX_PAPERS_PER_SUPPLEMENT})')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--skip-errors', action='store_true', 
                        help='Continue processing even if a study fails to update')
    return parser.parse_args()

def main():
    """
    Main function to process supplements and their research studies
    """
    # Parse command line arguments
    args = parse_arguments()
    
    # Add debug logging flag
    if args.debug:
        logger.setLevel(logging.DEBUG)
        # Add a handler for debug logs
        debug_handler = logging.FileHandler("supplement_analysis_debug.log", encoding='utf-8')
        debug_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        debug_handler.setFormatter(formatter)
        logger.addHandler(debug_handler)
        logger.debug("Debug logging enabled")
    
    logger.info(f"Starting analysis script at {datetime.now().isoformat()}")
    logger.info(f"Using prompt version: {PROMPT_VERSION}")
    logger.info(f"Max papers per supplement: {args.limit}")
    
    # Load progress from previous run (unless reset flag is set)
    progress = None if args.reset else load_progress()
    last_supplement_id = progress.get('last_supplement_id') if progress else None
    
    if last_supplement_id and not args.reset:
        logger.info(f"Resuming from supplement ID: {last_supplement_id}")
    
    # Get supplements
    supplements = get_supplements_needing_analysis(args.supplement)
    logger.info(f"Found {len(supplements)} supplements to process")
    
    if not supplements:
        logger.info("No supplements found to process. Exiting.")
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
        
        # Get unanalyzed studies for this supplement
        studies = get_unanalyzed_studies_for_supplement(supplement_id, args.limit)
        logger.info(f"Found {len(studies)} unanalyzed studies for {supplement_name}")
        
        if not studies:
            logger.info(f"No unanalyzed studies found for {supplement_name}, moving to next supplement.")
            continue
        
        processed_count = 0
        
        for i, study in enumerate(studies):
            study_id = study['id']
            title = study['title']
            abstract = study['abstract']
            
            # Truncate long titles for logging and ensure they're safe for console output
            if title:
                # Remove or replace problematic characters for Windows console
                title_safe = title
                if sys.platform == 'win32':
                    # Replace specific Greek letters with ascii equivalents
                    title_safe = title.replace('α', 'alpha').replace('β', 'beta').replace('γ', 'gamma')
                
                title_display = (title_safe[:47] + '...') if len(title_safe) > 50 else title_safe
            else:
                title_display = "[No title]"
            
            logger.info(f"  [{i+1}/{len(studies)}] Analyzing study: {title_display}")
            
            # Skip if abstract is missing
            if not abstract:
                logger.warning(f"    No abstract available for study ID {study_id}, skipping.")
                continue
            
            try:
                # Analyze the abstract
                analysis_response = analyze_abstract_with_deepseek(supplement_name, abstract)
                
                # Parse the response
                analysis_data = parse_analysis_response(analysis_response)
                
                if not analysis_data:
                    logger.warning(f"    Failed to parse analysis for study ID {study_id}, skipping.")
                    continue
                
                # Update the study record
                success = update_study_with_analysis(study_id, analysis_data)
                
                if success:
                    logger.info(f"    Successfully updated study ID {study_id}")
                    processed_count += 1
                    total_processed += 1
                else:
                    logger.warning(f"    Failed to update study ID {study_id}")
                    if not args.skip_errors:
                        logger.error("Stopping due to database update error. Use --skip-errors to continue despite errors.")
                        return
                
            except Exception as e:
                logger.error(f"    Error processing study ID {study_id}: {str(e)}")
                if not args.skip_errors:
                    logger.error("Stopping due to processing error. Use --skip-errors to continue despite errors.")
                    return
            
            # Save progress after each study
            save_progress(supplement_id, processed_count, len(studies))
            
            # Sleep to avoid API rate limits
            time.sleep(2)
        
        logger.info(f"Processed {processed_count} studies for supplement {supplement_name}")
    
    logger.info(f"\nAnalysis script completed at {datetime.now().isoformat()}")
    logger.info(f"Total studies processed: {total_processed}")

if __name__ == "__main__":
    main()