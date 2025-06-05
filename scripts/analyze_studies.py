import os
import dotenv
from supabase import create_client, Client
import httpx
import time
from datetime import datetime, timezone
import re

# --- Configuration ---
# Load environment variables from .env file
dotenv.load_dotenv()

SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use the service role key for admin operations
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
LLM_MODEL = "deepseek-chat" # As specified in your example
LLM_BASE_URL = "https://api.deepseek.com/v1" # Corrected API base URL for chat completions
PROMPT_VERSION = "1.1" # Current prompt version (as in your example)

# Maximum number of papers to process per supplement in one run
MAX_PAPERS_PER_SUPPLEMENT_RUN = 20

# --- Initialize Supabase Client ---
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Successfully connected to Supabase.")
except Exception as e:
    print(f"Error connecting to Supabase: {e}")
    exit()

# --- Initialize DeepSeek API Client (using httpx) ---
deepseek_client = httpx.Client(base_url=LLM_BASE_URL, headers={
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Content-Type": "application/json"
})

def get_analysis_prompt_template(supplement_name: str, abstract_text: str) -> str:
    """
    Generates the prompt for the DeepSeek API.
    """
    return f"""You are to perform an analysis of the research paper abstract provided below, which relates to {supplement_name}. Output only the specified information and nothing else. Format your response exactly as requested.

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

def parse_llm_response(response_text: str) -> dict:
    """
    Parses the structured text response from the LLM into a dictionary.
    """
    parsed_data = {}
    patterns = {
        "safety_score": r"SAFETY SCORE:\s*(.+)",
        "efficacy_score": r"EFFICACY SCORE:\s*(\d+)",
        "quality_score": r"QUALITY SCORE:\s*(\d+)",
        "study_goal": r"GOAL:\s*([\s\S]+?)RESULTS:", # Capture multiline until RESULTS:
        "results_summary": r"RESULTS:\s*([\s\S]+?)POPULATION:", # Capture multiline until POPULATION:
        "population_specificity": r"POPULATION:\s*([\s\S]+?)DOSAGE:", # Capture multiline until DOSAGE:
        "effective_dosage": r"DOSAGE:\s*([\s\S]+?)DURATION:", # Capture multiline until DURATION:
        "study_duration": r"DURATION:\s*([\s\S]+?)INTERACTIONS:", # Capture multiline until INTERACTIONS:
        "interactions": r"INTERACTIONS:\s*(.+)"
    }

    # Adjusting multiline patterns to be less greedy and stop at the next known keyword or end of string
    # The current patterns for multiline are okay but might need refinement if responses are very varied.
    # A more robust approach would be to split by lines and then parse.

    for key, pattern in patterns.items():
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if key in ["efficacy_score", "quality_score"]:
                try:
                    parsed_data[key] = int(value)
                except ValueError:
                    print(f"Warning: Could not parse {key} value '{value}' as integer. Storing as None.")
                    parsed_data[key] = None
            elif key == "safety_score":
                 parsed_data[key] = value # Stays as text, e.g., "Not Assessed" or "7"
            else:
                # Clean up potential bleed-over from multiline captures
                if key == "study_goal": value = value.split("RESULTS:")[0].strip()
                if key == "results_summary": value = value.split("POPULATION:")[0].strip()
                if key == "population_specificity": value = value.split("DOSAGE:")[0].strip()
                if key == "effective_dosage": value = value.split("DURATION:")[0].strip()
                if key == "study_duration": value = value.split("INTERACTIONS:")[0].strip()

                parsed_data[key] = value
        else:
            parsed_data[key] = None
            print(f"Warning: Could not find {key} in LLM response.")

    # Ensure all keys are present, even if None
    expected_keys = [
        "safety_score", "efficacy_score", "quality_score", "study_goal",
        "results_summary", "population_specificity", "effective_dosage",
        "study_duration", "interactions"
    ]
    for k in expected_keys:
        if k not in parsed_data:
            parsed_data[k] = None

    return parsed_data

def analyze_and_update_study(study_id: int, supplement_name: str, abstract: str):
    """
    Analyzes a single study abstract using DeepSeek and updates the database.
    """
    if not abstract or not abstract.strip():
        print(f"  Skipping study ID {study_id} for supplement '{supplement_name}' due to empty abstract.")
        return

    print(f"  Analyzing study ID {study_id} for supplement '{supplement_name}'...")
    prompt = get_analysis_prompt_template(supplement_name, abstract)

    try:
        response = deepseek_client.post(
            "/chat/completions", # Ensure this is the correct endpoint for your DeepSeek version
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 1000, # Adjust as needed
                "temperature": 0.2 # Lower temperature for more deterministic output
            },
            timeout=120 # Increased timeout for potentially long analyses
        )
        response.raise_for_status() # Raise an exception for HTTP errors
        
        llm_response_content = response.json()["choices"][0]["message"]["content"]
        print(f"    LLM Raw Response: {llm_response_content[:200]}...") # Log snippet of raw response

        parsed_data = parse_llm_response(llm_response_content)
        print(f"    Parsed Data: {parsed_data}")

        if not any(parsed_data.values()): # Check if all parsed values are None
            print(f"    Error: LLM response parsing resulted in all None values for study ID {study_id}. LLM Raw: {llm_response_content}")
            # Optionally, update with an error state or skip update
            # For now, we skip updating if parsing completely fails
            return

        update_payload = {
            "safety_score": parsed_data.get("safety_score"),
            "efficacy_score": parsed_data.get("efficacy_score"),
            "quality_score": parsed_data.get("quality_score"),
            "study_goal": parsed_data.get("study_goal"),
            "results_summary": parsed_data.get("results_summary"),
            "population_specificity": parsed_data.get("population_specificity"),
            "effective_dosage": parsed_data.get("effective_dosage"),
            "study_duration": parsed_data.get("study_duration"),
            "interactions": parsed_data.get("interactions"),
            "analysis_prompt_version": PROMPT_VERSION,
            "last_analyzed_at": datetime.now(timezone.utc).isoformat()
        }

        # Filter out None values from payload to avoid Supabase errors if a field cannot be None
        # and you want to keep the existing value. However, for these fields, setting to None if
        # not found might be acceptable. Check your DB constraints.
        # update_payload_cleaned = {k: v for k, v in update_payload.items() if v is not None}
        # For this script, we'll send all keys as parsed, allowing NULLs if the DB schema permits.


        update_response = supabase.table("supplement_studies").update(update_payload).eq("id", study_id).execute()

        if update_response.data:
            print(f"    Successfully updated study ID {study_id} in Supabase.")
        else:
            # Supabase V2 client's update usually doesn't have 'error' in successful response,
            # but data list might be empty if no rows matched. Check count or data presence.
            # For Supabase Python client, if there's an error, it should raise an exception caught below.
            # If data is empty but no exception, it could mean the `eq("id", study_id)` didn't match.
            print(f"    Study ID {study_id} updated (or no error reported, but check data). Response: {update_response}")


    except httpx.HTTPStatusError as e:
        print(f"    Error calling DeepSeek API for study ID {study_id}: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        print(f"    Request error calling DeepSeek API for study ID {study_id}: {e}")
    except KeyError as e:
        print(f"    Error parsing DeepSeek API JSON response for study ID {study_id}: Missing key {e}. Response: {response.text if 'response' in locals() else 'No response object'}")
    except Exception as e:
        print(f"    An unexpected error occurred while processing study ID {study_id}: {e}")
        # Consider more specific error handling for Supabase update failures
        # if hasattr(e, 'message'): print(f"    Supabase error details: {e.message}")


def main():
    print("Starting supplement study analysis script...")

    # 1. Fetch all supplements
    try:
        supplements_response = supabase.table("supplements").select("id, name").execute()
        if supplements_response.data:
            supplements = supplements_response.data
            print(f"Found {len(supplements)} supplements to process.")
        else:
            print("No supplements found in the database.")
            return
    except Exception as e:
        print(f"Error fetching supplements: {e}")
        return

    total_studies_processed_this_run = 0

    # 2. Iterate through each supplement
    for supplement in supplements:
        supplement_id = supplement["id"]
        supplement_name = supplement["name"]
        print(f"\nProcessing supplement: {supplement_name} (ID: {supplement_id})")

        # 3. Fetch unanalyzed studies for the current supplement, limited to MAX_PAPERS_PER_SUPPLEMENT_RUN
        try:
            studies_response = supabase.table("supplement_studies") \
                .select("id, abstract") \
                .eq("supplement_id", supplement_id) \
                .is_("last_analyzed_at", None) \
                .limit(MAX_PAPERS_PER_SUPPLEMENT_RUN) \
                .execute()

            if studies_response.data:
                studies_to_analyze = studies_response.data
                print(f"  Found {len(studies_to_analyze)} unanalyzed studies for {supplement_name} (limit {MAX_PAPERS_PER_SUPPLEMENT_RUN}).")

                for study in studies_to_analyze:
                    analyze_and_update_study(study["id"], supplement_name, study["abstract"])
                    total_studies_processed_this_run += 1
                    time.sleep(1) # Small delay to be kind to the API, adjust as needed

            else:
                print(f"  No unanalyzed studies found for {supplement_name} in this batch.")

        except Exception as e:
            print(f"  Error fetching or processing studies for supplement {supplement_name}: {e}")
            # Continue to the next supplement

    print(f"\nScript finished. Total studies processed in this run: {total_studies_processed_this_run}.")

if __name__ == "__main__":
    if not all([SUPABASE_URL, SUPABASE_KEY, DEEPSEEK_API_KEY]):
        print("Missing one or more environment variables: NEXT_PUBLIC_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DEEPSEEK_API_KEY")
    else:
        main()