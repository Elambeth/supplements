import os
import dotenv
from supabase import create_client

# Load environment variables from .env file
dotenv.load_dotenv()

# --- Configuration ---
SUPABASE_URL = os.environ.get("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_analysis_status():
    """
    Quick check of supplements with unanalyzed studies
    """
    print("Checking supplements with unanalyzed studies...")
    
    try:
        # Get count of all studies
        studies_response = supabase.table("supplement_studies").select("id", count="exact").execute()
        total_studies = studies_response.count
        
        # Get count of analyzed studies
        analyzed_response = supabase.table("supplement_studies").select("id", count="exact").not_.is_("last_analyzed_at", "null").execute()
        analyzed_studies = analyzed_response.count
        
        # Calculate unanalyzed
        unanalyzed_studies = total_studies - analyzed_studies
        
        print(f"\nSUMMARY:")
        print(f"Total studies: {total_studies}")
        print(f"Analyzed studies: {analyzed_studies} ({(analyzed_studies/total_studies)*100:.2f if total_studies > 0 else 0}%)")
        print(f"Unanalyzed studies: {unanalyzed_studies} ({(unanalyzed_studies/total_studies)*100:.2f if total_studies > 0 else 0}%)")
        
        # Find supplements with unanalyzed studies
        if unanalyzed_studies > 0:
            print("\nFinding supplements with unanalyzed studies...")
            
            # First get all supplements
            supplements_response = supabase.table("supplements").select("id, name").execute()
            supplements = {s['id']: s['name'] for s in supplements_response.data}
            
            # Find supplements with unanalyzed studies
            unanalyzed_supplements = []
            
            for supp_id, supp_name in supplements.items():
                # Check if this supplement has unanalyzed studies
                unanalyzed_response = supabase.table("supplement_studies")\
                    .select("id", count="exact")\
                    .eq("supplement_id", supp_id)\
                    .is_("last_analyzed_at", "null")\
                    .execute()
                
                unanalyzed_count = unanalyzed_response.count
                
                if unanalyzed_count > 0:
                    # Get total studies for this supplement
                    total_response = supabase.table("supplement_studies")\
                        .select("id", count="exact")\
                        .eq("supplement_id", supp_id)\
                        .execute()
                    
                    total_count = total_response.count
                    
                    unanalyzed_supplements.append({
                        "id": supp_id,
                        "name": supp_name,
                        "total": total_count,
                        "unanalyzed": unanalyzed_count,
                        "percent_unanalyzed": (unanalyzed_count / total_count) * 100
                    })
            
            # Sort by percentage unanalyzed
            unanalyzed_supplements.sort(key=lambda x: x["percent_unanalyzed"], reverse=True)
            
            # Print supplements with unanalyzed studies
            print(f"\nFound {len(unanalyzed_supplements)} supplements with unanalyzed studies:")
            
            for i, supp in enumerate(unanalyzed_supplements[:20]):
                print(f"{i+1}. {supp['name']} (ID: {supp['id']}) - {supp['unanalyzed']}/{supp['total']} unanalyzed ({supp['percent_unanalyzed']:.1f}%)")
            
            if len(unanalyzed_supplements) > 20:
                print(f"... and {len(unanalyzed_supplements) - 20} more supplements with unanalyzed studies")
            
            print("\nRun the following commands to analyze these supplements:")
            
            for supp in unanalyzed_supplements[:5]:
                print(f"python supplement_research_analyzer.py --supplement {supp['id']}")
        
    except Exception as e:
        print(f"Error checking analysis status: {str(e)}")

if __name__ == "__main__":
    check_analysis_status()