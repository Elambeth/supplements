# The key issue is likely in how the script compares versions

"""
I notice from your CSV info that analysis_prompt_version is stored as a Float in your database.
This could cause comparison issues when your script is using string comparisons.

For example:
- In DB: 1.1 (as a float)
- In script: "1.1" (as a string)

These would not match in a strict equality comparison, causing the script
to repeatedly process the same studies.
"""

# 1. Modified version of get_studies_to_analyze to handle float vs string comparison:

def get_studies_to_analyze(batch_size=5, supplement_id=None, prompt_version=DEFAULT_PROMPT_VERSION):
    """
    Fetches a batch of supplement studies that haven't been analyzed yet
    or were analyzed with an older prompt version.
    
    Args:
        batch_size: Number of studies to fetch
        supplement_id: Optional ID to restrict to a specific supplement
        prompt_version: The prompt version to use for analysis
    """
    try:
        # Convert the string prompt_version to float for consistent comparison with DB
        try:
            float_prompt_version = float(prompt_version)
            print(f"Using float version {float_prompt_version} for comparison (from {prompt_version})")
        except ValueError:
            float_prompt_version = prompt_version
            print(f"Couldn't convert {prompt_version} to float, using as is")
            
        params = {
            'batch_limit': batch_size,
            'current_prompt_version': float_prompt_version  # Use float version
        }
        
        if supplement_id:
            print(f"Calling RPC 'get_studies_for_analysis_by_supplement' with supplement_id={supplement_id}, batch_limit={batch_size}, prompt_version={float_prompt_version}")
            response = supabase.rpc('get_studies_for_analysis_by_supplement', {
                **params,
                'supplement_filter': supplement_id
            }).execute()
        else:
            print(f"Calling RPC 'get_studies_for_analysis' with batch_limit={batch_size}, current_prompt_version={float_prompt_version}")
            response = supabase.rpc('get_studies_for_analysis', params).execute()

        print(f"RPC call completed. Response data: {response.data}")
        
        # Additional check to filter out already processed studies with matching versions
        # This is a safeguard in case the database comparison has issues
        if response.data:
            filtered_data = []
            for study in response.data:
                db_version = study.get('analysis_prompt_version')
                
                # Handle different data types for comparison
                if db_version is not None:
                    db_version_float = float(db_version) if isinstance(db_version, str) else db_version
                    prompt_version_float = float(prompt_version) if isinstance(prompt_version, str) else prompt_version
                    
                    # Only include studies with different versions
                    if abs(db_version_float - prompt_version_float) > 0.001:  # Allow for floating point errors
                        filtered_data.append(study)
                        print(f"Including study {study.get('study_id')} with version {db_version} (different from target {prompt_version})")
                    else:
                        print(f"Filtering out study {study.get('study_id')} with matching version {db_version}")
                else:
                    # Include studies with no version
                    filtered_data.append(study)
                    print(f"Including study {study.get('study_id')} with no version")
                    
            print(f"Filtered {len(response.data) - len(filtered_data)} studies with matching versions")
            return filtered_data
            
        return response.data

    except Exception as e:
        print(f"An error occurred while fetching studies: {e}")
        return []

# 2. Modified update_study_with_analysis function to handle float versions:

def update_study_with_analysis(study_id, analysis_data, prompt_version=DEFAULT_PROMPT_VERSION):
    if not analysis_data:
        print(f"No analysis data to update for study {study_id}.")
        return False
    
    # Convert prompt_version to float for database storage
    try:
        float_prompt_version = float(prompt_version)
    except ValueError:
        float_prompt_version = prompt_version
    
    db_payload = {
        "safety_score": analysis_data.get("safety_score"),
        "efficacy_score": analysis_data.get("efficacy_score"),
        "quality_score": analysis_data.get("quality_score"),
        "study_goal": analysis_data.get("study_goal"),
        "results_summary": analysis_data.get("results_summary"),
        "population_specificity": analysis_data.get("population_specificity"),
        "effective_dosage": analysis_data.get("effective_dosage"),
        "study_duration": analysis_data.get("study_duration"),
        "interactions": analysis_data.get("interactions"),
        "analysis_prompt_version": float_prompt_version,  # Store as float
        "last_analyzed_at": "now()"
    }
    
    try:
        # Verify the study exists and check its current version
        check_response = supabase.table('supplement_studies') \
            .select('id, analysis_prompt_version') \
            .eq('id', study_id) \
            .execute()
            
        if not check_response.data or len(check_response.data) == 0:
            print(f"Error: Study ID {study_id} not found in database.")
            return False
            
        current_version = check_response.data[0].get('analysis_prompt_version')
        
        # Skip update if versions already match (comparing as floats)
        if current_version is not None:
            current_float = float(current_version) if isinstance(current_version, str) else current_version
            target_float = float(prompt_version) if isinstance(prompt_version, str) else prompt_version
            
            if abs(current_float - target_float) < 0.001:  # Account for floating point errors
                print(f"Study {study_id} already has version {current_version}. Skipping update.")
                return True
            
        print(f"Current prompt version for study {study_id}: {current_version}, updating to: {float_prompt_version}")
        
        # Perform the update
        response = supabase.table('supplement_studies') \
            .update(db_payload) \
            .eq('id', study_id) \
            .execute()
            
        if hasattr(response, 'error') and response.error:
             print(f"Error updating study {study_id} in DB: {response.error}")
             print(f"Payload attempted: {db_payload}")
             return False
             
        print(f"Successfully updated study {study_id} in database.")
        return True
        
    except Exception as e:
        print(f"An unexpected exception occurred while updating study {study_id} in DB: {e}")
        print(f"Payload attempted: {db_payload}")
        return False

# 3. Modified RPC function for database (SQL):
"""
-- Update your get_studies_for_analysis_by_supplement function to handle float versions:
CREATE OR REPLACE FUNCTION get_studies_for_analysis_by_supplement(
  batch_limit integer,
  current_prompt_version double precision, -- Changed to double precision for float
  supplement_filter bigint
) 
RETURNS TABLE(
  study_id bigint,
  pmid text,
  abstract text,
  supplement_name text,
  analysis_prompt_version double precision -- Changed to double precision
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    ss.id as study_id,
    ss.pmid,
    ss.abstract,
    s.name as supplement_name,
    ss.analysis_prompt_version
  FROM 
    supplement_studies ss
    JOIN supplements s ON ss.supplement_id = s.id
  WHERE 
    ss.supplement_id = supplement_filter
    AND (
      ss.analysis_prompt_version IS NULL 
      OR ABS(ss.analysis_prompt_version - current_prompt_version) > 0.001 -- Float comparison
    )
    AND ss.abstract IS NOT NULL
    AND length(trim(ss.abstract)) > 0
  ORDER BY ss.id
  LIMIT batch_limit;
END;
$$ LANGUAGE plpgsql;
"""

# 4. Add a quick verification script to check version types in your database:

"""
This is a standalone script to verify version types in your database.
Run this to see exactly what's happening with the versions.
"""

import os
import dotenv
from supabase import create_client

# Load environment variables
dotenv.load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_version_types():
    print("=== Checking Version Types in Database ===")
    
    try:
        # Get some sample studies
        response = supabase.table('supplement_studies') \
            .select('id, supplement_id, analysis_prompt_version') \
            .not_.is_('analysis_prompt_version', 'null') \
            .limit(10) \
            .execute()
            
        if not response.data:
            print("No studies with analysis_prompt_version found.")
            return
            
        print(f"Found {len(response.data)} studies with versions. Examining types:")
        
        for study in response.data:
            study_id = study.get('id')
            version = study.get('analysis_prompt_version')
            version_type = type(version).__name__
            
            print(f"Study {study_id}: Version = {version} (Type: {version_type})")
            
            # If string, try converting to float
            if isinstance(version, str):
                try:
                    float_version = float(version)
                    print(f"  Can be converted to float: {float_version}")
                except ValueError:
                    print(f"  Cannot be converted to float!")
    
    except Exception as e:
        print(f"Error checking version types: {e}")

if __name__ == "__main__":
    check_version_types()